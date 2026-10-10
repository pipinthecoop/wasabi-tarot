"""Public art coverage and real finite-state integration for Phosphor Arcana."""

import copy
import hashlib
import json
import struct
import tempfile
import unittest
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path

from PIL import Image, ImageChops, ImageSequence

from tarot.core import Store, load_registry
from tarot.ui import Parlor, asset, load_theme

ROOT = Path(__file__).resolve().parents[1]


class CRTTests(unittest.TestCase):
    def test_original_complete_unique_rendered_art(self):
        registry = load_registry(str(ROOT / "registry.json"))
        ids = registry["decks"]["crt"]["cards"]
        self.assertEqual(len(ids), 78)
        self.assertEqual(ids, registry["decks"]["dawn"]["cards"])
        catalogue = json.loads((ROOT / "art/crt/catalogue.json").read_text())["cards"]
        self.assertEqual([c["id"] for c in catalogue], ids)
        self.assertEqual(len({c["scene_sha256"] for c in catalogue}), 78)
        hashes = set()
        for cid in ids + ["back"]:
            png = (ROOT / "art/crt" / f"{cid}.png").read_bytes()
            self.assertEqual(png[:8], b"\x89PNG\r\n\x1a\n")
            self.assertEqual(struct.unpack(">II", png[16:24]), (600, 900))
            self.assertGreater(len(png), 10000)
            hashes.add(hashlib.sha256(png).hexdigest())
            svg = (ROOT / "art/crt" / f"{cid}.svg").read_text()
            self.assertIn('<title id="title">', svg)
            self.assertNotIn("<image", svg)
            self.assertNotIn("http://", svg.replace("http://www.w3.org/2000/svg", ""))
        self.assertEqual(len(hashes), 79)

    def test_adding_crt_preserves_existing_shoe_and_retry(self):
        registry = load_registry(str(ROOT / "registry.json"), "https://cards.example/decks")
        old = copy.deepcopy(registry)
        old["decks"].pop("crt")
        with tempfile.TemporaryDirectory() as temp:
            path = str(Path(temp) / "state.sqlite3")
            store = Store(path, old)
            original = store.command("old", "T", "C", "U", "draw dawn three")
            with store.connect() as db:
                before = db.execute("SELECT * FROM shoes").fetchall()
            store = Store(path, registry)
            crt = store.command("crt", "T", "C", "U", "draw crt three")
            self.assertEqual(store.command("old", "T", "C", "U", "draw dawn three"), original)
            with store.connect() as db:
                self.assertIn(before[0], db.execute("SELECT * FROM shoes").fetchall())
            urls = [b["image_url"] for b in crt["payload"]["blocks"] if b["type"] == "image"]
            self.assertEqual(len(urls), 3)
            for cid, url in zip(crt["cards"], urls):
                self.assertEqual(url, f"https://cards.example/decks/crt/{cid}.gif")

    def test_crt_concurrency_exhaustion_restart_and_explicit_shuffle(self):
        with tempfile.TemporaryDirectory() as temp:
            store = Store(str(Path(temp) / "state.sqlite3"), load_registry(str(ROOT / "registry.json")))
            with ThreadPoolExecutor(max_workers=8) as pool:
                draws = list(pool.map(lambda i: store.command(f"draw-{i}", "T", "C", "U", "draw crt single"), range(78)))
            self.assertEqual(len({draw["cards"][0] for draw in draws}), 78)
            store = Store(store.path, store.registry)
            exhausted = store.command("empty", "T", "C", "U", "draw crt single")
            self.assertTrue(exhausted["error"])
            self.assertIn("Explicitly shuffle", exhausted["text"])
            self.assertEqual(store.command("draw-0", "T", "C", "U", "draw crt single"), draws[0])
            store.command("shuffle", "T", "C", "U", "shuffle crt")
            self.assertIn("78 draw / 0 discard", store.command("status", "T", "C", "U", "status crt")["text"])

    def test_animated_deck_and_static_configuration(self):
        animated = load_registry(str(ROOT / "registry.json"), "https://cards.example")
        static = load_registry(str(ROOT / "registry.json"), "https://cards.example", animated_art=False)
        for a, b in zip(animated["cards"], static["cards"]):
            self.assertEqual(a["art"]["crt"], f"https://cards.example/crt/{a['id']}.gif")
            self.assertEqual(b["art"]["crt"], a["static_art"]["crt"])
            self.assertEqual(a["art"]["dawn"], b["art"]["dawn"])
        invalid = json.loads((ROOT / "registry.json").read_text())
        invalid["decks"]["crt"]["art_format"] = "../private"
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "registry.json"
            path.write_text(json.dumps(invalid))
            with self.assertRaisesRegex(ValueError, "Art format"):
                load_registry(str(path))

    def test_scene_specific_gifs_decode_loop_and_preserve_titles(self):
        specs = json.loads((ROOT / "art/crt/animations.json").read_text())["cards"]
        self.assertEqual(len(specs), 78)
        self.assertEqual(len({json.dumps([s["effects"], s["phase"], s["duration"]]) for s in specs}), 78)
        hashes = set()
        motions = set()
        for spec in specs:
            path = ROOT / "art/crt" / spec["file"]
            blob = path.read_bytes()
            hashes.add(hashlib.sha256(blob).hexdigest())
            self.assertEqual(hashlib.sha256(blob).hexdigest(), spec["sha256"])
            self.assertLess(len(blob), 2_000_000)
            with Image.open(path) as gif:
                self.assertEqual(gif.size, (320, 480))
                self.assertEqual(gif.n_frames, spec["frames"])
                self.assertEqual(gif.info["loop"], 0)
                self.assertEqual(spec["artwork_geometry"], "fixed")
                frames = [frame.convert("RGB").copy() for frame in ImageSequence.Iterator(gif)]
                self.assertGreater(len({f.tobytes() for f in frames}), 8)
                motions.add(hashlib.sha256(ImageChops.difference(frames[0], frames[4]).tobytes()).hexdigest())
                self.assertEqual(len({f.crop((0, 433, 320, 480)).tobytes() for f in frames}), 1)
        self.assertEqual(len(hashes), 78)
        self.assertEqual(len(motions), 78)

    def test_crt_scheduler_retry_and_slack_modal(self):
        with tempfile.TemporaryDirectory() as temp:
            store = Store(
                str(Path(temp) / "state.sqlite3"), load_registry(str(ROOT / "registry.json")), load_theme(str(ROOT / "theme.json"), "https://theme.example")
            )
            store.command("schedule", "T", "C", "U", "schedule 08:00 America/New_York crt single")
            with ThreadPoolExecutor(max_workers=8) as pool:
                list(pool.map(lambda _: store.tick(datetime(2026, 10, 10, 12, tzinfo=timezone.utc)), range(16)))
            with store.connect() as db:
                self.assertEqual(db.execute("SELECT COUNT(*) FROM outbox").fetchone()[0], 1)
            self.assertIn("77 draw / 1 discard", store.command("status", "T", "C", "U", "status crt")["text"])
            modal = Parlor(store).modal("sample", "draw")
            options = next(b["element"]["options"] for b in modal["blocks"] if b.get("block_id") == "deck")
            self.assertIn({"text": {"type": "plain_text", "text": "Phosphor Arcana", "emoji": False}, "value": "crt"}, options)
            self.assertEqual(asset(store.theme, "card_back", "crt"), "https://theme.example/crt-back.png")


if __name__ == "__main__":
    unittest.main()
