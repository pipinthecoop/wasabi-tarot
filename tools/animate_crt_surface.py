"""Accepted fixed-artwork CRT luminance treatment across all 78 cards."""

import copy
import hashlib
import json
from pathlib import Path

from crt_motion_regions import recipe as scene_recipe
from crt_surface_samples import SAMPLES, render

ROOT = Path(__file__).resolve().parents[1]


def recipe(cid):
    seed = int(hashlib.sha256(cid.encode()).hexdigest()[:8], 16)
    if cid in SAMPLES:
        spec = copy.deepcopy(SAMPLES[cid])
        spec["frames"] = 22 + seed % 3
    else:
        regions = scene_recipe(cid)["effects"]
        region = regions[seed % len(regions)][1]
        x0, y0, x1, y1 = region
        # Meaningful subject light regions converted from tonal coordinates
        # into the approved monitor's coordinates. Geometry never moves.
        spec = {
            "frames": 22 + seed % 3,
            "duration": 90 + seed % 5 * 10,
            "phase": (seed % 997) / 997,
            "scan_cycles": 1 + seed % 2,
            "glow": [58 + x0 * 1.008, 154 + y0 * 0.945, 58 + x1 * 1.008, 154 + y1 * 0.945],
        }
    spec.update(
        {
            "harmonics": [2 + seed % 4, 7 + seed % 5],
            "glow_cycles": 1 + seed % 3,
            "band_gain": 0.22 + seed % 7 * 0.01,
            "size": [320, 480],
            "palette": 48,
            "effects": ["rolling refresh", "scanlines", "gentle irregular luminance", "localized phosphor bloom", "persistence trail"],
            "seed": seed,
            "artwork_geometry": "fixed",
        }
    )
    return spec


def main():
    out = ROOT / "art/crt"
    cards = json.loads((ROOT / "registry.json").read_text())["decks"]["crt"]["cards"]
    specs = []
    for cid in cards:
        spec = recipe(cid)
        render(cid, spec, size=(320, 480), out=out)
        specs.append(spec)
    assert len({json.dumps([s["phase"], s["harmonics"], s["glow"], s["duration"]]) for s in specs}) == 78
    (out / "animations.json").write_text(
        json.dumps({"loop": 0, "palette_colors": 48, "style": "Approved realistic CRT surface; illustration geometry fixed", "cards": specs}, indent=2) + "\n"
    )
    print("78 fixed-geometry CRT surface loops finished.")


if __name__ == "__main__":
    main()
