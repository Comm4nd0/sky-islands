# Sky Islands leaderboard service

Tiny FastAPI + SQLite service. Lives at https://skyislands.lumatechsolutions.co.uk.

## Endpoints

| Method | Path | Notes |
| --- | --- | --- |
| POST | `/api/v1/scores` | `{player_id, name, score, islands, landings, km, course?, track?}`. Keeps the player's all-time best, and with `course` (UTC date) plus `track` their best run on that course. Returns `{best, rank, improved, players, top, daily}`. |
| GET | `/api/v1/ghosts?course=YYYY-MM-DD&limit=3&player_id=…` | Top runs on a course with their tracks, plus the caller's own best if not in the top. |
| GET | `/api/v1/leaderboard?limit=10&player_id=…` | Top N plus `me` if the id is known. |
| GET | `/healthz` | `{ok, players}` |

A track is a flat `[x, alt, x, alt, …]` list sampled at 10 Hz: `x` is the run's scroll in
world px, `alt` the height as a fraction of sea-to-sky. Up to 6000 samples (10 min).

Names are trimmed to 16 chars of `A-Za-z0-9 _.-'!?`. Submissions are rate limited to
12 per IP per minute and capped at plausible values (see the env vars in `app.py`).

## Deploy

```sh
# from the repo root
rsync -av --delete server/ root@178.104.29.66:/root/sky-islands/
ssh root@178.104.29.66 'cd /root/sky-islands && docker compose up -d --build'
```

Data lives in the `sky-islands_sky-data` volume. To back it up:

```sh
ssh root@178.104.29.66 'docker exec sky-islands-web sqlite3 /data/scores.db .dump' > scores.sql
```

## Run locally

```sh
cd server && pip install -r requirements.txt
SKY_DB=/tmp/scores.db uvicorn app:app --reload
```
