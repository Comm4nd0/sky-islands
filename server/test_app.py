"""Regression tests for isolated daily races; uses a fresh SQLite DB, never production."""
import os
import tempfile
import unittest
from datetime import datetime, timezone

from fastapi.testclient import TestClient

import app as api


class DailyRaceTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory(prefix="sky-race-test-")
        api.DB_PATH = os.path.join(self.directory.name, "scores.db")
        api._hits.clear()
        api.init_db()
        self.client = TestClient(api.app)
        self.course = datetime.now(timezone.utc).date().isoformat()

    def tearDown(self):
        self.client.close()
        self.directory.cleanup()

    def race(self, player="test-player-111", score=100, **changes):
        return dict(player_id=player, name="Pilot", score=score, islands=1, landings=0,
                    km=2, course=self.course, track=[v for i in range(101) for v in (i * 30, .4)],
                    duration=10, mode="daily", plane="bluebird", assisted=False,
                    ruleset="flight-club-1", **changes)

    def post(self, body):
        response = self.client.post("/api/v2/scores", json=body)
        self.assertEqual(response.status_code, 200, response.text)
        return response.json()

    def test_best_only_and_stable_ties(self):
        self.post(self.race())
        second = self.post(self.race(player="test-player-222"))
        self.assertEqual(second["rank"], 2)
        lower = self.post(self.race(score=50))
        self.assertFalse(lower["improved"])
        self.assertEqual(lower["best"], 100)
        higher = self.post(self.race(player="test-player-222", score=200))
        self.assertEqual(higher["rank"], 1)
        self.assertEqual(higher["players"], 2)

    def test_legacy_isolation_and_upgrade_keeps_old_data(self):
        old = self.race()
        response = self.client.post("/api/v1/scores", json=old)
        self.assertEqual(response.status_code, 200)
        api.init_db()
        self.assertEqual(self.client.get("/healthz").json()["players"], 1)
        new = self.client.get("/api/v2/leaderboard", params={"course": self.course}).json()
        self.assertEqual(new["players"], 0)
        self.post(self.race(player="test-player-222"))
        self.assertEqual(self.client.get("/api/v1/leaderboard").json()["players"], 1)

    def test_assisted_free_wrong_plane_and_unknown_rules_rejected(self):
        for key, value in [("assisted", True), ("mode", "free"), ("plane", "goldarrow"),
                           ("ruleset", "unknown"), ("duration", 181), ("course", "2026-02-31")]:
            with self.subTest(key=key):
                body = self.race()
                body[key] = value
                self.assertEqual(self.client.post("/api/v2/scores", json=body).status_code, 422)

    def test_bad_track_and_duration_mismatch_rejected(self):
        for track in [[0,.4,30], [0,.4,-1,.4], [0,.4,999999,.4], [0,.4,30,4], [0,.4,30,.4]]:
            body = self.race()
            body["track"] = track
            self.assertEqual(self.client.post("/api/v2/scores", json=body).status_code, 422)

    def test_personal_and_nearby_rival_ghosts(self):
        for player, score in [("test-player-111", 100), ("test-player-222", 200), ("test-player-333", 300)]:
            self.post(self.race(player=player, score=score))
        params = {"course": self.course, "player_id": "test-player-222"}
        mine = self.client.get("/api/v2/ghosts", params=params).json()["ghosts"][0]
        self.assertTrue(mine["you"])
        self.assertEqual(mine["score"], 200)
        rival = self.client.get("/api/v2/ghosts", params={**params, "selection": "rival"}).json()["ghosts"][0]
        self.assertEqual(rival["score"], 300)
        self.assertFalse(rival["you"])
        self.assertEqual(rival["plane"], "bluebird")
        beginner = self.client.get("/api/v2/ghosts", params={"course": self.course, "selection": "rival"}).json()
        self.assertEqual(beginner["ghosts"][0]["score"], 100)

    def test_names_are_filtered_on_new_leaderboard_and_ghosts(self):
        body = self.race()
        body["name"] = "Sh!thead"
        result = self.post(body)
        self.assertEqual(result["top"][0]["name"], "Pilot")
        ghost = self.client.get("/api/v2/ghosts", params={"course": self.course, "player_id": body["player_id"]}).json()
        self.assertEqual(ghost["ghosts"][0]["name"], "Pilot")

    def test_read_validation_and_no_ghost_yet(self):
        self.assertEqual(self.client.get("/api/v2/ghosts", params={"course": "2026-02-31"}).status_code, 422)
        self.assertEqual(self.client.get("/api/v2/ghosts", params={"course": self.course, "selection": "all"}).status_code, 422)
        empty = self.client.get("/api/v2/ghosts", params={"course": self.course}).json()
        self.assertEqual(empty["ghosts"], [])


if __name__ == "__main__":
    unittest.main()
