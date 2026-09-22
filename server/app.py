"""Sky Islands leaderboard.

A deliberately small service: one SQLite file, two real endpoints.

  POST /api/v1/scores        submit a run; keeps each player's best, and their best
                             on that day's course together with the recorded track
  GET  /api/v1/leaderboard   all-time top N plus the caller's own rank
  GET  /api/v1/ghosts        top runs on a course with tracks, for ghost racing
  GET  /healthz              liveness for compose and Caddy

There are no accounts. A player is a random id the app generates once and
keeps in localStorage. The name is whatever they typed, sanitised. Scores can
be forged by anyone who reads the app bundle; the plausibility caps and the
per-IP rate limit make it tedious rather than impossible.
"""

from __future__ import annotations

import json
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
MAX_TRACK = 12000                                              # numbers: 6000 samples at 10 Hz = 10 min
COURSE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
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
            CREATE TABLE IF NOT EXISTS runs (
              course     TEXT NOT NULL,
              player_id  TEXT NOT NULL,
              name       TEXT NOT NULL,
              score      INTEGER NOT NULL,
              islands    INTEGER NOT NULL DEFAULT 0,
              km         INTEGER NOT NULL DEFAULT 0,
              track      TEXT NOT NULL,
              updated_at INTEGER NOT NULL,
              PRIMARY KEY (course, player_id)
            );
            CREATE INDEX IF NOT EXISTS runs_by_course ON runs(course, score DESC, updated_at ASC);
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
    course: str | None = Field(None, max_length=10)
    track: list[float] | None = Field(None, max_length=MAX_TRACK)

    @field_validator("course")
    @classmethod
    def _course(cls, v: str | None) -> str | None:
        if v is None:
            return None
        if not COURSE_RE.match(v):
            raise ValueError("bad course")
        return v

    @field_validator("track")
    @classmethod
    def _track(cls, v: list[float] | None) -> list[float] | None:
        if v is None:
            return None
        if len(v) % 2 or len(v) < 4:
            raise ValueError("track must be [x, alt, x, alt, ...]")
        for i in range(0, len(v), 2):
            if not (0 <= v[i] <= 10_000_000) or not (-5 <= v[i + 1] <= 5):
                raise ValueError("track value out of range")
        return v

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


def _course_rank(conn: sqlite3.Connection, course: str, score: int, updated_at: int) -> int:
    row = conn.execute(
        "SELECT COUNT(*) AS n FROM runs WHERE course = ? AND (score > ? OR (score = ? AND updated_at < ?))",
        (course, score, score, updated_at),
    ).fetchone()
    return int(row["n"]) + 1


def _course_top(conn: sqlite3.Connection, course: str, limit: int, me: str | None) -> list[Entry]:
    rows = conn.execute(
        "SELECT player_id, name, score, islands, km FROM runs WHERE course = ? "
        "ORDER BY score DESC, updated_at ASC LIMIT ?",
        (course, limit),
    ).fetchall()
    return [
        Entry(rank=i + 1, name=r["name"], score=r["score"], islands=r["islands"], km=r["km"],
              you=(r["player_id"] == me))
        for i, r in enumerate(rows)
    ]


def _compact(track: list[float]) -> str:
    out: list[float] = []
    for i in range(0, len(track), 2):
        out.append(int(track[i]))
        out.append(round(track[i + 1], 3))
    return json.dumps(out, separators=(",", ":"))


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

        daily = None
        if body.course and body.track:
            cur = conn.execute("SELECT score, updated_at FROM runs WHERE course=? AND player_id=?",
                               (body.course, body.player_id)).fetchone()
            if cur is None or body.score > cur["score"]:
                conn.execute(
                    "INSERT OR REPLACE INTO runs(course,player_id,name,score,islands,km,track,updated_at) "
                    "VALUES(?,?,?,?,?,?,?,?)",
                    (body.course, body.player_id, body.name, body.score, body.islands, body.km,
                     _compact(body.track), now),
                )
                dbest, dwhen = body.score, now
            else:
                conn.execute("UPDATE runs SET name=? WHERE course=? AND player_id=?",
                             (body.name, body.course, body.player_id))
                dbest, dwhen = cur["score"], cur["updated_at"]
            daily = {
                "course": body.course,
                "best": dbest,
                "rank": _course_rank(conn, body.course, dbest, dwhen),
                "players": conn.execute("SELECT COUNT(*) AS n FROM runs WHERE course=?", (body.course,)).fetchone()["n"],
                "top": _course_top(conn, body.course, 10, body.player_id),
            }
    return {"best": best, "rank": rank, "improved": improved, "players": total, "top": top, "daily": daily}


@app.get("/api/v1/ghosts")
def ghosts(course: str = Query(..., max_length=10), limit: int = Query(3, ge=1, le=10),
           player_id: str | None = Query(None, max_length=64)) -> dict:
    if not COURSE_RE.match(course):
        raise HTTPException(status_code=422, detail="bad course")
    me = player_id if player_id and PLAYER_RE.match(player_id) else None
    with db() as conn:
        rows = conn.execute(
            "SELECT player_id, name, score, track FROM runs WHERE course = ? "
            "ORDER BY score DESC, updated_at ASC LIMIT ?",
            (course, limit),
        ).fetchall()
        out = [{"name": r["name"], "score": r["score"], "you": r["player_id"] == me,
                "track": json.loads(r["track"])} for r in rows]
        if me and not any(g["you"] for g in out):
            mine = conn.execute("SELECT name, score, track FROM runs WHERE course=? AND player_id=?",
                                (course, me)).fetchone()
            if mine:
                out.append({"name": mine["name"], "score": mine["score"], "you": True,
                            "track": json.loads(mine["track"])})
        players = conn.execute("SELECT COUNT(*) AS n FROM runs WHERE course=?", (course,)).fetchone()["n"]
    return {"course": course, "players": players, "ghosts": out}


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
