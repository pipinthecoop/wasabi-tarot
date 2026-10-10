"""Native Slack surfaces and durable, owner-bound, single-use rituals."""

import hashlib
import json
import shlex
import time
import uuid
from pathlib import Path
from typing import TYPE_CHECKING
from urllib.parse import urlsplit

if TYPE_CHECKING:
    from tarot.core import Store


def plain(text: str) -> dict:
    return {"type": "plain_text", "text": text, "emoji": False}


def section(text: str) -> dict:
    return {"type": "section", "text": plain(text)}


def button(label: str, action: str, value: str, style: str = "") -> dict:
    item = {"type": "button", "text": plain(label), "action_id": action, "value": value, "accessibility_label": label}
    if style:
        item["style"] = style
    return item


def image(url: str, alt: str) -> dict:
    return {"type": "image", "image_url": url, "alt_text": alt[:2000]}


def load_theme(path: str = "theme.json", base_url: str = "") -> dict:
    theme = json.loads(Path(path).read_text()) if Path(path).is_file() else {"name": "The Midnight Parlor", "assets": {}}
    if theme.get("reading_layout", "classic") not in ("classic", "carousel"):
        raise ValueError("reading_layout must be classic or carousel")
    if base_url:
        parsed = urlsplit(base_url)
        if parsed.scheme != "https" or not parsed.netloc or parsed.username or parsed.password or parsed.query or parsed.fragment:
            raise ValueError("Theme asset base must be public HTTPS without credentials, query or fragment")
    if not isinstance(theme.get("name", "The Midnight Parlor"), str) or len(theme.get("name", "")) > 100:
        raise ValueError("Theme name must fit native Slack headers")
    collections = [theme.get("assets", {})] + list(theme.get("deck_assets", {}).values())
    for collection in collections:
        for source in collection.values():
            if not isinstance(source, str):
                raise ValueError("Theme asset paths must be strings")
            parsed = urlsplit(source)
            if source.startswith("https://"):
                if not parsed.netloc or parsed.username or parsed.password or parsed.query or parsed.fragment:
                    raise ValueError("Theme assets must be public HTTPS URLs without credentials/query/fragment")
            elif "/" in source or not source.endswith((".png", ".webp", ".jpg", ".jpeg")):
                raise ValueError("Relative theme assets must be image basenames")
    theme["base_url"] = base_url.rstrip("/")
    return theme


def asset(theme: dict, key: str, deck: str = "") -> str:
    source = theme.get("deck_assets", {}).get(deck, {}).get(key) or theme.get("assets", {}).get(key, "")
    if not source:
        return ""
    if source.startswith("https://"):
        return source
    return f"{theme['base_url']}/{source}" if theme.get("base_url") else ""


def snapshot(db, registry: dict, team: str, channel: str, deck: str) -> str:
    scope = json.dumps([team, channel, deck])
    row = db.execute("SELECT draw,discard,cycle FROM shoes WHERE scope=?", (scope,)).fetchone()
    value = json.dumps([list(row) if row else None, sorted(registry["decks"][deck]["cards"])])
    return hashlib.sha256(value.encode()).hexdigest()


def reading(theme: dict, registry: dict, channel: str, deck: str, positions: list[str], picked: list[str], cycle: int, remaining: int) -> dict:
    cards = {c["id"]: c for c in registry["cards"]}
    title = theme.get("name", "The Midnight Parlor")
    name = registry["decks"][deck].get("name", deck)
    lines = [f"{p}: {cards[c]['name']} — {cards[c]['meaning']}" for p, c in zip(positions, picked)]
    text = f"{title} · {name} · cycle {cycle}\n" + "\n".join(lines) + f"\n{remaining} cards remain. Reflection, not certainty."
    blocks = [{"type": "header", "text": plain("✦ Your reading is revealed")}, section(f"{name} · Cycle {cycle}\nTake a breath. Notice what meets you here.")]
    hero = asset(theme, "spread", deck)
    if hero:
        blocks.append(image(hero, "Ritual illustration: three face-down celestial gold cards on midnight velvet; revealed cards are described below."))
    if theme.get("reading_layout") == "carousel":
        elements = []
        for position, cid in zip(positions, picked):
            card = cards[cid]
            item = {"type": "card", "title": plain(card["name"][:150]), "subtitle": plain(position[:150]), "body": plain(card["meaning"][:200])}
            url = card.get("art", {}).get(deck)
            if url:
                item["hero_image"] = image(url, f"{position}: {card['name']}")
            elements.append(item)
        blocks.append({"type": "carousel", "elements": elements})
        # Keep every meaning available as full, visible, accessible text.
        blocks.extend(section(line) for line in lines)
    else:
        for position, cid in zip(positions, picked):
            card = cards[cid]
            blocks.append({"type": "divider"})
            blocks.append(section(f"{position}\n{card['name']}\n{card['meaning']}"))
            url = card.get("art", {}).get(deck)
            if url:
                blocks.append(image(url, f"{position}: {card['name']}"))
    blocks.append(
        {
            "type": "context",
            "elements": [plain(f"{remaining} in draw · {len(registry['decks'][deck]['cards']) - remaining} in discard · No automatic reshuffle")],
        }
    )
    blocks.append(section("Keep what resonates. Leave the rest.\nReply in a thread, add a reaction, or open /tarot for another ritual."))
    return {"channel": channel, "text": text, "blocks": blocks, "unfurl_links": False, "unfurl_media": False, "_reading": True}


class Parlor:
    def __init__(self, store: "Store"):
        self.store = store
        with store.connect() as db:
            db.execute(
                "CREATE TABLE IF NOT EXISTS rituals(id TEXT PRIMARY KEY, team TEXT, channel TEXT, owner TEXT, mode TEXT, snapshots TEXT, expires REAL, status TEXT, result TEXT)"
            )

    def create(self, db, team: str, channel: str, user: str, mode: str) -> str:
        sid = str(uuid.uuid4())
        snapshots = {deck: snapshot(db, self.store.registry, team, channel, deck) for deck in self.store.registry["decks"]}
        db.execute("INSERT INTO rituals VALUES (?,?,?,?,?,?,?,'ready',NULL)", (sid, team, channel, user, mode, json.dumps(snapshots), time.time() + 3600))
        return sid

    def panel(self, key: str, team: str, channel: str, user: str, home: bool = False) -> dict:
        with self.store.connect() as db:
            db.execute("BEGIN IMMEDIATE")
            previous = db.execute("SELECT result FROM requests WHERE id=?", (key,)).fetchone()
            if previous:
                return json.loads(previous[0])
            ids = {mode: self.create(db, team, channel, user, mode) for mode in ("draw", "shuffle", "schedule")}
            theme = self.store.theme
            blocks = [{"type": "header", "text": plain("✦ " + theme.get("name", "The Midnight Parlor"))}]
            hero = asset(theme, "header") or asset(theme, "spread")
            if hero:
                blocks.append(image(hero, "The Midnight Parlor: antique gold celestial ornament on deep ink-blue velvet."))
            blocks.append(section(theme.get("tagline", "A quiet table. A question held. A possible path.")))
            blocks.append(
                section(
                    "Choose your deck and a shape for your question.\nDraw from a finite shared deck. Every card rests in discard until you explicitly shuffle."
                )
            )
            blocks.append(
                {
                    "type": "actions",
                    "elements": [
                        button("Draw a reading", "ritual_draw", ids["draw"], "primary"),
                        button("Shuffle deck", "ritual_shuffle", ids["shuffle"]),
                        button("Daily ritual", "ritual_schedule", ids["schedule"]),
                    ],
                }
            )
            if home:
                with self.store.connect() as reader:
                    rows = reader.execute("SELECT id,spec FROM schedules WHERE enabled=1").fetchall()
                blocks.extend([{"type": "divider"}, {"type": "header", "text": plain("Your daily rituals")}])
                specs = [(sid, json.loads(raw)) for sid, raw in rows if json.loads(raw)["team"] == team and json.loads(raw)["user"] == user]
                for sid, spec in specs[:12]:
                    cancel = self.create(db, team, spec["channel"], user, "unschedule:" + sid)
                    blocks.append(
                        {
                            "type": "section",
                            "text": plain(f"{spec['time']} · {spec['zone']}\n{spec['deck']} / {spec['spread']} · channel {spec['channel']}"),
                            "accessory": button("End daily ritual", "ritual_stop", cancel),
                        }
                    )
                if not specs:
                    blocks.append(section("No daily rituals yet. Choose Daily ritual to begin."))
                blocks.append(
                    section(
                        f"These controls open a ritual for channel {channel}. To choose another channel, run /tarot home there.\nUse /tarot schedules to list all channel rituals."
                    )
                )
            else:
                blocks.append({"type": "context", "elements": [plain("Your private controls · One hour to begin · Draws appear as normal channel messages")]})
                blocks.append(
                    section("A custom spread can be any 1–10 positions.\nDaily rituals honor your local time zone. /tarot home opens your personal parlor.")
                )
            result = {"text": "The Midnight Parlor is open. Choose Draw a reading, Shuffle deck, or Daily ritual.", "blocks": blocks}
            db.execute("INSERT INTO requests VALUES (?,?)", (key, json.dumps(result)))
            return result

    def row(self, db, sid: str, team: str, user: str):
        row = db.execute("SELECT channel,mode,snapshots,expires,status,result FROM rituals WHERE id=? AND team=? AND owner=?", (sid, team, user)).fetchone()
        if not row:
            raise ValueError("This ritual belongs to another reader. Open /tarot for your own table.")
        if row[4] not in ("done", "cancelled") and row[3] < time.time():
            raise ValueError("This table has closed. Open /tarot for fresh controls.")
        return row

    def open(self, sid: str, team: str, user: str) -> dict:
        with self.store.connect() as db:
            db.execute("BEGIN IMMEDIATE")
            row = self.row(db, sid, team, user)
            if row[4] != "ready":
                return {"text": "This ritual is already open or complete. Return to its modal, or open /tarot again."}
            db.execute("UPDATE rituals SET status='open' WHERE id=?", (sid,))
            return {"view": self.modal(sid, row[1]), "text": "Your ritual is opening."}

    def modal(self, sid: str, mode: str) -> dict:
        registry = self.store.registry
        options = [{"text": plain(v.get("name", k)[:75]), "value": k} for k, v in list(registry["decks"].items())[:100]]
        defaults = next(iter(registry["decks"]))
        blocks = []
        hero = asset(self.store.theme, "header")
        if hero:
            blocks.append(image(hero, "Midnight velvet and antique gold celestial ornament."))
        copy = {
            "draw": "Hold your question lightly. Choose a deck, then let the cards offer a perspective.",
            "shuffle": "Begin a new cycle. This returns EVERY card, including discard, to this channel's deck. It also adopts any changed card membership.",
            "schedule": "Make a little room for reflection each day. Your finite channel deck is shared with other readers.",
        }
        blocks.append(section(copy[mode]))
        blocks.append(
            {
                "type": "input",
                "block_id": "deck",
                "label": plain("Art deck"),
                "element": {
                    "type": "static_select",
                    "action_id": "value",
                    "options": options,
                    "initial_option": next(o for o in options if o["value"] == defaults),
                },
            }
        )
        if mode != "shuffle":
            spreads = [{"text": plain(k.title()[:75]), "value": k} for k in list(registry["spreads"])[:100]]
            blocks.append(
                {
                    "type": "input",
                    "block_id": "spread",
                    "label": plain("Spread"),
                    "element": {"type": "static_select", "action_id": "value", "options": spreads, "initial_option": spreads[0]},
                }
            )
            blocks.append(
                {
                    "type": "input",
                    "optional": True,
                    "block_id": "custom",
                    "label": plain("Custom positions (optional)"),
                    "hint": plain("Overrides the chosen spread. Separate 1–10 positions with |."),
                    "element": {
                        "type": "plain_text_input",
                        "action_id": "value",
                        "placeholder": plain("Situation | What to release | Next step"),
                        "max_length": 1000,
                    },
                }
            )
        if mode == "schedule":
            blocks.extend(
                [
                    {
                        "type": "input",
                        "block_id": "time",
                        "label": plain("Daily time"),
                        "element": {"type": "timepicker", "action_id": "value", "initial_time": "08:00"},
                    },
                    {
                        "type": "input",
                        "block_id": "zone",
                        "label": plain("IANA time zone"),
                        "hint": plain("For example America/New_York, Europe/London, or UTC. Handles daylight saving time."),
                        "element": {"type": "plain_text_input", "action_id": "value", "initial_value": "UTC", "max_length": 100},
                    },
                ]
            )
        blocks.append({"type": "context", "elements": [plain("No cards are consumed until you submit. Cancel leaves the deck untouched.")]})
        return {
            "type": "modal",
            "callback_id": "ritual_submit",
            "private_metadata": sid,
            "notify_on_close": True,
            "title": plain("Midnight Parlor"),
            "submit": plain({"draw": "Reveal cards", "shuffle": "Shuffle all cards", "schedule": "Begin daily ritual"}[mode]),
            "close": plain("Leave the table"),
            "blocks": blocks,
        }

    def cancel(self, sid: str, team: str, user: str) -> None:
        with self.store.connect() as db:
            db.execute("BEGIN IMMEDIATE")
            row = self.row(db, sid, team, user)
            if row[4] not in ("done", "cancelled"):
                db.execute("UPDATE rituals SET status='cancelled' WHERE id=?", (sid,))

    def submit(self, sid: str, team: str, user: str, values: dict) -> dict:
        # Single-use ritual ID deduplicates distinct click timestamps and retries.
        # Existing command keys preserve deduplication through restart as well.
        with self.store.connect() as db:
            db.execute("BEGIN IMMEDIATE")
            row = self.row(db, sid, team, user)
            if row[4] == "done":
                return json.loads(row[5])
            if row[4] != "open":
                return {"response_action": "errors", "errors": {"deck": "This ritual was cancelled or never opened. Open /tarot again."}}
            mode = row[1]
            try:
                deck = values["deck"]["value"]["selected_option"]["value"]
                spread = (values.get("custom", {}).get("value", {}).get("value") or "").strip() or values.get("spread", {}).get("value", {}).get(
                    "selected_option", {}
                ).get("value", "single")
                self.store.selection(deck, spread)
                if mode == "schedule":
                    clock = values["time"]["value"]["selected_time"]
                    zone = values["zone"]["value"]["value"].strip()
                    import re
                    from zoneinfo import ZoneInfo

                    if not re.fullmatch(r"(?:[01][0-9]|2[0-3]):[0-5][0-9]", clock):
                        return {"response_action": "errors", "errors": {"time": "Choose a valid daily time."}}
                    try:
                        ZoneInfo(zone)
                    except (ValueError, KeyError):
                        return {"response_action": "errors", "errors": {"zone": "Use a valid IANA zone such as America/New_York or UTC."}}
                    command = shlex.join([mode, clock, zone, deck, spread])
                else:
                    command = shlex.join([mode, deck, spread])
                    if json.loads(row[2]).get(deck) != snapshot(db, self.store.registry, team, row[0], deck):
                        result = {
                            "response_action": "update",
                            "view": self.receipt(
                                "The table has changed",
                                "Another reader drew or shuffled, or the deck registry changed. No cards were consumed. Open /tarot again for a fresh table.",
                            ),
                        }
                        db.execute("UPDATE rituals SET status='done',result=? WHERE id=?", (json.dumps(result), sid))
                        return result
            except (ValueError, KeyError, TypeError):
                return {"response_action": "errors", "errors": {"deck": "Check the deck and spread. Use 1–10 nonempty positions, up to 100 characters each."}}
            # Reserve while holding the DB transaction; execute in this same transaction.
            try:
                args = shlex.split(command)
                outcome = self.store.execute(db, team, row[0], user, args[0], args[1:])
            except (ValueError, KeyError) as exc:
                outcome = {"text": str(exc), "error": True}
            key = f"ritual:{sid}"
            db.execute("INSERT INTO requests VALUES (?,?)", (key, json.dumps(outcome)))
            if "payload" in outcome:
                db.execute("INSERT INTO outbox(id,payload) VALUES (?,?)", (key, json.dumps(outcome["payload"])))
            text = outcome["text"]
            if mode == "draw" and not outcome.get("error"):
                text = "Your cards are revealed and queued for the channel. Reply to the reading in a thread or add a reaction."
            result = {"response_action": "update", "view": self.receipt("✦ " + ("Ritual complete" if not outcome.get("error") else "The deck rests"), text)}
            db.execute("UPDATE rituals SET status='done',result=? WHERE id=?", (json.dumps(result), sid))
            return result

    def stop(self, sid: str, team: str, user: str) -> dict:
        with self.store.connect() as db:
            db.execute("BEGIN IMMEDIATE")
            row = self.row(db, sid, team, user)
            if row[4] == "done":
                return json.loads(row[5])
            if row[4] != "ready" or not row[1].startswith("unschedule:"):
                raise ValueError("This control is no longer available.")
            outcome = self.store.execute(db, team, row[0], user, "unschedule", [row[1].split(":", 1)[1]])
            db.execute("UPDATE rituals SET status='done',result=? WHERE id=?", (json.dumps(outcome), sid))
            return outcome

    @staticmethod
    def receipt(title: str, text: str) -> dict:
        return {
            "type": "modal",
            "title": plain("Midnight Parlor"),
            "close": plain("Close"),
            "blocks": [{"type": "header", "text": plain(title)}, section(text)],
        }
