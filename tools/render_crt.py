"""Render original SVG masters with Chromium and make review sheets (QA extra)."""

import argparse
import json
from pathlib import Path

from PIL import Image, ImageDraw
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]


def sheet(ids, name, columns=6):
    width, height = 240, 360
    canvas = Image.new("RGB", (columns * width, ((len(ids) + columns - 1) // columns) * height + 60), "#020b07")
    ImageDraw.Draw(canvas).text((20, 20), "PHOSPHOR ARCANA / ORIGINAL CODE-DRAWN TAROT", fill="#72f9a9")
    for i, cid in enumerate(ids):
        with Image.open(ROOT / "art/crt" / f"{cid}.png") as card:
            canvas.paste(card.resize((width, height), Image.Resampling.LANCZOS), ((i % columns) * width, 60 + (i // columns) * height))
    path = ROOT / "preview" / name
    path.parent.mkdir(exist_ok=True)
    canvas.save(path)
    return str(path)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--sample", action="store_true")
    parser.add_argument("--cards", nargs="+")
    parser.add_argument("--executable")
    args = parser.parse_args()
    catalogue = json.loads((ROOT / "art/crt/catalogue.json").read_text())["cards"]
    ids = [card["id"] for card in catalogue]
    chosen = ["major-0", "major-2", "major-9", "major-16", "cups-seven", "pentacles-nine"] if args.sample else ids + ["back"]
    if args.cards:
        chosen = args.cards
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(executable_path=args.executable)
        page = browser.new_page(viewport={"width": 600, "height": 900}, device_scale_factor=1)
        for cid in chosen:
            svg = (ROOT / "art/crt" / f"{cid}.svg").read_text()
            page.set_content('<html><body style="margin:0;background:#020403">' + svg + "</body></html>")
            page.screenshot(path=str(ROOT / "art/crt" / f"{cid}.png"))
        browser.close()
    if args.sample:
        print(sheet(chosen, "crt-first-look.png", 3))
    else:
        print(sheet(ids, "crt-all-78.png"))
        print(sheet(ids[:22], "crt-major-arcana.png"))
        for suit in ("wands", "cups", "swords", "pentacles"):
            print(sheet([cid for cid in ids if cid.startswith(suit + "-")], f"crt-{suit}.png", 7))


if __name__ == "__main__":
    main()
