"""Rebuild original raster geometry placeholders using only Python's stdlib."""

import json
import math
import struct
import zlib
from pathlib import Path


def chunk(kind: bytes, data: bytes) -> bytes:
    return struct.pack("!I", len(data)) + kind + data + struct.pack("!I", zlib.crc32(kind + data))


def main() -> None:
    root = Path(__file__).resolve().parents[1]
    cards = json.loads((root / "registry.json").read_text())["cards"]
    for deck, bg, ink in [("dawn", (248, 238, 219), (142, 73, 60)), ("midnight", (20, 33, 56), (182, 213, 239))]:
        dest = root / "art" / deck
        dest.mkdir(exist_ok=True, parents=True)
        for index, card in enumerate(cards):
            rows = bytearray()
            for y in range(480):
                rows.append(0)
                for x in range(300):
                    radius = math.hypot(x - 150, y - 205)
                    angle = math.atan2(y - 205, x - 150) + index * 0.17
                    star = abs(radius - (70 + 20 * math.cos(3 * angle))) < 2
                    ring = abs(radius - (40 + index % 25)) < 2
                    border = (x in (15, 284) and 15 <= y <= 464) or (y in (15, 464) and 15 <= x <= 284)
                    # Binary constellation near the foot gives each card a distinct signature.
                    mark = 350 <= y <= 360 and any((index + 1) & (1 << bit) and 65 + bit * 25 <= x <= 75 + bit * 25 for bit in range(7))
                    rows.extend(ink if star or ring or border or mark else bg)
            png = b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack("!IIBBBBB", 300, 480, 8, 2, 0, 0, 0))
            png += chunk(b"IDAT", zlib.compress(rows, 9)) + chunk(b"IEND", b"")
            (dest / f"{card['id']}.png").write_bytes(png)


if __name__ == "__main__":
    main()
