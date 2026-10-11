import io
import json
import tempfile
import time
import unittest
import urllib.parse
import hashlib
import hmac
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from unittest.mock import patch
from datetime import datetime, timezone

from tarot.core import Store, load_registry
from tarot.ui import Parlor, reading, load_theme
from tarot.web import WebTable, digest
from tarot.server import handler, deliver
from tarot.embeds import entity, details, reading_id


def values(deck="dawn", spread="three", custom=""):
    return {
        "deck": {"value": {"selected_option": {"value": deck}}},
        "spread": {"value": {"selected_option": {"value": spread}}},
        "custom": {"value": {"value": custom}},
        "time": {"value": {"selected_time": "08:00"}},
        "zone": {"value": {"value": "America/New_York"}},
    }


class InterfaceTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.store = Store(str(Path(self.tmp.name) / "tarot.sqlite3"), load_registry("registry.json"), load_theme("theme.json", "https://assets.example/theme"))
        self.ui = Parlor(self.store)

    def ritual(self, mode="draw"):
        with self.store.connect() as db:
            sid = self.ui.create(db, "T", "C", "U", mode)
        self.ui.open(sid, "T", "U")
        return sid

    def count(self, table):
        with self.store.connect() as db:
            return db.execute("SELECT COUNT(*) FROM " + table).fetchone()[0]

    def test_panel_is_idempotent_and_does_not_initialize_shoe(self):
        first = self.ui.panel("p", "T", "C", "U")
        self.assertEqual(first, self.ui.panel("p", "T", "C", "U"))
        self.assertEqual(self.count("rituals"), 3)
        self.assertEqual(self.count("shoes"), 0)
        self.assertEqual(first["blocks"][1]["type"], "image")
        actions = next(b["elements"] for b in first["blocks"] if b["type"] == "actions")
        self.assertEqual(len({a["action_id"] for a in actions}), len(actions))

    def test_repeated_and_simultaneous_submissions_draw_once(self):
        sid = self.ritual()
        with ThreadPoolExecutor(max_workers=8) as pool:
            results = list(pool.map(lambda _: self.ui.submit(sid, "T", "U", values()), range(16)))
        self.assertTrue(all(r == results[0] for r in results))
        self.assertEqual(self.count("outbox"), 1)
        result = self.store.command("status", "T", "C", "U", "status dawn")
        self.assertIn("75 draw / 3 discard", result["text"])
        self.store = Store(self.store.path, self.store.registry, self.store.theme)
        self.assertEqual(results[0], Parlor(self.store).submit(sid, "T", "U", values()))

    def test_cancel_has_no_mutation_and_cannot_replay_submit(self):
        sid = self.ritual()
        self.ui.cancel(sid, "T", "U")
        result = self.ui.submit(sid, "T", "U", values())
        self.assertEqual(result["response_action"], "errors")
        self.assertEqual(self.count("shoes"), 0)
        self.assertEqual(self.count("outbox"), 0)

    def test_stale_controls_do_not_draw_or_reset_shared_shoe(self):
        a, b = self.ritual(), self.ritual("shuffle")
        self.ui.submit(a, "T", "U", values())
        result = self.ui.submit(b, "T", "U", values())
        self.assertIn("table has changed", result["view"]["blocks"][0]["text"]["text"])
        state = self.store.command("s", "T", "C", "U", "status dawn")["text"]
        self.assertIn("75 draw / 3 discard; cycle 1", state)

    def test_registry_change_invalidates_open_table_without_reset(self):
        sid = self.ritual()
        self.store.registry["cards"].append({"id": "new", "name": "New", "meaning": "A prompt", "art": {}})
        self.store.registry["decks"]["dawn"]["cards"].append("new")
        result = self.ui.submit(sid, "T", "U", values())
        self.assertIn("table has changed", result["view"]["blocks"][0]["text"]["text"])
        self.assertEqual(self.count("shoes"), 0)

    def test_expired_or_other_reader_controls_are_rejected(self):
        sid = self.ritual()
        for team, user in [("OTHER", "U"), ("T", "OTHER")]:
            with self.assertRaises(ValueError):
                self.ui.submit(sid, team, user, values())
        with self.store.connect() as db:
            db.execute("UPDATE rituals SET expires=? WHERE id=?", (time.time() - 1, sid))
        with self.assertRaisesRegex(ValueError, "table has closed"):
            self.ui.submit(sid, "T", "U", values())
        self.assertEqual(self.count("outbox"), 0)

    def test_invalid_form_can_be_corrected_and_schedule_is_single_use(self):
        sid = self.ritual("schedule")
        invalid = values()
        invalid["zone"]["value"]["value"] = "Invalid/Zone"
        response = self.ui.submit(sid, "T", "U", invalid)
        self.assertIn("zone", response["errors"])
        self.assertEqual(self.count("schedules"), 0)
        first = self.ui.submit(sid, "T", "U", values(custom="Focus|Invitation"))
        self.assertEqual(first, self.ui.submit(sid, "T", "U", values()))
        self.assertEqual(self.count("schedules"), 1)
        now = datetime(2026, 10, 10, 15, tzinfo=timezone.utc)
        self.store.tick(now)
        self.store.tick(now)
        self.assertEqual(self.count("outbox"), 1)

    def test_custom_positions_and_both_reading_layouts_preserve_full_text(self):
        for layout in ("classic", "carousel"):
            theme = {**self.store.theme, "reading_layout": layout}
            result = reading(theme, self.store.registry, "C", "dawn", ["My focus"], ["major-0"], 1, 77)
            self.assertIn("My focus", result["text"])
            self.assertIn("Begin with curiosity", result["text"])
            self.assertLessEqual(len(result["blocks"]), 50)
            if layout == "carousel":
                block = next(b for b in result["blocks"] if b["type"] == "carousel")
                self.assertEqual(len(block["elements"]), 1)
                self.assertLessEqual(len(block["elements"][0]["body"]["text"]), 200)

    def test_custom_card_and_deck_render_in_modal(self):
        self.store.registry["cards"].append({"id": "local", "name": "Local card", "meaning": "Test", "art": {}})
        self.store.registry["decks"]["custom"] = {"name": "My custom deck", "cards": ["local"]}
        sid = self.ritual()
        result = self.ui.submit(sid, "T", "U", values("custom", "single"))
        self.assertEqual(result["response_action"], "update")
        with self.store.connect() as db:
            payload = json.loads(db.execute("SELECT payload FROM outbox").fetchone()[0])
        self.assertIn("Local card", payload["text"])

    def test_home_lists_owned_schedules_and_stop_is_idempotent(self):
        self.store.command("schedule", "T", "C", "U", "schedule 08:00 UTC dawn")
        home = self.ui.panel("home", "T", "C", "U", home=True)
        cancel = next(b["accessory"]["value"] for b in home["blocks"] if "accessory" in b)
        first = self.ui.stop(cancel, "T", "U")
        self.assertEqual(first, self.ui.stop(cancel, "T", "U"))
        self.store.tick(datetime(2026, 10, 10, 12, tzinfo=timezone.utc))
        self.assertEqual(self.count("outbox"), 0)

    def test_web_disabled_and_unauthenticated_requests_cannot_mutate(self):
        web = WebTable(self.store)
        with self.assertRaises(PermissionError):
            web.login("anything", "https://table.example")
        with self.assertRaises(PermissionError):
            web.action("anything", "https://table.example", "", {})
        self.assertEqual(self.count("shoes"), 0)

    def login(self):
        web = WebTable(self.store, True, "https://table.example")
        issued = web.issue("code", "T", "C", "U")
        code = issued["text"].split("code in the browser: ")[1].splitlines()[0]
        token = web.login(code, "https://table.example")
        return web, code, token

    def test_slack_code_is_one_time_and_cookie_session_survives_restart(self):
        web, code, token = self.login()
        with self.assertRaises(PermissionError):
            web.login(code, "https://table.example")
        with self.store.connect() as db:
            self.assertEqual(db.execute("SELECT hash FROM table_sessions").fetchone()[0], digest(token))
        restored = WebTable(Store(self.store.path, self.store.registry), True, "https://table.example")
        self.assertEqual(restored.identity(token)[:3], ("T", "C", "U"))

    def test_web_origin_csrf_and_owner_checks(self):
        web, code, token = self.login()
        state = web.state(token)
        body = {"ritual": state["rituals"]["draw"], "values": values()}
        for origin, csrf in [("null", state["csrf"]), ("https://evil.example", state["csrf"]), ("https://table.example", "wrong")]:
            with self.assertRaises(PermissionError):
                web.action(token, origin, csrf, body)
        self.assertEqual(self.count("shoes"), 0)
        with self.assertRaises(PermissionError):
            web.login(code, "https://evil.example")

    def test_live_browser_and_slack_use_same_shoe_and_repeat_same_reading(self):
        web, _, token = self.login()
        state = web.state(token)
        body = {"ritual": state["rituals"]["draw"], "values": values()}
        first = web.action(token, "https://table.example", state["csrf"], body)
        self.assertEqual(len(first["cards"]), 3)
        self.assertEqual(first, web.action(token, "https://table.example", state["csrf"], body))
        self.assertIn("75 draw / 3 discard", self.store.command("s", "T", "C", "U", "status dawn")["text"])
        state = web.state(token)
        self.store.command("another", "T", "C", "U", "draw dawn")
        response = web.action(token, "https://table.example", state["csrf"], {"ritual": state["rituals"]["draw"], "values": values()})
        self.assertNotIn("cards", response)
        self.assertIn("table has changed", response["surface"]["view"]["blocks"][0]["text"]["text"])

    def test_code_and_session_expiry_and_logout(self):
        web, _, token = self.login()
        state = web.state(token)
        web.logout(token, "https://table.example", state["csrf"])
        with self.assertRaises(PermissionError):
            web.state(token)
        self.assertEqual(self.count("shoes"), 0)
        issued = web.issue("second-code", "T", "C", "U")
        code = issued["text"].split("code in the browser: ")[1].splitlines()[0]
        with self.store.connect() as db:
            db.execute("UPDATE table_codes SET expires=0")
        with self.assertRaises(PermissionError):
            web.login(code, "https://table.example")

    def post(self, path, payload, signed=True):
        body = urllib.parse.urlencode({"payload": json.dumps(payload)}).encode()
        stamp = str(int(time.time()))
        signature = "v0=" + hmac.new(b"secret", b"v0:" + stamp.encode() + b":" + body, hashlib.sha256).hexdigest()
        request = handler(self.store, "secret", "T", "test").__new__(handler(self.store, "secret", "T", "test"))
        request.path = path
        request.headers = {"Content-Length": str(len(body)), "X-Slack-Request-Timestamp": stamp, "X-Slack-Signature": signature if signed else ""}
        request.rfile, request.wfile = io.BytesIO(body), io.BytesIO()
        with patch.object(request, "send_response") as code, patch.object(request, "send_header"), patch.object(request, "end_headers"):
            request.do_POST()
        return code.call_args.args[0], request.wfile.getvalue()

    def test_signed_interaction_open_is_single_use_and_unsigned_rejected(self):
        with self.store.connect() as db:
            sid = self.ui.create(db, "T", "C", "U", "draw")
        payload = {
            "type": "block_actions",
            "team": {"id": "T"},
            "user": {"id": "U"},
            "trigger_id": "trigger",
            "actions": [{"action_id": "ritual_open", "value": sid}],
        }
        self.assertEqual(self.post("/slack/interactions", payload, signed=False)[0], 401)
        with patch("tarot.server.api", return_value={"ok": True}) as api:
            self.assertEqual(self.post("/slack/interactions", payload)[0], 200)
            self.assertEqual(self.post("/slack/interactions", payload)[0], 200)
            self.assertEqual(api.call_count, 1)
        self.assertEqual(self.count("shoes"), 0)

    def test_outbox_handles_home_api_without_message_timestamp(self):
        with self.store.connect() as db:
            db.execute(
                "INSERT INTO outbox(id,payload) VALUES (?,?)",
                ("home", json.dumps({"_method": "views.publish", "user_id": "U", "view": {"type": "home", "blocks": []}})),
            )
        with patch("urllib.request.urlopen", return_value=io.StringIO('{"ok":true,"view":{"id":"V"}}')) as call:
            deliver(self.store, "test")
            self.assertEqual(call.call_args.args[0].full_url, "https://slack.com/api/views.publish")
        with self.store.connect() as db:
            self.assertEqual(db.execute("SELECT status FROM outbox").fetchone()[0], "sent")

    def test_browser_reading_retry_keeps_committed_card_text(self):
        web, _, token = self.login()
        state = web.state(token)
        data = {"ritual": state["rituals"]["draw"], "values": values()}
        first = web.action(token, "https://table.example", state["csrf"], data)
        for card in self.store.registry["cards"]:
            card["meaning"] = "Edited after the reading"
        data["values"] = values("midnight", "single")
        self.assertEqual(first, web.action(token, "https://table.example", state["csrf"], data))

    def test_http_login_cookie_and_mutation_require_verified_session(self):
        web = WebTable(self.store, True, "https://table.example")
        issued = web.issue("wire-code", "T", "C", "U")
        code = issued["text"].split("code in the browser: ")[1].splitlines()[0]
        cls = handler(self.store, "secret", "T", "test", web)
        request = cls.__new__(cls)
        request.path = "/api/login"
        raw = json.dumps({"code": code}).encode()
        request.headers = {"Content-Length": str(len(raw)), "Origin": "https://table.example"}
        request.rfile, request.wfile = io.BytesIO(raw), io.BytesIO()
        with patch.object(request, "send_response") as status, patch.object(request, "send_header") as headers, patch.object(request, "end_headers"):
            request.do_POST()
            status.assert_called_with(200)
        cookie = next(c.args[1] for c in headers.call_args_list if c.args[0] == "Set-Cookie")
        for expected in ("__Host-tarot=", "Secure", "HttpOnly", "SameSite=Strict", "Path=/", "Max-Age=3600"):
            self.assertIn(expected, cookie)
        self.assertNotIn("Domain=", cookie)

    def test_work_object_delivery_strips_internal_marker(self):
        self.store.theme["enable_work_objects"] = True
        self.store.theme["board_directory"] = str(Path(self.store.path).parent / "boards")
        self.store.theme["public_url"] = "https://table.example"
        self.store.command("object-reading", "T", "C", "U", "draw dawn")
        with patch("urllib.request.urlopen", return_value=io.StringIO('{"ok":true,"ts":"1.2"}')) as call:
            deliver(self.store, "test")
        payload = json.loads(call.call_args.args[0].data)
        self.assertNotIn("_reading", payload)
        self.assertEqual(payload["metadata"]["entities"][0]["entity_type"], "slack#/entities/item")

    def test_existing_message_update_reuses_reading_and_strips_internal_fields(self):
        self.store.theme["public_url"] = "https://table.example"
        self.store.theme["board_directory"] = str(Path(self.store.path).parent / "boards")
        saved = self.store.command("saved-reading", "T", "C", "U", "draw crt three")
        with self.store.connect() as db:
            before = db.execute("SELECT * FROM shoes").fetchall()
            payload = dict(saved["payload"], _method="chat.update", ts="1.2")
            db.execute("UPDATE outbox SET payload=? WHERE id=?", (json.dumps(payload), "saved-reading"))
        with patch("urllib.request.urlopen", return_value=io.StringIO('{"ok":true,"ts":"1.2"}')) as call:
            deliver(self.store, "test")
        request = call.call_args.args[0]
        self.assertEqual(request.full_url, "https://slack.com/api/chat.update")
        sent = json.loads(request.data)
        self.assertEqual(sent["ts"], "1.2")
        for internal in ("_reading", "_board", "_method", "client_msg_id"):
            self.assertNotIn(internal, sent)
        self.assertEqual(sum(block["type"] == "image" for block in sent["blocks"]), 1)
        with self.store.connect() as db:
            self.assertEqual(db.execute("SELECT * FROM shoes").fetchall(), before)
            self.assertEqual(json.loads(db.execute("SELECT result FROM requests WHERE id='saved-reading'").fetchone()[0]), saved)

    def test_work_object_public_preview_contains_no_reading_data_or_token(self):
        self.store.command("reading-key", "T", "C", "U", "draw dawn")
        rid = reading_id("reading-key")
        item = entity(rid, "https://table.example", preview=True)
        self.assertEqual(item["entity_payload"]["attributes"]["full_size_preview"]["preview_url"], "https://table.example/embed/table")
        self.assertNotIn("cards", json.dumps(item))
        request = details({"external_ref": {"id": rid, "type": "tarot-reading"}}, {"trigger_id": "event-trigger"}, self.store, "https://table.example")
        self.assertEqual(request["_method"], "entity.presentDetails")
        with self.assertRaises(ValueError):
            details({"external_ref": {"id": "unknown", "type": "tarot-reading"}}, {"trigger_id": "event"}, self.store, "https://table.example")


if __name__ == "__main__":
    unittest.main()
