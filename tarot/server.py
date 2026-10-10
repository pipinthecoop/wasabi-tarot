"""Signed slash-command ingress and durable worker. No third-party runtime deps."""

import hashlib
import hmac
import json
import os
import time
import urllib.error
import urllib.parse
import urllib.request
import uuid
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from threading import Thread
from pathlib import Path

from tarot.core import Store, load_registry


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
    payload["client_msg_id"] = str(uuid.uuid5(uuid.NAMESPACE_URL, row[0]))
    req = urllib.request.Request(
        "https://slack.com/api/chat.postMessage",
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
            status, ts, error = "sent", result["ts"], None
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


def handler(store: Store, secret: str, team: str) -> type[BaseHTTPRequestHandler]:
    class Handler(BaseHTTPRequestHandler):
        def log_message(self, format: str, *args: object) -> None:
            pass

        def do_GET(self) -> None:
            self.send_response(200 if self.path == "/health" else 404)
            self.end_headers()

        def do_POST(self) -> None:
            if self.path != "/slack/commands":
                self.send_response(404)
                self.end_headers()
                return
            try:
                length = int(self.headers.get("Content-Length", "0"))
                if not 0 < length <= 16384:
                    raise ValueError("Invalid request size")
            except ValueError:
                self.send_response(413)
                self.end_headers()
                return
            body = self.rfile.read(length)
            if not verify(secret, self.headers.get("X-Slack-Request-Timestamp", ""), self.headers.get("X-Slack-Signature", ""), body, time.time()):
                self.send_response(401)
                self.end_headers()
                return
            try:
                fields = {k: v[0] for k, v in urllib.parse.parse_qs(body.decode()).items()}
                if fields.get("team_id") != team or fields.get("command") != "/tarot":
                    self.send_response(403)
                    self.end_headers()
                    return
                # trigger_id identifies a logical command; HTTP retries preserve it.
                key = f"slash:{team}:{fields['trigger_id']}"
                result = store.command(key, team, fields["channel_id"], fields["user_id"], fields.get("text", ""))
                response = {"response_type": "ephemeral", "text": result["text"]}
            except (ValueError, KeyError) as exc:
                response = {"response_type": "ephemeral", "text": str(exc)}
            except Exception:
                self.send_response(503)
                self.end_headers()
                return
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps(response).encode())

    return Handler


def main() -> None:
    for name in ("SLACK_SIGNING_SECRET", "SLACK_TEAM_ID"):
        if not os.environ.get(name):
            raise ValueError(f"{name} is required")
    if os.environ.get("RUN_WORKER", "1") == "1" and not os.environ.get("SLACK_BOT_TOKEN"):
        raise ValueError("SLACK_BOT_TOKEN is required for worker")
    path = os.environ.get("DATABASE_PATH", "data/tarot.sqlite3")
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    store = Store(path, load_registry(os.environ.get("REGISTRY_PATH", "registry.json"), os.environ.get("ART_BASE_URL", "")))
    if os.environ.get("RUN_WORKER", "1") == "1":
        Thread(target=worker, args=(store, os.environ["SLACK_BOT_TOKEN"]), daemon=True).start()
    server = ThreadingHTTPServer(
        ("0.0.0.0", int(os.environ.get("PORT", "8080"))), handler(store, os.environ["SLACK_SIGNING_SECRET"], os.environ["SLACK_TEAM_ID"])
    )
    server.serve_forever()


if __name__ == "__main__":
    main()
