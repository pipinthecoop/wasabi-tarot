"""Three review-only CRT surface loops. Artwork pixels never move or deform."""

import hashlib
import json
import math
from pathlib import Path

from PIL import Image, ImageChops, ImageDraw, ImageFilter, ImageSequence

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "preview/crt-surface-samples"
SIZE = (400, 600)
SAMPLES = {
    "major-0": {"frames": 28, "duration": 80, "phase": 0.13, "scan_cycles": 1, "glow": [230, 165, 415, 455]},
    "major-2": {"frames": 32, "duration": 100, "phase": 0.57, "scan_cycles": 1, "glow": [162, 218, 425, 625]},
    "major-16": {"frames": 30, "duration": 90, "phase": 0.82, "scan_cycles": 2, "glow": [215, 162, 478, 505]},
}


def render(cid, spec, size=SIZE, out=OUT):
    scale = size[0] / 600
    original = Image.open(ROOT / "art/crt" / (cid + ".png")).convert("RGB").resize(size, Image.Resampling.LANCZOS)
    # Mask only curved screen glass: case, LEDs, titles and illustration positions
    # remain exactly fixed. This pass only changes phosphor intensity/bloom.
    mask = Image.new("L", size)
    ImageDraw.Draw(mask).rounded_rectangle(tuple(int(v * scale) for v in (43.5, 102, 556.5, 783)), radius=int(40.5 * scale), fill=255)
    mask = mask.filter(ImageFilter.GaussianBlur(4.5 * scale))
    local = Image.new("L", size)
    box = tuple(int(v * scale) for v in spec["glow"])
    ImageDraw.Draw(local).ellipse(box, fill=255)
    local = local.filter(ImageFilter.GaussianBlur(42 * scale))
    bloom = original.filter(ImageFilter.GaussianBlur(0.85))
    frames = []
    for index in range(spec["frames"]):
        t = index / spec["frames"]
        phase = t + spec["phase"]
        # Gentle, nonuniform power/exposure drift. Periodic harmonics give an
        # irregular analog rhythm without a discontinuity at the loop seam.
        harmonics = spec.get("harmonics", (3, 7))
        flicker = 0.017 * math.sin(math.tau * (phase * harmonics[0] + 0.18)) + 0.009 * math.sin(math.tau * (phase * harmonics[1] + 0.61))
        center = (105 + ((phase * spec["scan_cycles"]) % 1) * 675) * scale
        field = Image.new("L", size)
        draw = ImageDraw.Draw(field)
        for y in range(size[1]):
            distance = min(abs(y - center), abs(y - center + 675 * scale), abs(y - center - 675 * scale))
            refresh = spec.get("band_gain", 0.25) * math.exp(-((distance / (36 * scale)) ** 2))
            trailing = 0.095 * math.exp(-(((y - center + 52.5 * scale) / (64.5 * scale)) ** 2))
            fine = 0.035 * math.cos(math.tau * (y / (3.75 * scale) + phase * 2))
            level = int(max(0, min(255, 182 * (1 + flicker + refresh + trailing + fine))))
            draw.line((0, y, size[0], y), fill=level)
        swell_gain = 0.11 * (0.5 + 0.5 * math.sin(math.tau * (phase * spec.get("glow_cycles", 2) + 0.37)))
        field = ImageChops.add(field, local.point(lambda value: int(value / 255 * 182 * swell_gain)))
        brightness = field.point(lambda value: min(255, int(value * 1.1)))
        # Scale the original image by an intensity field. No translations,
        # warps, geometric transforms, subject animation, or fresh glyphs.
        lit = ImageChops.multiply(original, Image.merge("RGB", (brightness, brightness, brightness)))
        lit = lit.point(lambda value: min(255, int(value * 1.28)))
        glow_gain = 0.08 + 0.07 * (0.5 + 0.5 * math.sin(math.tau * (phase * 2 + 0.37)))
        added = bloom.point(lambda value: int(value * glow_gain))
        lit = ImageChops.add(lit, added)
        frames.append(Image.composite(lit, original, mask))
    palette = frames[0].quantize(colors=spec.get("palette", 64), method=Image.Quantize.MEDIANCUT)
    frames = [f.quantize(palette=palette, dither=Image.Dither.NONE) for f in frames]
    path = out / (cid + ".gif")
    frames[0].save(path, save_all=True, append_images=frames[1:], duration=spec["duration"], loop=0, disposal=2, optimize=True)
    with Image.open(path) as gif:
        decoded = [f.convert("RGB").copy() for f in ImageSequence.Iterator(gif)]
        assert gif.n_frames == spec["frames"]
        assert gif.info["loop"] == 0
        assert len({f.tobytes() for f in decoded}) > spec["frames"] // 2
        assert len({f.crop((0, int(size[1] * 0.9), size[0], size[1])).tobytes() for f in decoded}) == 1
    spec.update(
        {"id": cid, "file": path.name, "bytes": path.stat().st_size, "sha256": hashlib.sha256(path.read_bytes()).hexdigest(), "artwork_geometry": "fixed"}
    )
    print(cid, path.stat().st_size, "bytes; fixed geometry / rolling refresh / bloom / gentle flicker", flush=True)
    return decoded


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    sheet = Image.new("RGB", (1200, 680), "#020704")
    draw = ImageDraw.Draw(sheet)
    draw.text((20, 18), "CRT SURFACE STUDIES / THE ARTWORK STAYS STILL", fill="#a9ffd0")
    for i, (cid, spec) in enumerate(SAMPLES.items()):
        frames = render(cid, spec)
        sheet.paste(frames[spec["frames"] // 3], (i * 400, 55))
    sheet.save(OUT / "surface-three-preview.png")
    (OUT / "surface-samples.json").write_text(
        json.dumps({"purpose": "Three samples only, review before scaling", "size": list(SIZE), "palette": 64, "cards": list(SAMPLES.values())}, indent=2)
        + "\n"
    )


if __name__ == "__main__":
    main()
