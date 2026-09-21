"""Sky Islands leaderboard.

A deliberately small service: one SQLite file, two real endpoints.

  POST /api/v1/scores        submit a run; keeps each player's best
  GET  /api/v1/leaderboard   top N plus the caller's own rank
  GET  /healthz              liveness for compose and Caddy

There are no accounts. A player is a random id the app generates once and
keeps in localStorage. The name is whatever they typed, sanitised. Scores can
be forged by anyone who reads the app bundle; the plausibility caps and the
per-IP rate limit make it tedious rather than impossible.
"""

from __future__ import annotations

import os
import re
import sqlite3
import threading
import time
from collections import defaultdict, deque
from contextlib import contextmanager
from typing import Iterator

from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field, field_validator

DB_PATH = os.environ.get("SKY_DB", "/data/scores.db")
MAX_SCORE = int(os.environ.get("SKY_MAX_SCORE", "250000"))     # gold in one run
MAX_ISLANDS = int(os.environ.get("SKY_MAX_ISLANDS", "500"))
MAX_KM = int(os.environ.get("SKY_MAX_KM", "2000"))
RATE_PER_MIN = int(os.environ.get("SKY_RATE_PER_MIN", "12"))   # submissions per IP per minute
NAME_RE = re.compile(r"[^A-Za-z0-9 _.\-'!?]")
PLAYER_RE = re.compile(r"^[A-Za-z0-9\-]{8,64}$")

app = FastAPI(title="Sky Islands leaderboard", docs_url=None, redoc_url=None)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],           # public read, no cookies or credentials involved
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type"],
)

# ---------- storage ----------

_db_lock = threading.Lock()


def _connect() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA synchronous=NORMAL")
    return conn


@contextmanager
def db() -> Iterator[sqlite3.Connection]:
    with _db_lock:
        conn = _connect()
        try:
            yield conn
            conn.commit()
        finally:
            conn.close()


def init_db() -> None:
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    with db() as conn:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS scores (
              player_id  TEXT PRIMARY KEY,
              name       TEXT NOT NULL,
              score      INTEGER NOT NULL,
              islands    INTEGER NOT NULL DEFAULT 0,
              landings   INTEGER NOT NULL DEFAULT 0,
              km         INTEGER NOT NULL DEFAULT 0,
              runs       INTEGER NOT NULL DEFAULT 1,
              created_at INTEGER NOT NULL,
              updated_at INTEGER NOT NULL
            );
            CREATE INDEX IF NOT EXISTS scores_by_score ON scores(score DESC, updated_at ASC);
            """
        )


@app.on_event("startup")
def _startup() -> None:
    init_db()


# ---------- rate limit ----------

_hits: dict[str, deque[float]] = defaultdict(deque)
_hits_lock = threading.Lock()


def _client_ip(request: Request) -> str:
    fwd = request.headers.get("x-forwarded-for")
    if fwd:
        return fwd.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


def _check_rate(ip: str) -> None:
    now = time.monotonic()
    with _hits_lock:
        q = _hits[ip]
        while q and now - q[0] > 60:
            q.popleft()
        if len(q) >= RATE_PER_MIN:
            raise HTTPException(status_code=429, detail="Too many submissions, try again in a minute")
        q.append(now)


# ---------- models ----------


class ScoreIn(BaseModel):
    player_id: str = Field(..., min_length=8, max_length=64)
    name: str = Field(..., min_length=1, max_length=16)
    score: int = Field(..., ge=0, le=MAX_SCORE)
    islands: int = Field(0, ge=0, le=MAX_ISLANDS)
    landings: int = Field(0, ge=0, le=MAX_ISLANDS)
    km: int = Field(0, ge=0, le=MAX_KM)

    @field_validator("player_id")
    @classmethod
    def _pid(cls, v: str) -> str:
        if not PLAYER_RE.match(v):
            raise ValueError("bad player id")
        return v

    @field_validator("name")
    @classmethod
    def _name(cls, v: str) -> str:
        v = NAME_RE.sub("", v).strip()[:16]
        return v or "Pilot"


class Entry(BaseModel):
    rank: int
    name: str
    score: int
    islands: int
    km: int
    you: bool = False


# ---------- helpers ----------


def _rank_of(conn: sqlite3.Connection, score: int, updated_at: int) -> int:
    row = conn.execute(
        "SELECT COUNT(*) AS n FROM scores WHERE score > ? OR (score = ? AND updated_at < ?)",
        (score, score, updated_at),
    ).fetchone()
    return int(row["n"]) + 1


def _top(conn: sqlite3.Connection, limit: int, me: str | None) -> list[Entry]:
    rows = conn.execute(
        "SELECT player_id, name, score, islands, km FROM scores "
        "ORDER BY score DESC, updated_at ASC LIMIT ?",
        (limit,),
    ).fetchall()
    return [
        Entry(rank=i + 1, name=r["name"], score=r["score"], islands=r["islands"], km=r["km"],
              you=(r["player_id"] == me))
        for i, r in enumerate(rows)
    ]


# ---------- routes ----------


@app.get("/healthz")
def healthz() -> dict:
    with db() as conn:
        n = conn.execute("SELECT COUNT(*) AS n FROM scores").fetchone()["n"]
    return {"ok": True, "players": n}


@app.post("/api/v1/scores")
def submit(body: ScoreIn, request: Request) -> dict:
    _check_rate(_client_ip(request))
    now = int(time.time())
    with db() as conn:
        cur = conn.execute("SELECT score, updated_at FROM scores WHERE player_id = ?", (body.player_id,)).fetchone()
        if cur is None:
            conn.execute(
                "INSERT INTO scores(player_id,name,score,islands,landings,km,runs,created_at,updated_at) "
                "VALUES(?,?,?,?,?,?,1,?,?)",
                (body.player_id, body.name, body.score, body.islands, body.landings, body.km, now, now),
            )
            best, when, improved = body.score, now, True
        elif body.score > cur["score"]:
            conn.execute(
                "UPDATE scores SET name=?, score=?, islands=?, landings=?, km=?, runs=runs+1, updated_at=? "
                "WHERE player_id=?",
                (body.name, body.score, body.islands, body.landings, body.km, now, body.player_id),
            )
            best, when, improved = body.score, now, True
        else:
            conn.execute("UPDATE scores SET name=?, runs=runs+1 WHERE player_id=?", (body.name, body.player_id))
            best, when, improved = cur["score"], cur["updated_at"], False
        rank = _rank_of(conn, best, when)
        top = _top(conn, 10, body.player_id)
        total = conn.execute("SELECT COUNT(*) AS n FROM scores").fetchone()["n"]
    return {"best": best, "rank": rank, "improved": improved, "players": total, "top": top}


@app.get("/api/v1/leaderboard")
def leaderboard(limit: int = Query(10, ge=1, le=100), player_id: str | None = Query(None, max_length=64)) -> dict:
    me = player_id if player_id and PLAYER_RE.match(player_id) else None
    with db() as conn:
        top = _top(conn, limit, me)
        total = conn.execute("SELECT COUNT(*) AS n FROM scores").fetchone()["n"]
        mine = None
        if me:
            row = conn.execute("SELECT name, score, islands, km, updated_at FROM scores WHERE player_id=?", (me,)).fetchone()
            if row:
                mine = Entry(rank=_rank_of(conn, row["score"], row["updated_at"]), name=row["name"],
                             score=row["score"], islands=row["islands"], km=row["km"], you=True)
    return {"players": total, "top": top, "me": mine}
