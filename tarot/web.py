"""Optional live browser table, authenticated through a verified Slack command.

No ambient authorization, URL tokens, public mutations, or embed mutations.
"""

import hashlib
import hmac
import json
import secrets
import time
from urllib.parse import urlsplit

from tarot.core import Store
from tarot.decks import available_decks, default_deck
from tarot.ui import Parlor, asset


def digest(value: str) -> str:
    return hashlib.sha256(value.encode()).hexdigest()


class WebTable:
    def __init__(self, store: Store, enabled: bool = False, public_url: str = ""):
        self.store, self.parlor, self.enabled = store, Parlor(store), enabled
        parsed = urlsplit(public_url)
        if public_url and (
            parsed.scheme != "https"
            or not parsed.netloc
            or parsed.username
            or parsed.password
            or parsed.query
            or parsed.fragment
            or parsed.path not in ("", "/")
        ):
            raise ValueError("PUBLIC_BASE_URL must be an HTTPS origin, without credentials or path")
        if enabled and not public_url:
            raise ValueError("Live web table requires PUBLIC_BASE_URL")
        self.origin = public_url.rstrip("/")
        with store.connect() as db:
            db.executescript("""
            CREATE TABLE IF NOT EXISTS table_codes(hash TEXT PRIMARY KEY, team TEXT, channel TEXT, owner TEXT, expires REAL, used INTEGER DEFAULT 0);
            CREATE TABLE IF NOT EXISTS table_sessions(hash TEXT PRIMARY KEY, team TEXT, channel TEXT, owner TEXT, expires REAL, csrf TEXT);
            """)

    def issue(self, key: str, team: str, channel: str, owner: str) -> dict:
        if not self.enabled:
            return {
                "text": "The illustrated table is in isolated demo mode. Native /tarot controls remain live. "
                + (self.origin + "/table" if self.origin else "Ask Wasabi for the table URL.")
            }
        with self.store.connect() as db:
            db.execute("BEGIN IMMEDIATE")
            old = db.execute("SELECT result FROM requests WHERE id=?", (key,)).fetchone()
            if old:
                return json.loads(old[0])
            code = secrets.token_urlsafe(24)
            db.execute("INSERT INTO table_codes(hash,team,channel,owner,expires) VALUES (?,?,?,?,?)", (digest(code), team, channel, owner, time.time() + 300))
            result = {
                "text": f"Your private table: {self.origin}/table\nEnter this one-time code in the browser: {code}\nExpires in five minutes. This binds the table to this Slack channel. Keep the code private; it never belongs in a URL."
            }
            db.execute("INSERT INTO requests VALUES (?,?)", (key, json.dumps(result)))
            return result

    def login(self, code: str, origin: str) -> str:
        if not self.enabled or origin != self.origin:
            raise PermissionError("Live table is unavailable from this origin")
        with self.store.connect() as db:
            db.execute("BEGIN IMMEDIATE")
            row = db.execute("SELECT team,channel,owner,expires,used FROM table_codes WHERE hash=?", (digest(code),)).fetchone()
            if not row or row[3] < time.time() or row[4]:
                raise PermissionError("Code is invalid, expired, or already used. Run /tarot table again.")
            token = secrets.token_urlsafe(32)
            csrf = secrets.token_urlsafe(24)
            db.execute("UPDATE table_codes SET used=1 WHERE hash=?", (digest(code),))
            db.execute("INSERT INTO table_sessions VALUES (?,?,?,?,?,?)", (digest(token), row[0], row[1], row[2], time.time() + 3600, csrf))
            return token

    def identity(self, token: str) -> tuple:
        if not self.enabled:
            raise PermissionError("Live table is disabled")
        with self.store.connect() as db:
            row = db.execute("SELECT team,channel,owner,expires,csrf FROM table_sessions WHERE hash=?", (digest(token),)).fetchone()
        if not row or row[3] < time.time():
            raise PermissionError("Session ended. Run /tarot table for a new private code.")
        return row

    def state(self, token: str) -> dict:
        team, channel, owner, _, csrf = self.identity(token)
        with self.store.connect() as db:
            db.execute("BEGIN IMMEDIATE")
            rituals = {mode: self.parlor.create(db, team, channel, owner, mode) for mode in ("draw", "shuffle", "schedule")}
            for sid in rituals.values():
                db.execute("UPDATE rituals SET status='open' WHERE id=?", (sid,))
            decks = []
            for did, spec in available_decks(self.store.registry).items():
                row = db.execute("SELECT draw,discard,cycle FROM shoes WHERE scope=?", (json.dumps([team, channel, did]),)).fetchone()
                draw, discard, cycle = (json.loads(row[0]), json.loads(row[1]), row[2]) if row else (spec["cards"], [], 0)
                decks.append(
                    {
                        "id": did,
                        "name": spec.get("name", did),
                        "remaining": len(draw),
                        "discard": len(discard),
                        "cycle": cycle,
                        "changed": bool(row) and set(draw + discard) != set(spec["cards"]),
                    }
                )
            schedules = [
                {"id": sid, **json.loads(raw)}
                for sid, raw in db.execute("SELECT id,spec FROM schedules WHERE enabled=1")
                if json.loads(raw)["team"] == team and json.loads(raw)["channel"] == channel and json.loads(raw)["user"] == owner
            ]
        return {
            "backs": {deck: asset(self.store.theme, "card_back", deck) or "/assets/theme/card-back.webp" for deck in self.store.registry["decks"]},
            "mode": "live",
            "channel": channel,
            "decks": decks,
            "default_deck": default_deck(self.store.registry),
            "spreads": self.store.registry["spreads"],
            "rituals": rituals,
            "csrf": csrf,
            "schedules": schedules,
        }

    def action(self, token: str, origin: str, csrf: str, data: dict) -> dict:
        team, channel, owner, _, expected = self.identity(token)
        if origin != self.origin or not hmac.compare_digest(expected, csrf):
            raise PermissionError("Origin or CSRF check failed")
        sid = data["ritual"]
        if data.get("cancel"):
            self.parlor.cancel(sid, team, owner)
            return {"text": "You left the table. No cards were consumed."}
        outcome = self.parlor.submit(sid, team, owner, data["values"])
        result: dict = {"surface": outcome}
        with self.store.connect() as db:
            request = db.execute("SELECT result FROM requests WHERE id=?", (f"ritual:{sid}",)).fetchone()
        if request:
            reading = json.loads(request[0])
            result["text"] = reading["text"]
            if "cards" in reading:
                result["positions"] = reading["positions"]
                result["cards"] = reading["card_details"]
        return result

    def logout(self, token: str, origin: str, csrf: str) -> None:
        row = self.identity(token)
        if origin != self.origin or not hmac.compare_digest(row[4], csrf):
            raise PermissionError("Origin or CSRF check failed")
        with self.store.connect() as db:
            db.execute("DELETE FROM table_sessions WHERE hash=?", (digest(token),))
