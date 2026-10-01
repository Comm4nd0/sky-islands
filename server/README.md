# Sky Islands leaderboard service

Tiny FastAPI + SQLite service. Lives at https://skyislands.lumatechsolutions.co.uk.

## Endpoints

| Method | Path | Notes |
| --- | --- | --- |
| POST | `/api/v1/scores` | `{player_id, name, score, islands, landings, km, course?, track?}`. Keeps the player's all-time best, and with `course` (UTC date) plus `track` their best run on that course. Returns `{best, rank, improved, players, top, daily}`. |
| GET | `/api/v1/ghosts?course=YYYY-MM-DD&limit=3&player_id=…` | Top runs on a course with their tracks, plus the caller's own best if not in the top. |
| GET | `/api/v1/leaderboard?limit=10&player_id=…` | Top N plus `me` if the id is known. |
| GET | `/healthz` | `{ok, players}` |
| GET | `/privacy`, `/support` | Static pages from `pages/`, linked from the App Store listing. |

A track is a flat `[x, alt, x, alt, …]` list sampled at 10 Hz: `x` is the run's scroll in
world px, `alt` the height as a fraction of sea-to-sky. Up to 6000 samples (10 min).

Names are trimmed to 16 chars of `A-Za-z0-9 _.-'!?` and replaced with `Pilot` if they hit the
blocklist in `clean_name` (stored names are re-checked on startup). Submissions are rate limited to
12 per IP per minute and capped at plausible values (see the env vars in `app.py`).

## Deploy

```sh
# from the repo root
rsync -av server/app.py server/requirements.txt server/Dockerfile luma:/root/sky-islands/
rsync -av server/pages/ luma:/root/sky-islands/pages/
ssh luma 'cd /root/sky-islands && docker compose up -d --build web'
```

Inspect the remote files and Compose configuration before deploying. Preserve remote
`.env` files and unrelated services; do not use `rsync --delete`. Data lives in the
`sky-islands_sky-data` volume. Before schema changes, retain the old app.py and image,
then make an online SQLite backup (the container does not require the sqlite3 CLI):

```sh
ssh luma 'docker exec -i sky-islands-web python -' <<'PY'
import sqlite3
with sqlite3.connect('/data/scores.db') as source:
    with sqlite3.connect('/tmp/scores-backup.db') as backup:
        source.backup(backup)
        assert backup.execute('PRAGMA integrity_check').fetchone()[0] == 'ok'
PY
ssh luma 'docker cp sky-islands-web:/tmp/scores-backup.db /root/backups/sky-scores-backup.db'
scp luma:/root/backups/sky-scores-backup.db ./scores-backup.db
```

## Run locally

```sh
cd server && pip install -r requirements.txt
SKY_DB=/tmp/scores.db uvicorn app:app --reload
```

## Flight Club / 1.1.0

The new Daily Race uses `/api/v2` and the `flight-club-1` ruleset. The v1 API and its
existing tables remain unchanged for older builds. `init_db` adds a `ranked_runs` table;
back up SQLite with its online backup API before deploying this additive schema change.
Keep the prior image and app.py so code can be rolled back without dropping any tables.

| Method | Path | Notes |
| --- | --- | --- |
| POST | `/api/v2/scores` | Existing run fields plus required `mode:"daily"`, `plane:"bluebird"`, `assisted:false`, `ruleset:"flight-club-1"`, `duration` in seconds and a 10 Hz `track` beginning at takeoff. |
| GET | `/api/v2/leaderboard?course=YYYY-MM-DD&player_id=…` | Today's ranking, best, top ten and player count for the new ruleset. |
| GET | `/api/v2/ghosts?course=YYYY-MM-DD&player_id=…&selection=personal` | One personal ghost; use `selection=rival` for the next pilot ahead, runner-up if leading, or the lowest score for a new pilot. |

Race submissions must use a valid UTC date from the last seven days, last at most 180
seconds, and contain a plausible monotonic flight path with a matching sample count.
Assisted flights, different aircraft and unknown rulesets are rejected. These are
plausibility checks, not cryptographic anti-cheat: anonymous clients can still forge
requests. Mission rewards are bank-only and are excluded from race scores.

Run the API regression suite in an isolated Python 3.11+ environment:

```sh
pip install -r server/requirements.txt httpx==0.28.1
cd server
python -B -m unittest -v test_app
```

Tests create temporary databases and cover best-score updates, legacy isolation,
assisted-run rejection, track checks, name filtering and personal/rival ghost selection.
