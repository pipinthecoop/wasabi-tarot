import hashlib
import copy
import hmac
import json
import io
import urllib.parse
import time
import tempfile
import unittest
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch

from tarot.core import Store, load_registry
from tarot.server import deliver, verify, handler


class TarotTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.registry = load_registry("registry.json")
        self.store = Store(str(Path(self.tmp.name) / "state.sqlite3"), self.registry)

    def draw(self, key, text="draw dawn single"):
        result = self.store.command(key, "T1", "C1", "U1", text)
        if result.get("error"):
            raise ValueError(result["text"])
        return result

    def test_concurrent_duplicate_draws(self):
        with ThreadPoolExecutor(max_workers=12) as pool:
            results = list(pool.map(self.draw, ["same"] * 24))
        self.assertTrue(all(r == results[0] for r in results))
        with self.store.connect() as db:
            self.assertEqual(db.execute("SELECT COUNT(*) FROM outbox").fetchone()[0], 1)
        self.assertIn("77 draw / 1 discard", self.draw("status", "status dawn")["text"])

    def test_concurrent_unique_finite_draws_and_restart(self):
        with ThreadPoolExecutor(max_workers=12) as pool:
            results = list(pool.map(self.draw, map(str, range(78))))
        self.assertEqual(len({r["cards"][0] for r in results}), 78)
        self.store = Store(self.store.path, self.registry)
        with self.assertRaisesRegex(ValueError, "Explicitly shuffle"):
            self.draw("exhausted")
        self.assertIn("0 draw / 78 discard", self.draw("status", "status dawn")["text"])
        self.draw("shuffle", "shuffle dawn")
        self.assertIn("cycle 2", self.draw("status2", "status dawn")["text"])

    def test_partial_spread_is_atomic(self):
        for i in range(77):
            self.draw(str(i))
        with self.assertRaises(ValueError):
            self.draw("three", "draw dawn three")
        self.assertIn("1 draw / 77 discard", self.draw("status", "status dawn")["text"])

    def test_deck_and_workspace_isolation(self):
        self.draw("one")
        self.assertIn("78 draw", self.draw("other", "status midnight")["text"])
        self.assertIn("78 draw", self.store.command("workspace2", "T2", "C1", "U1", "status dawn")["text"])

    def test_custom_cards_spreads(self):
        self.registry["cards"].append({"id": "custom", "name": "Example", "meaning": "Hello", "art": {}})
        self.registry["decks"]["custom"] = {"cards": ["custom"]}
        result = self.draw("custom", 'draw custom "My focus"')
        self.assertEqual(result["cards"], ["custom"])
        self.assertIn("My focus", result["payload"]["text"])
        with self.assertRaises(ValueError):
            self.draw("invalid", 'draw dawn "A||C"')

    def test_schedule_dst_retry_and_cancel(self):
        result = self.draw("schedule", "schedule 01:30 America/New_York dawn single")
        self.store.tick(datetime(2026, 11, 1, 5, 30, tzinfo=timezone.utc))
        self.store.tick(datetime(2026, 11, 1, 6, 30, tzinfo=timezone.utc))
        with self.store.connect() as db:
            self.assertEqual(db.execute("SELECT COUNT(*) FROM outbox").fetchone()[0], 1)
        sid = result["text"].split(": ")[1]
        self.assertTrue(self.store.command("badcancel", "T1", "C1", "U2", f"unschedule {sid}")["error"])
        self.draw("cancel", f"unschedule {sid}")
        self.store.tick(datetime(2026, 11, 2, 12, tzinfo=timezone.utc))
        with self.store.connect() as db:
            self.assertEqual(db.execute("SELECT COUNT(*) FROM outbox").fetchone()[0], 1)

    def test_spring_gap_and_restart_catchup(self):
        self.draw("schedule", "schedule 02:30 America/New_York")
        self.store.tick(datetime(2026, 3, 8, 7, tzinfo=timezone.utc))
        self.store.tick(datetime(2026, 3, 8, 22, tzinfo=timezone.utc))
        with self.store.connect() as db:
            self.assertEqual(db.execute("SELECT COUNT(*) FROM outbox").fetchone()[0], 1)

    def test_schedule_exhaustion_one_notice(self):
        for i in range(78):
            self.draw(str(i))
        self.draw("schedule", "schedule 08:00 UTC dawn")
        for _ in range(3):
            self.store.tick(datetime(2026, 10, 9, 12, tzinfo=timezone.utc))
        with self.store.connect() as db:
            self.assertEqual(db.execute("SELECT COUNT(*) FROM outbox").fetchone()[0], 79)

    def test_failed_request_remains_failed_after_shuffle(self):
        for i in range(78):
            self.draw(str(i))
        first = self.store.command("failed", "T1", "C1", "U1", "draw dawn")
        self.draw("shuffle", "shuffle dawn")
        self.assertEqual(first, self.store.command("failed", "T1", "C1", "U1", "draw dawn"))
        self.assertIn("78 draw", self.draw("status", "status dawn")["text"])

    def test_concurrent_scheduler_and_art_urls(self):
        self.draw("schedule", "schedule 08:00 UTC dawn")
        with ThreadPoolExecutor(max_workers=8) as pool:
            list(pool.map(self.store.tick, [datetime(2026, 10, 9, 12, tzinfo=timezone.utc)] * 16))
        with self.store.connect() as db:
            self.assertEqual(db.execute("SELECT COUNT(*) FROM outbox").fetchone()[0], 1)
        registry = load_registry("registry.json", "https://assets.example/art")
        self.assertEqual(registry["cards"][0]["art"]["midnight"], "https://assets.example/art/midnight/major-0.png")
        with self.assertRaises(ValueError):
            load_registry("registry.json", "https://user:password@assets.example/art")

    def test_signed_http_command_retry_and_workspace_rejection(self):
        body = urllib.parse.urlencode(dict(team_id="T1", channel_id="C1", user_id="U1", trigger_id="trigger", command="/tarot", text="draw dawn")).encode()
        stamp = str(int(time.time()))
        signature = "v0=" + hmac.new(b"secret", b"v0:" + stamp.encode() + b":" + body, hashlib.sha256).hexdigest()
        cls = handler(self.store, "secret", "T1")
        responses = []
        for _ in range(2):
            req = cls.__new__(cls)
            req.path = "/slack/commands"
            req.headers = {"Content-Length": str(len(body)), "X-Slack-Request-Timestamp": stamp, "X-Slack-Signature": signature}
            req.rfile, req.wfile = io.BytesIO(body), io.BytesIO()
            with patch.object(req, "send_response") as code, patch.object(req, "send_header"), patch.object(req, "end_headers"):
                req.do_POST()
                code.assert_called_with(200)
            responses.append(req.wfile.getvalue())
        self.assertEqual(responses[0], responses[1])
        with self.store.connect() as db:
            self.assertEqual(db.execute("SELECT COUNT(*) FROM outbox").fetchone()[0], 1)
        headers = req.headers
        bad_cls = handler(self.store, "secret", "OTHER")
        req = bad_cls.__new__(bad_cls)
        req.path, req.headers, req.rfile = "/slack/commands", headers, io.BytesIO(body)
        with patch.object(req, "send_response") as code, patch.object(req, "end_headers"):
            req.do_POST()
            code.assert_called_with(403)

    def test_delivery_success_and_permanent_error(self):
        self.draw("one")
        with patch("urllib.request.urlopen", return_value=io.StringIO('{"ok":true,"ts":"1.2"}')):
            deliver(self.store, "test")
        self.draw("two")
        with patch("urllib.request.urlopen", return_value=io.StringIO('{"ok":false,"error":"not_in_channel"}')):
            deliver(self.store, "test")
        with self.store.connect() as db:
            self.assertEqual(db.execute("SELECT status,ts FROM outbox WHERE id='one'").fetchone(), ("sent", "1.2"))
            self.assertEqual(db.execute("SELECT status,error FROM outbox WHERE id='two'").fetchone(), ("failed", "not_in_channel"))

    def test_membership_addition_and_removal_require_explicit_shuffle(self):
        original = self.draw("first")
        with self.store.connect() as db:
            before = db.execute("SELECT draw,discard,cycle FROM shoes").fetchone()
        changed = copy.deepcopy(self.registry)
        changed["cards"].append({"id": "new-card", "name": "New card", "meaning": "New prompt", "art": {}})
        changed["decks"]["dawn"]["cards"].append("new-card")
        self.store = Store(self.store.path, changed)
        self.assertIn("Membership changed", self.draw("status", "status dawn")["text"])
        with self.assertRaisesRegex(ValueError, "existing shoe is preserved"):
            self.draw("rejected")
        with self.store.connect() as db:
            self.assertEqual(before, db.execute("SELECT draw,discard,cycle FROM shoes").fetchone())
        self.assertEqual(original, self.draw("first"))
        self.draw("explicit", "shuffle dawn")
        self.assertIn("79 draw / 0 discard; cycle 2", self.draw("newstatus", "status dawn")["text"])
        with self.store.connect() as db:
            after_shuffle = db.execute("SELECT draw,discard,cycle FROM shoes").fetchone()
        changed["decks"]["dawn"]["cards"].remove("major-0")
        self.store = Store(self.store.path, changed)
        with self.assertRaises(ValueError):
            self.draw("removed")
        with self.store.connect() as db:
            self.assertEqual(after_shuffle, db.execute("SELECT draw,discard,cycle FROM shoes").fetchone())

    def test_restart_preserves_pending_readings_and_schedule_occurrence(self):
        self.draw("schedule", "schedule 08:00 UTC dawn")
        now = datetime(2026, 10, 9, 12, tzinfo=timezone.utc)
        self.store.tick(now)
        with self.store.connect() as db:
            before = db.execute("SELECT draw,discard,cycle FROM shoes").fetchone()
            outgoing = db.execute("SELECT id,payload,status FROM outbox").fetchall()
        self.store = Store(self.store.path, self.registry)
        self.store.tick(now)
        with self.store.connect() as db:
            self.assertEqual(before, db.execute("SELECT draw,discard,cycle FROM shoes").fetchone())
            self.assertEqual(outgoing, db.execute("SELECT id,payload,status FROM outbox").fetchall())
        self.store.tick(datetime(2026, 10, 10, 12, tzinfo=timezone.utc))
        self.assertIn("76 draw / 2 discard", self.draw("status", "status dawn")["text"])

    def test_same_day_retry_after_clock_rollback(self):
        self.draw("schedule", "schedule 08:00 UTC dawn")
        for hour in (12, 7, 8, 23):
            self.store.tick(datetime(2026, 10, 9, hour, tzinfo=timezone.utc))
        self.assertIn("77 draw / 1 discard", self.draw("status", "status dawn")["text"])

    def test_schedule_and_user_draws_share_one_finite_shoe(self):
        self.draw("schedule", "schedule 08:00 UTC dawn")
        now = datetime(2026, 10, 9, 12, tzinfo=timezone.utc)
        with ThreadPoolExecutor(max_workers=12) as pool:
            futures = [pool.submit(self.draw, f"user-{i}") for i in range(40)]
            futures += [pool.submit(self.store.tick, now) for _ in range(20)]
            for future in futures:
                future.result()
        with self.store.connect() as db:
            readings = [json.loads(row[0])["cards"][0] for row in db.execute("SELECT result FROM requests") if "cards" in json.loads(row[0])]
            self.assertEqual(len(readings), 41)
            self.assertEqual(len(set(readings)), 41)
            self.assertEqual(db.execute("SELECT COUNT(*) FROM outbox").fetchone()[0], 41)

    def test_signature_and_replay(self):
        body, stamp = b"hello", "1000"
        sig = "v0=" + hmac.new(b"secret", b"v0:1000:" + body, hashlib.sha256).hexdigest()
        self.assertTrue(verify("secret", stamp, sig, body, 1001))
        self.assertFalse(verify("secret", stamp, sig, b"changed", 1001))
        self.assertFalse(verify("secret", stamp, sig, body, 1400))
        self.assertFalse(verify("secret", "invalid", sig, body, 1001))

    def test_ambiguous_delivery_quarantined(self):
        self.draw("one")
        with patch("urllib.request.urlopen", side_effect=OSError("timeout")):
            self.assertTrue(deliver(self.store, "test"))
            self.assertFalse(deliver(self.store, "test"))
        with self.store.connect() as db:
            self.assertEqual(db.execute("SELECT status FROM outbox").fetchone()[0], "uncertain")

    def test_registry_rejects_duplicate_and_unknown_cards(self):
        p = Path(self.tmp.name) / "registry.json"
        self.registry["decks"]["dawn"]["cards"].append("unknown")
        p.write_text(json.dumps(self.registry))
        with self.assertRaises(ValueError):
            load_registry(str(p))


if __name__ == "__main__":
    unittest.main()
