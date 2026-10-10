"""Signed slash-command ingress and durable worker. No third-party runtime deps."""

import hashlib
import ipaddress
import hmac
import json
import os
import time
import urllib.error
import urllib.parse
import urllib.request
import uuid
import mimetypes
from http.cookies import SimpleCookie
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from threading import Thread
from pathlib import Path

from tarot.core import Store, load_registry
from tarot.ui import Parlor, load_theme
from tarot.web import WebTable
from tarot.embeds import entity, reading_id, details


def verify(secret: str, stamp: str, signature: str, body: bytes, now: float) -> bool:
    try:
        if abs(now - int(stamp)) > 300:
            return False
    except ValueError:
        return False
    expected = "v0=" + hmac.new(secret.encode(), b"v0:" + stamp.encode() + b":" + body, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, signature)


def deliver(store: Store, token: str) -> bool:
    # A single designated worker owns delivery. Mark before network IO: an ambiguous
    # outcome is quarantined rather than blindly retried and duplicated in Slack.
    with store.connect() as db:
        db.execute("BEGIN IMMEDIATE")
        row = db.execute("SELECT id,payload FROM outbox WHERE status='pending' ORDER BY rowid LIMIT 1").fetchone()
        if not row:
            return False
        db.execute("UPDATE outbox SET status='sending' WHERE id=?", (row[0],))
    payload = json.loads(row[1])
    is_reading = payload.pop("_reading", False)
    method = payload.pop("_method", "chat.postMessage")
    if method not in ("chat.postMessage", "chat.postEphemeral", "views.publish", "entity.presentDetails"):
        raise ValueError("Unsupported outbox method")
    if method == "chat.postMessage":
        payload["client_msg_id"] = str(uuid.uuid5(uuid.NAMESPACE_URL, row[0]))
        if is_reading and store.theme.get("enable_work_objects"):
            payload["metadata"] = {"entities": [entity(reading_id(row[0]), store.theme["public_url"])]}
    req = urllib.request.Request(
        "https://slack.com/api/" + method,
        data=json.dumps(payload).encode(),
        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json; charset=utf-8"},
    )
    status = "uncertain"
    ts: str | None = None
    error: str | None = "Ambiguous network outcome; inspect Slack before retry"
    try:
        with urllib.request.urlopen(req, timeout=20) as response:
            result = json.load(response)
        if result.get("ok"):
            status, ts, error = "sent", result.get("ts"), None
        else:
            status, error = "failed", result.get("error", "unknown_error")
    except urllib.error.HTTPError as exc:
        if exc.code == 429:
            status, error = "pending", "rate_limited"
            time.sleep(min(60, int(exc.headers.get("Retry-After", "30"))))
        else:
            error = f"HTTP {exc.code}; inspect before retry"
    except (OSError, ValueError):
        pass
    with store.connect() as db:
        db.execute("UPDATE outbox SET status=?,ts=?,error=? WHERE id=?", (status, ts, error, row[0]))
    return True


def worker(store: Store, token: str) -> None:
    while True:
        try:
            store.tick(datetime.now(timezone.utc))
            deliver(store, token)
        except Exception as exc:
            # Never print tokens, Slack bodies, or exception payloads.
            print(f"Worker error: {type(exc).__name__}", flush=True)
        time.sleep(1)


def api(token: str, method: str, payload: dict) -> dict:
    request = urllib.request.Request(
        "https://slack.com/api/" + method, data=json.dumps(payload).encode(), headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    )
    with urllib.request.urlopen(request, timeout=1.5) as response:
        result = json.load(response)
    if not result.get("ok"):
        raise ValueError("Slack could not open this surface. Open /tarot again, or use the text commands.")
    return result


def handler(store: Store, secret: str, team: str, token: str = "", web: WebTable | None = None) -> type[BaseHTTPRequestHandler]:
    parlor = Parlor(store)
    table = web or WebTable(store)
    root = Path(__file__).resolve().parents[1]

    def notice(key: str, channel: str, user: str, text: str) -> None:
        with store.connect() as db:
            payload = {"_method": "chat.postEphemeral", "channel": channel, "user": user, "text": text}
            db.execute("INSERT OR IGNORE INTO outbox(id,payload) VALUES (?,?)", (key, json.dumps(payload)))

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, format: str, *args: object) -> None:
            pass

        def respond(self, status: int, value: dict, cookie: str = "") -> None:
            self.send_response(status)
            self.send_header("Content-Type", "application/json")
            self.send_header("Cache-Control", "no-store")
            if cookie:
                self.send_header("Set-Cookie", cookie)
            self.end_headers()
            self.wfile.write(json.dumps(value).encode())

        def browser_token(self) -> str:
            cookies: SimpleCookie = SimpleCookie()
            try:
                cookies.load(self.headers.get("Cookie", ""))
                return cookies["__Host-tarot"].value
            except (KeyError, ValueError):
                return ""

        def do_GET(self) -> None:
            path = urllib.parse.urlsplit(self.path).path
            if path == "/health":
                self.send_response(200)
                self.end_headers()
                return
            if path == "/api/table":
                try:
                    self.respond(200, table.state(self.browser_token()))
                except PermissionError as exc:
                    self.respond(401, {"error": str(exc)})
                return
            # Serve an allowlisted public bundle only; never filesystem paths from requests.
            static = {"/table": root / "web/table.html", "/embed/table": root / "web/table.html"}
            for name in ("table.css", "table.js", "demo.json"):
                static["/web/" + name] = root / "web" / name
            for filename in (root / "art/theme").glob("*"):
                if filename.suffix in (".png", ".webp"):
                    static["/assets/theme/" + filename.name] = filename
            for folder in ("dawn", "midnight", "crt"):
                for filename in (root / "art" / folder).glob("*"):
                    if filename.suffix not in (".png", ".gif"):
                        continue
                    static[f"/assets/decks/{folder}/{filename.name}"] = filename
            file = static.get(path)
            if not file or not file.is_file():
                self.send_response(404)
                self.end_headers()
                return
            self.send_response(200)
            self.send_header("Content-Type", mimetypes.guess_type(file.name)[0] or "application/octet-stream")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.send_header("X-Content-Type-Options", "nosniff")
            self.send_header("Referrer-Policy", "no-referrer")
            self.send_header("Cache-Control", "no-cache")
            ancestors = "https://*.slack.com https://*.slack-gov.com https://*.slack-mcps.com" if path == "/embed/table" else "'none'"
            self.send_header(
                "Content-Security-Policy",
                f"default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' https:; connect-src 'self'; base-uri 'none'; form-action 'self'; frame-ancestors {ancestors}",
            )
            self.end_headers()
            self.wfile.write(file.read_bytes())

        def do_POST(self) -> None:
            if self.path not in ("/slack/commands", "/slack/interactions", "/slack/events", "/api/login", "/api/ritual", "/api/logout"):
                self.send_response(404)
                self.end_headers()
                return
            try:
                length = int(self.headers.get("Content-Length", "0"))
                if not 0 < length <= 65536:
                    raise ValueError("Invalid request size")
            except ValueError:
                self.send_response(413)
                self.end_headers()
                return
            body = self.rfile.read(length)
            if self.path.startswith("/api/"):
                try:
                    data = json.loads(body)
                    origin = self.headers.get("Origin", "")
                    if self.path == "/api/login":
                        session = table.login(data["code"], origin)
                        self.respond(200, {"ok": True}, f"__Host-tarot={session}; Secure; HttpOnly; SameSite=Strict; Path=/; Max-Age=3600")
                    elif self.path == "/api/logout":
                        table.logout(self.browser_token(), origin, self.headers.get("X-CSRF-Token", ""))
                        self.respond(200, {"ok": True}, "__Host-tarot=; Secure; HttpOnly; SameSite=Strict; Path=/; Max-Age=0")
                    else:
                        self.respond(200, table.action(self.browser_token(), origin, self.headers.get("X-CSRF-Token", ""), data))
                except PermissionError as exc:
                    self.respond(403, {"error": str(exc)})
                except (KeyError, ValueError, TypeError):
                    self.respond(400, {"error": "Check your request. No reading was created."})
                except Exception:
                    self.respond(503, {"error": "The table is busy. Retry the same action."})
                return
            if not verify(secret, self.headers.get("X-Slack-Request-Timestamp", ""), self.headers.get("X-Slack-Signature", ""), body, time.time()):
                self.send_response(401)
                self.end_headers()
                return
            try:
                if self.path == "/slack/events":
                    data = json.loads(body)
                    if data.get("type") == "url_verification":
                        self.respond(200, {"challenge": data["challenge"]})
                        return
                    if data.get("team_id") != team:
                        self.respond(403, {})
                        return
                    event = data.get("event", {})
                    if store.theme.get("enable_work_objects") and event.get("type") == "entity_details_requested":
                        payload = details(event, data, store, store.theme["public_url"])
                        with store.connect() as db:
                            claim = db.execute("INSERT OR IGNORE INTO requests VALUES (?,?)", ("entity:" + data["event_id"], '{"attempted":true}')).rowcount
                        if claim:
                            method = payload.pop("_method")
                            api(token, method, payload)
                    self.respond(200, {})
                    return
                fields = {k: v[0] for k, v in urllib.parse.parse_qs(body.decode()).items()}
                if self.path == "/slack/interactions":
                    data = json.loads(fields["payload"])
                    if data.get("team", {}).get("id") != team:
                        self.respond(403, {})
                        return
                    user = data["user"]["id"]
                    kind = data["type"]
                    if kind in ("view_submission", "view_closed"):
                        view = data["view"]
                        if view.get("callback_id") != "ritual_submit":
                            self.respond(400, {})
                            return
                        sid = view["private_metadata"]
                        if kind == "view_closed":
                            parlor.cancel(sid, team, user)
                            self.respond(200, {})
                        else:
                            self.respond(200, parlor.submit(sid, team, user, view["state"]["values"]))
                        return
                    action = data["actions"][0]
                    sid = action["value"]
                    with store.connect() as db:
                        row = parlor.row(db, sid, team, user)
                        channel = row[0]
                    if action["action_id"] == "ritual_stop":
                        outcome = parlor.stop(sid, team, user)
                    elif action["action_id"] in ("ritual_open", "ritual_draw", "ritual_shuffle", "ritual_schedule"):
                        outcome = parlor.open(sid, team, user)
                        if "view" in outcome:
                            try:
                                api(token, "views.open", {"trigger_id": data["trigger_id"], "view": outcome["view"]})
                            except (ValueError, OSError):
                                outcome = {"text": "The table could not open. No cards were consumed. Open /tarot again; text commands still work."}
                    else:
                        raise ValueError("Unknown action")
                    if "view" not in outcome:
                        notice("notice:" + sid, channel, user, outcome["text"])
                    self.respond(200, {})
                    return
                if fields.get("team_id") != team or fields.get("command") != "/tarot":
                    self.send_response(403)
                    self.end_headers()
                    return
                key = f"slash:{team}:{fields['trigger_id']}"
                text = fields.get("text", "").strip()
                if text in ("", "parlor", "home"):
                    result = parlor.panel(key, team, fields["channel_id"], fields["user_id"], home=text == "home")
                    if text == "home":
                        if store.theme.get("enable_home"):
                            with store.connect() as db:
                                db.execute(
                                    "INSERT OR IGNORE INTO outbox(id,payload) VALUES (?,?)",
                                    (
                                        key,
                                        json.dumps(
                                            {"_method": "views.publish", "user_id": fields["user_id"], "view": {"type": "home", "blocks": result["blocks"]}}
                                        ),
                                    ),
                                )
                            result = {"text": "Your personal parlor is opening in the app's Home tab."}
                        else:
                            result["text"] = "App Home is not enabled here; your private parlor controls are below."
                elif text == "table":
                    result = table.issue(key, team, fields["channel_id"], fields["user_id"])
                else:
                    result = store.command(key, team, fields["channel_id"], fields["user_id"], text)
                response = {"response_type": "ephemeral", "text": result["text"]}
                if "blocks" in result:
                    response["blocks"] = result["blocks"]
            except (ValueError, KeyError, TypeError) as exc:
                # Invalid controls get a safe acknowledgment; no arbitrary payload echoes.
                response = {"response_type": "ephemeral", "text": str(exc) if isinstance(exc, ValueError) else "This control is invalid. Open /tarot again."}
            except Exception:
                self.send_response(503)
                self.end_headers()
                return
            self.respond(200, response)

    return Handler


def bind_address() -> tuple[str, int]:
    """Explicit native bind; keep existing container default for compatibility."""
    host = os.environ.get("BIND_HOST", "0.0.0.0")
    ipaddress.ip_address(host)
    port = int(os.environ.get("PORT", "8080"))
    if not 1 <= port <= 65535:
        raise ValueError("PORT must be 1–65535")
    return host, port


def main() -> None:
    for name in ("SLACK_SIGNING_SECRET", "SLACK_TEAM_ID", "SLACK_BOT_TOKEN"):
        if not os.environ.get(name):
            raise ValueError(f"{name} is required")
    if os.environ.get("RUN_WORKER", "1") == "1" and not os.environ.get("SLACK_BOT_TOKEN"):
        raise ValueError("SLACK_BOT_TOKEN is required for worker")
    path = os.environ.get("DATABASE_PATH", "data/tarot.sqlite3")
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    theme = load_theme(os.environ.get("THEME_PATH", "theme.json"), os.environ.get("THEME_ASSET_BASE_URL", ""))
    theme["enable_home"] = os.environ.get("ENABLE_APP_HOME", "0") == "1"
    theme["enable_work_objects"] = os.environ.get("ENABLE_WORK_OBJECTS", "0") == "1"
    theme["public_url"] = os.environ.get("PUBLIC_BASE_URL", "").rstrip("/")
    store = Store(
        path,
        load_registry(os.environ.get("REGISTRY_PATH", "registry.json"), os.environ.get("ART_BASE_URL", ""), os.environ.get("ANIMATED_ART", "1") == "1"),
        theme,
    )
    web = WebTable(store, os.environ.get("ENABLE_WEB_TABLE", "0") == "1", theme["public_url"])
    if theme["enable_work_objects"] and not web.origin:
        raise ValueError("Work Objects require PUBLIC_BASE_URL")
    if os.environ.get("RUN_WORKER", "1") == "1":
        Thread(target=worker, args=(store, os.environ["SLACK_BOT_TOKEN"]), daemon=True).start()
    server = ThreadingHTTPServer(
        bind_address(),
        handler(store, os.environ["SLACK_SIGNING_SECRET"], os.environ["SLACK_TEAM_ID"], os.environ.get("SLACK_BOT_TOKEN", ""), web),
    )
    server.serve_forever()


if __name__ == "__main__":
    main()
