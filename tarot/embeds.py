"""Opt-in Work Objects adapter. Embedded content is public demo artwork only."""

import hashlib
import time


ENTITY_TYPE = "slack#/entities/item"


def entity(reading_id: str, origin: str, preview: bool = False) -> dict:
    # Stable reading identity is not an authorization token and exposes no reading.
    attributes: dict = {
        "title": {"text": "The Midnight Parlor · Tarot reading"},
        "product_name": "Wasabi Tarot",
        "full_size_preview": {"is_supported": True, "mime_type": "application/vnd.slack-embed"},
    }
    if preview:
        attributes["full_size_preview"]["preview_url"] = origin + "/embed/table"
        attributes["metadata_last_modified"] = int(time.time())
    return {
        "entity_type": ENTITY_TYPE,
        "url": origin + "/table#reading-" + reading_id,
        "external_ref": {"id": reading_id, "type": "tarot-reading"},
        "entity_payload": {"attributes": attributes, "fields": {}},
    }


def reading_id(key: str) -> str:
    return hashlib.sha256(key.encode()).hexdigest()[:32]


def details(event: dict, body: dict, store, origin: str) -> dict:
    external = event.get("external_ref", {})
    rid = external.get("id", "")
    if external.get("type") != "tarot-reading" or event.get("entity_type", ENTITY_TYPE) != ENTITY_TYPE:
        raise ValueError("Unsupported entity")
    with store.connect() as db:
        known = any(reading_id(row[0]) == rid for row in db.execute("SELECT id FROM outbox"))
    if not known:
        raise ValueError("Unknown reading entity")
    return {"_method": "entity.presentDetails", "trigger_id": body["trigger_id"], "metadata": entity(rid, origin, preview=True)}
