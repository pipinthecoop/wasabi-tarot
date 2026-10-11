"""Compose immutable, unlisted reading boards from original local card art."""

import math
import os
import re
import tempfile
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


def font(size: int):
    for candidate in ("/System/Library/Fonts/Supplemental/Georgia.ttf", "/usr/share/fonts/truetype/dejavu/DejaVuSerif.ttf"):
        if Path(candidate).is_file():
            return ImageFont.truetype(candidate, size)
    return ImageFont.load_default(size=size)


def render_board(spec: dict, registry: dict, directory: Path, art: Path) -> Path:
    token, deck = spec["token"], spec["deck"]
    ids, positions = spec["cards"], spec["positions"]
    if not re.fullmatch(r"[0-9a-f]{32}", token) or not re.fullmatch(r"[a-z0-9_-]+", deck):
        raise ValueError("Invalid board identity")
    if not 1 <= len(ids) <= 10 or len(ids) != len(positions) or len(set(ids)) != len(ids):
        raise ValueError("Invalid board spread")
    cards = {card["id"]: card for card in registry["cards"]}
    for cid in ids:
        if cid not in registry["decks"][deck]["cards"] or not re.fullmatch(r"[a-z0-9_-]+", cid):
            raise ValueError("Unknown card")
    directory.mkdir(mode=0o700, parents=True, exist_ok=True)
    target = directory / f"{token}.png"
    if target.is_file():
        with Image.open(target) as existing:
            existing.verify()
        return target
    columns = min(3, len(ids))
    rows = math.ceil(len(ids) / columns)
    width, height = columns * 570 + 120, rows * 910 + 270
    canvas = Image.new("RGB", (width, height), "#0b1428")
    draw = ImageDraw.Draw(canvas)
    gold, ivory = "#caa86a", "#f4ead6"
    draw.rounded_rectangle((24, 24, width-25, height-25), radius=30, outline=gold, width=3)
    draw.text((width/2, 66), "THE MIDNIGHT PARLOR", font=font(30), fill=gold, anchor="mt")
    def label(value: str, x: float, y: int, size: int, max_width: int, color: str):
        while size > 15 and draw.textlength(value, font=font(size)) > max_width:
            size -= 1
        # Position labels are user supplied and bounded by the spread parser.
        while draw.textlength(value, font=font(size)) > max_width:
            value = value[:-2] + "…"
        draw.text((x, y), value, font=font(size), fill=color, anchor="mt")
    label(spec["spread"], width/2, 112, 46, width-160, ivory)
    for index, (cid, position) in enumerate(zip(ids, positions)):
        row, column = divmod(index, columns)
        count = min(columns, len(ids)-row*columns)
        x = int((width-count*570)/2 + column*570 + 35)
        y = 230 + row*910
        label(position, x+250, y-50, 34, 520, gold)
        draw.rounded_rectangle((x-9, y-9, x+509, y+759), radius=15, fill="#16243c", outline=gold, width=2)
        with Image.open(art / deck / f"{cid}.png") as card:
            canvas.paste(card.convert("RGB").resize((500, 750), Image.Resampling.LANCZOS), (x, y))
        label(cards[cid]["name"], x+250, y+785, 32, 520, ivory)
    draw.text((width/2, height-65), "A question held. A possible path.", font=font(25), fill=gold, anchor="mt")
    descriptor, temporary = tempfile.mkstemp(prefix=".board-", suffix=".png", dir=directory)
    try:
        with os.fdopen(descriptor, "wb") as stream:
            canvas.save(stream, format="PNG")
        os.replace(temporary, target)
    finally:
        Path(temporary).unlink(missing_ok=True)
    return target
