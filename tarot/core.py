"""Durable finite shoes, request deduplication and daily schedule occurrences."""

import json
import random
import re
import shlex
from contextlib import contextmanager
from collections.abc import Iterator
import sqlite3
import uuid
from datetime import datetime
from pathlib import Path
from urllib.parse import urlsplit
from zoneinfo import ZoneInfo


class Store:
    def __init__(self, path: str, registry: dict):
        self.path, self.registry = path, registry
        with self.connect() as db:
            db.executescript("""
            PRAGMA journal_mode=WAL;
            CREATE TABLE IF NOT EXISTS shoes(scope TEXT PRIMARY KEY, draw TEXT, discard TEXT, cycle INTEGER);
            CREATE TABLE IF NOT EXISTS requests(id TEXT PRIMARY KEY, result TEXT);
            CREATE TABLE IF NOT EXISTS outbox(id TEXT PRIMARY KEY, payload TEXT, status TEXT DEFAULT 'pending', ts TEXT, error TEXT);
            CREATE TABLE IF NOT EXISTS schedules(id TEXT PRIMARY KEY, spec TEXT, enabled INTEGER DEFAULT 1);
            """)

    @contextmanager
    def connect(self) -> Iterator[sqlite3.Connection]:
        db = sqlite3.connect(self.path, timeout=2)
        db.execute("PRAGMA busy_timeout=2000")
        try:
            with db:
                yield db
        finally:
            db.close()

    def command(self, key: str, team: str, channel: str, user: str, text: str) -> dict:
        args = shlex.split(text)
        action = args[0] if args else "help"
        with self.connect() as db:
            db.execute("BEGIN IMMEDIATE")
            old = db.execute("SELECT result FROM requests WHERE id=?", (key,)).fetchone()
            if old:
                return json.loads(old[0])
            if key.startswith("daily:"):
                enabled = db.execute("SELECT enabled FROM schedules WHERE id=?", (key.split(":")[1],)).fetchone()
                if not enabled or not enabled[0]:
                    return {"text": "Schedule disabled."}
            try:
                result = self.execute(db, team, channel, user, action, args[1:])
            except (ValueError, KeyError) as exc:
                result = {"text": str(exc), "error": True}
                if key.startswith("daily:"):
                    result["payload"] = {"channel": channel, "text": f"Daily tarot: {exc}"}
            db.execute("INSERT INTO requests VALUES (?,?)", (key, json.dumps(result)))
            if "payload" in result:
                db.execute("INSERT INTO outbox(id,payload) VALUES (?,?)", (key, json.dumps(result["payload"])))
            return result

    def execute(self, db: sqlite3.Connection, team: str, channel: str, user: str, action: str, args: list[str]) -> dict:
        if action == "help":
            return {
                "text": 'draw [deck] [spread or "Position|Position"]; decks; spreads; status [deck]; shuffle [deck]; schedule HH:MM IANA-zone [deck] [spread]; schedules; unschedule ID'
            }
        if action in ("decks", "spreads"):
            return {"text": ", ".join(self.registry[action])}
        if action == "schedules":
            rows = db.execute("SELECT id,spec FROM schedules WHERE enabled=1").fetchall()
            return {"text": "\n".join(f"{i}: {s}" for i, s in rows if json.loads(s)["team"] == team and json.loads(s)["channel"] == channel) or "No schedules."}
        if action == "unschedule":
            if len(args) != 1:
                raise ValueError("unschedule requires an ID")
            row = db.execute("SELECT spec FROM schedules WHERE id=?", (args[0],)).fetchone()
            if not row or json.loads(row[0])["user"] != user or json.loads(row[0])["team"] != team:
                raise ValueError("Only the schedule creator can disable it")
            db.execute("UPDATE schedules SET enabled=0 WHERE id=?", (args[0],))
            return {"text": "Schedule disabled."}
        if action == "schedule":
            if len(args) < 2:
                raise ValueError("schedule HH:MM IANA-zone [deck] [spread]")
            if not re.fullmatch(r"(?:[01][0-9]|2[0-3]):[0-5][0-9]", args[0]):
                raise ValueError("Time must be HH:MM in 24-hour format")
            ZoneInfo(args[1])
            deck = args[2] if len(args) > 2 else "dawn"
            spread = args[3] if len(args) > 3 else "single"
            self.selection(deck, spread)
            sid = str(uuid.uuid4())
            spec = dict(team=team, channel=channel, user=user, time=args[0], zone=args[1], deck=deck, spread=spread)
            db.execute("INSERT INTO schedules(id,spec) VALUES (?,?)", (sid, json.dumps(spec)))
            return {"text": f"Daily schedule created: {sid}"}
        if action not in ("draw", "shuffle", "status"):
            raise ValueError("Unknown command; use /tarot help")
        deck = args[0] if args else "dawn"
        spread = args[1] if len(args) > 1 else "single"
        cards, positions = self.selection(deck, spread)
        scope = json.dumps([team, channel, deck])
        row = db.execute("SELECT draw,discard,cycle FROM shoes WHERE scope=?", (scope,)).fetchone()
        draw, discard, cycle = (json.loads(row[0]), json.loads(row[1]), row[2]) if row else (list(cards), [], 0)
        membership_changed = bool(row) and set(draw + discard) != set(cards)
        if membership_changed and action == "draw":
            raise ValueError("Deck membership changed; the existing shoe is preserved. Explicitly shuffle to adopt the new cards, or use a new deck ID.")
        if not row or action == "shuffle":
            draw, discard, cycle = list(cards), [], cycle + 1
            random.SystemRandom().shuffle(draw)
        if action == "draw":
            if len(draw) < len(positions):
                raise ValueError(f"Only {len(draw)} cards remain. Explicitly shuffle before drawing; no cards consumed.")
            picked = [draw.pop() for _ in positions]
            discard.extend(picked)
            lines = [f"{p}: {cards[c]['name']} — {cards[c]['meaning']}" for p, c in zip(positions, picked)]
            payload: dict = {
                "channel": channel,
                "text": f"Tarot · {deck} · cycle {cycle}\n" + "\n".join(lines),
                "blocks": [
                    {"type": "section", "text": {"type": "plain_text", "text": f"{p}: {cards[c]['name']}\n{cards[c]['meaning']}"}}
                    for p, c in zip(positions, picked)
                ],
            }
            for c in picked:
                url = cards[c].get("art", {}).get(deck)
                if url:
                    payload["blocks"].append({"type": "image", "image_url": url, "alt_text": cards[c]["name"]})
            result = {"text": "Reading queued in this channel.", "payload": payload, "cards": picked}
        else:
            notice = " Membership changed; shuffle explicitly to adopt it." if membership_changed and action == "status" else ""
            result = {"text": f"{deck}: {len(draw)} draw / {len(discard)} discard; cycle {cycle}{notice}"}
        db.execute("INSERT OR REPLACE INTO shoes VALUES (?,?,?,?)", (scope, json.dumps(draw), json.dumps(discard), cycle))
        return result

    def selection(self, deck: str, spread: str) -> tuple[dict, list[str]]:
        if deck not in self.registry["decks"]:
            raise ValueError("Unknown deck")
        cards = {c["id"]: c for c in self.registry["cards"] if c["id"] in self.registry["decks"][deck]["cards"]}
        positions = self.registry["spreads"].get(spread, spread.split("|"))
        if not positions or len(positions) > min(10, len(cards)) or any(not p.strip() or len(p) > 100 for p in positions):
            raise ValueError("Spread requires 1–10 nonempty positions within deck size")
        return cards, positions

    def tick(self, now: datetime) -> None:
        if now.tzinfo is None:
            raise ValueError("Aware datetime required")
        with self.connect() as db:
            schedules = db.execute("SELECT id,spec FROM schedules WHERE enabled=1").fetchall()
        for sid, raw in schedules:
            spec = json.loads(raw)
            local = now.astimezone(ZoneInfo(spec["zone"]))
            if local.strftime("%H:%M") < spec["time"]:
                continue
            key = f"daily:{sid}:{local.date()}"
            self.command(key, spec["team"], spec["channel"], spec["user"], shlex.join(["draw", spec["deck"], spec["spread"]]))


def load_registry(path: str, art_base_url: str = "") -> dict:
    data = json.loads(Path(path).read_text())
    ids = [c["id"] for c in data["cards"]]
    if len(ids) != len(set(ids)) or not ids:
        raise ValueError("Card IDs must be unique and nonempty")
    for deck in data["decks"].values():
        if not deck["cards"] or len(deck["cards"]) != len(set(deck["cards"])) or not set(deck["cards"]) <= set(ids):
            raise ValueError("Invalid deck card membership")
    for card in data["cards"]:
        if not card["name"] or len(card["meaning"]) > 1000:
            raise ValueError("Invalid card text")
        if any(not url.startswith("https://") for url in card.get("art", {}).values()):
            raise ValueError("Art URLs must use HTTPS")
    if art_base_url:
        url = urlsplit(art_base_url)
        if url.scheme != "https" or not url.netloc or url.username or url.password or url.query or url.fragment:
            raise ValueError("ART_BASE_URL must be a public HTTPS base URL without credentials/query/fragment")
        for card in data["cards"]:
            for deck in data["decks"]:
                if card["id"] in data["decks"][deck]["cards"]:
                    card.setdefault("art", {}).setdefault(deck, f"{art_base_url.rstrip('/')}/{deck}/{card['id']}.png")
    return data
