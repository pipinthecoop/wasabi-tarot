"""Authored tonal illustrations translated to curved green ASCII phosphor.

Shared tonal renderer and the three approved original studies. The standalone
entry point writes review files only; the full generator uses these scenes.
"""

import hashlib
import html
import math
from pathlib import Path

from PIL import Image, ImageChops, ImageDraw, ImageFilter

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "preview/ascii-studies"
W, H = 480, 640


class Tonal:
    def __init__(self):
        self.image = Image.new("L", (W, H), 0)

    def shape(self, points, light=170, direction="left", edge=0):
        mask = Image.new("L", (W, H))
        ImageDraw.Draw(mask).polygon(points, fill=255)
        bounds = mask.getbbox()
        if not bounds:
            return
        x0, y0, x1, y1 = bounds
        paint = Image.new("L", (W, H))
        pixels = paint.load()
        for y in range(y0, y1):
            for x in range(x0, x1):
                position = (x - x0) / max(1, x1 - x0) if direction == "left" else (y - y0) / max(1, y1 - y0)
                folds = 0.84 + 0.16 * math.sin(x * 0.072 + y * 0.025)
                pixels[x, y] = int(max(0, min(255, light * (1 - position * 0.72) * folds)))
        if edge:
            ImageDraw.Draw(paint).line(points + [points[0]], fill=edge, width=2)
        self.image.paste(paint, (0, 0), mask)

    def line(self, points, light=150, width=2):
        ImageDraw.Draw(self.image).line(points, fill=light, width=width)

    def ellipse(self, bounds, light=150):
        ImageDraw.Draw(self.image).ellipse(bounds, fill=light)

    def glow(self, center, radius, light):
        field = Image.new("L", (W, H))
        draw = ImageDraw.Draw(field)
        x, y = center
        draw.ellipse((x - radius, y - radius, x + radius, y + radius), fill=light)
        self.image = ImageChops.lighter(self.image, field.filter(ImageFilter.GaussianBlur(radius * 0.5)))

    def landscape(self):
        self.shape([(0, 320), (56, 225), (105, 296), (153, 193), (237, 317), (297, 262), (354, 191), (480, 336), (480, 440), (0, 440)], 92)
        self.shape([(0, 404), (78, 336), (131, 411), (241, 327), (322, 413), (418, 326), (480, 420), (480, 527), (0, 527)], 46)
        for x, y in [(153, 193), (354, 191), (56, 225)]:
            self.shape([(x, y), (x - 18, y + 38), (x - 2, y + 26), (x + 18, y + 46)], 152)

    def stars(self):
        for x, y, r in [(28, 57, 2), (103, 26, 1), (214, 53, 2), (426, 89, 1), (338, 17, 2), (38, 155, 1), (290, 102, 1), (453, 198, 2)]:
            self.line([(x - r * 2, y), (x + r * 2, y)], 190, 1)
            self.line([(x, y - r * 3), (x, y + r * 3)], 190, 1)


def fool():
    s = Tonal()
    s.glow((366, 85), 80, 100)
    s.ellipse((325, 44, 407, 126), 198)
    s.ellipse((336, 51, 406, 121), 130)
    s.stars()
    s.landscape()
    # Precipice: luminous exposed strata above an enormous shadow.
    s.shape([(0, 490), (142, 477), (267, 458), (303, 489), (234, 512), (219, 550), (160, 559), (114, 640), (0, 640)], 195, "left")
    for k in range(9):
        s.line([(0, 504 + k * 15), (139 - k * 3, 498 + k * 13), (227 - k * 4, 486 + k * 6)], 35 + k * 3, 2)
    # Sweeping cloak and substantial bent boots; body is modeled with tonal folds.
    s.shape(
        [
            (182, 208),
            (215, 191),
            (248, 222),
            (282, 300),
            (321, 337),
            (289, 361),
            (262, 348),
            (281, 426),
            (240, 459),
            (186, 433),
            (135, 414),
            (157, 352),
            (141, 305),
        ],
        228,
    )
    s.shape([(192, 258), (189, 370), (168, 419), (201, 436), (218, 370), (209, 283)], 87)
    s.shape([(226, 265), (249, 344), (264, 422), (240, 453), (222, 385)], 176)
    s.shape([(182, 426), (202, 429), (203, 470), (229, 482), (216, 496), (178, 475)], 143)
    s.shape([(239, 432), (256, 427), (277, 458), (301, 459), (304, 474), (268, 479), (244, 464)], 195)
    # Face in profile, a blown plume, tangled hair, staff and satchel.
    s.shape([(183, 158), (203, 141), (224, 152), (226, 168), (241, 174), (228, 181), (231, 194), (211, 213), (192, 200)], 235)
    s.shape([(178, 154), (197, 132), (223, 144), (215, 155), (192, 158), (191, 192), (178, 184)], 74)
    s.line([(214, 165), (223, 165)], 32, 3)
    s.line([(219, 188), (228, 186)], 42, 2)
    s.shape([(190, 134), (194, 102), (224, 78), (212, 112)], 188)
    s.line([(133, 227), (321, 152)], 178, 5)
    s.shape([(133, 224), (155, 213), (171, 238), (158, 268), (131, 260), (124, 243)], 161)
    s.shape([(229, 231), (248, 230), (279, 210), (309, 215), (310, 225), (277, 225), (253, 255)], 215)
    s.ellipse((302, 199, 314, 214), 230)
    s.line([(309, 206), (338, 179)], 184, 2)
    s.ellipse((331, 165, 346, 183), 230)
    # Companion dog: raised muzzle, broad body, fur and tail.
    s.shape(
        [
            (91, 435),
            (109, 422),
            (139, 429),
            (153, 411),
            (164, 401),
            (173, 414),
            (169, 426),
            (158, 436),
            (151, 450),
            (130, 458),
            (102, 451),
            (98, 476),
            (86, 475),
        ],
        235,
    )
    s.shape([(142, 450), (154, 449), (163, 478), (151, 480)], 182)
    s.line([(92, 438), (76, 420), (80, 404)], 186, 5)
    s.line([(161, 414), (165, 414)], 25, 2)
    for x in range(98, 145, 5):
        s.line([(x, 434), (x - 5, 449)], 96, 1)
    return s


def priestess():
    s = Tonal()
    s.glow((240, 201), 128, 81)
    # Deep temple, tall pillars in alternating darkness and moonlight.
    for x, intensity in [(21, 130), (373, 100)]:
        s.shape([(x, 64), (x + 75, 64), (x + 68, 566), (x + 8, 566)], intensity)
        s.shape([(x - 7, 43), (x + 83, 43), (x + 83, 69), (x - 7, 69)], 190)
        s.shape([(x - 7, 566), (x + 83, 566), (x + 83, 598), (x - 7, 598)], 172)
        for offset in (15, 29, 43, 57):
            s.line([(x + offset, 81), (x + offset - 3, 547)], 35 if offset % 2 else 107, 3)
    # A patterned veil, pomegranate forms and subtle orbital geometry.
    s.shape([(102, 55), (372, 55), (370, 522), (101, 522)], 42, "top")
    for row in range(5):
        for col in range(5):
            x, y = 120 + col * 49, 94 + row * 75
            s.ellipse((x - 9, y - 10, x + 9, y + 10), 82)
            s.line([(x - 5, y - 13), (x, y - 18), (x + 5, y - 13)], 126, 2)
            s.line([(x, y - 7), (x, y + 8)], 27, 2)
    # Halo and crescent crown, sculptural seated robe; no outline-person anatomy.
    s.ellipse((170, 109, 310, 249), 54)
    s.ellipse((179, 118, 301, 240), 18)
    s.shape(
        [(183, 246), (215, 212), (267, 212), (300, 249), (312, 324), (292, 412), (335, 557), (317, 592), (160, 592), (144, 563), (186, 411), (166, 326)], 222
    )
    for x in range(172, 315, 15):
        s.line([(240 + (x - 240) * 0.31, 328), (x, 570)], 37 + int(abs(x - 240) / 3), 3)
    s.shape([(203, 237), (219, 209), (264, 209), (283, 238), (270, 338), (240, 372), (210, 329)], 87)
    s.shape([(211, 151), (231, 140), (258, 146), (275, 165), (274, 192), (259, 217), (240, 228), (221, 214), (205, 189)], 236)
    s.shape([(204, 149), (226, 133), (263, 140), (281, 159), (286, 234), (272, 216), (269, 171), (258, 151), (225, 158), (208, 223), (193, 235)], 86)
    s.line([(213, 177), (226, 174), (232, 179)], 30, 3)
    s.line([(246, 178), (257, 174), (267, 176)], 32, 3)
    s.line([(239, 179), (236, 194), (242, 196)], 114, 2)
    s.line([(230, 204), (241, 207), (253, 201)], 42, 2)
    s.ellipse((209, 82, 270, 143), 211)
    s.ellipse((215, 71, 266, 125), 24)
    s.ellipse((228, 87, 253, 112), 240)
    s.shape([(207, 133), (270, 133), (276, 148), (203, 148)], 190)
    # Hands cradle an illuminated scroll/book, a bright cross on the chest.
    s.shape([(177, 321), (200, 321), (226, 357), (213, 370), (190, 352)], 215)
    s.shape([(281, 326), (299, 322), (286, 352), (263, 371), (249, 360)], 205)
    s.shape([(191, 361), (247, 353), (293, 363), (290, 393), (239, 384), (192, 396)], 221)
    for y in (367, 374, 381):
        s.line([(203, y), (237, y - 5)], 48, 1)
        s.line([(252, y - 4), (279, y + 1)], 58, 1)
    s.line([(240, 251), (240, 291)], 234, 5)
    s.line([(226, 268), (254, 268)], 234, 5)
    # Moon at the hem, reflective tiled pool.
    s.ellipse((211, 546, 278, 613), 214)
    s.ellipse((226, 535, 285, 591), 10)
    for y in range(606, 640, 8):
        s.line([(100, y), (376, y)], 52, 2)
    return s


def tower():
    s = Tonal()
    # Storm rendered as sweeping light masses, not scattered random glyphs.
    for y in range(0, 215, 22):
        s.shape(
            [
                (0, y + 40),
                (78, y + 7),
                (167, y + 20),
                (247, y),
                (364, y + 17),
                (480, y - 4),
                (480, y + 34),
                (387, y + 49),
                (230, y + 33),
                (80, y + 48),
                (0, y + 68),
            ],
            34 + y // 11,
            "top",
        )
    s.glow((313, 189), 132, 81)
    s.shape([(0, 584), (71, 525), (157, 550), (213, 489), (314, 542), (391, 501), (480, 578), (480, 640), (0, 640)], 118)
    # Massive leaning stone tower with dimensional faces and jagged crown.
    left = [(138, 551), (162, 248), (149, 224), (171, 186), (192, 209), (210, 185), (230, 212), (254, 190), (278, 227), (282, 255), (303, 550)]
    s.shape(left, 200)
    s.shape([(241, 230), (282, 255), (303, 550), (255, 566), (231, 271)], 81)
    s.shape([(157, 249), (232, 244), (255, 566), (137, 551)], 177)
    for y in range(279, 555, 26):
        ratio = (y - 250) / 300
        s.line([(161 - ratio * 20, y), (240 + ratio * 11, y - 4)], 31, 3)
        for x in range(170, 248, 28):
            s.line([(x + (13 if y % 52 else 0), y), (x + (13 if y % 52 else 0), y + 21)], 33, 2)
    for y in (309, 402, 486):
        s.shape([(190, y), (192, y - 13), (201, y - 20), (209, y - 13), (213, y + 29), (187, y + 31)], 8)
        s.line([(188, y + 31), (213, y + 29)], 213, 3)
    # Huge branching electrical rupture and expressive flame tongues.
    s.shape([(404, 0), (289, 138), (341, 130), (226, 251), (285, 162), (247, 174), (359, 30)], 255, edge=255)
    s.line([(320, 106), (228, 88), (197, 117), (123, 92)], 209, 4)
    s.line([(282, 178), (368, 206), (401, 279)], 239, 5)
    s.shape([(148, 250), (113, 224), (129, 188), (118, 164), (151, 194), (163, 233)], 246)
    s.shape([(267, 267), (283, 236), (309, 204), (299, 170), (328, 209), (309, 252), (292, 280)], 239)
    s.shape([(173, 238), (180, 200), (161, 179), (180, 151), (193, 197), (210, 222)], 232)
    # Crown hurled away: a modeled solid shape and particles of masonry.
    s.shape([(321, 115), (339, 105), (338, 80), (355, 94), (370, 72), (376, 98), (398, 88), (395, 116), (372, 142), (342, 137)], 223)
    for x, y in [(131, 282), (329, 297), (111, 356), (354, 386), (290, 191), (85, 491)]:
        s.shape([(x, y), (x + 12, y - 5), (x + 18, y + 9), (x + 4, y + 17)], 188)
    # Two tumbling bodies with flowing clothing, solid limbs and shadowed faces.
    s.shape([(91, 304), (108, 319), (116, 345), (135, 359), (120, 378), (89, 357), (73, 337), (76, 319)], 219)
    s.ellipse((72, 293, 94, 316), 225)
    s.shape([(82, 330), (49, 349), (32, 337), (29, 346), (51, 364), (91, 344)], 175)
    s.shape([(113, 358), (143, 385), (138, 413), (149, 422), (157, 389), (134, 365)], 177)
    s.shape([(354, 372), (372, 358), (392, 366), (415, 410), (393, 425), (367, 398)], 195)
    s.ellipse((368, 337, 390, 359), 200)
    s.shape([(390, 374), (419, 354), (437, 364), (443, 357), (421, 339), (380, 363)], 181)
    s.shape([(389, 417), (362, 444), (348, 469), (359, 477), (375, 453), (409, 427)], 152)
    for y in range(575, 640, 10):
        s.line([(0, y), (480, y - 9)], 25 + (y % 40), 2)
    return s


def ascii_svg(scene, cid, title, number, caption):
    cols, rows = 88, 112
    tone = scene.image.resize((cols, rows), Image.Resampling.LANCZOS)
    ramp = " .,:;irsXA253hMHGS#9B&@"
    cells = []
    for row in range(rows):
        for col in range(cols):
            level = tone.getpixel((col, row))
            level = int(255 * (level / 255) ** 0.78)
            if level < 7:
                continue
            u, v = (col - cols / 2) / (cols / 2), (row - rows / 2) / (rows / 2)
            x = 58 + col * 5.5 - u * v * v * 3.3
            y = 154 + row * 5.4 + v * u * u * 7
            char = ramp[min(len(ramp) - 1, int(level / 255 * (len(ramp) - 1)))]
            # Glyph choice encodes modeled luminance, never random noise.
            intensity = min(255, int(60 + level * 0.77))
            color = f"rgb({int(intensity * 0.56)},{intensity},{int(intensity * 0.69)})"
            cells.append(f'<text x="{x:.2f}" y="{y:.2f}" fill="{color}">{html.escape(char)}</text>')
    chars = "".join(cells)
    svg = f"""<svg xmlns="http://www.w3.org/2000/svg" width="600" height="900" viewBox="0 0 600 900" role="img" aria-labelledby="title desc">
<title id="title">{html.escape(title)} — Phosphor Arcana terminal study</title><desc id="desc">{html.escape(caption)}. Original tonal artwork modeled in code and translated to luminous ASCII character cells on curved CRT glass.</desc>
<defs><radialGradient id="glass"><stop stop-color="#072018"/><stop offset=".74" stop-color="#03140d"/><stop offset="1" stop-color="#010603"/></radialGradient>
<linearGradient id="case" x2=".4" y2="1"><stop stop-color="#2c342c"/><stop offset=".1" stop-color="#121912"/><stop offset=".6" stop-color="#050805"/><stop offset="1" stop-color="#202920"/></linearGradient>
<radialGradient id="shade"><stop offset=".55" stop-color="#000" stop-opacity="0"/><stop offset="1" stop-color="#000" stop-opacity=".8"/></radialGradient>
<linearGradient id="reflection" x2=".8" y2="1"><stop stop-color="#b4ffd1" stop-opacity=".06"/><stop offset=".4" stop-color="#b4ffd1" stop-opacity="0"/></linearGradient>
<pattern id="scan" width="2" height="3" patternUnits="userSpaceOnUse"><rect y="2" width="2" height="1" fill="#000" opacity=".3"/></pattern>
<filter id="bloom"><feGaussianBlur stdDeviation="1.1"/></filter><clipPath id="screen"><path d="M43 133 Q46 106 77 102 Q300 92 524 104 Q554 107 557 136 Q568 452 552 746 Q550 772 525 779 Q300 791 77 779 Q49 775 47 747 Q32 440 43 133Z"/></clipPath></defs>
<rect width="600" height="900" rx="31" fill="#020403"/><rect x="9" y="9" width="582" height="882" rx="27" fill="url(#case)" stroke="#3a493d"/>
<path d="M27 121 Q27 89 68 84 Q300 71 537 85 Q575 89 576 125 L571 759 Q570 797 536 802 Q300 813 67 800 Q29 796 28 759Z" fill="#010402" stroke="#34483a" stroke-width="3"/>
<g clip-path="url(#screen)"><rect x="30" y="90" width="540" height="710" fill="url(#glass)"/>
<g font-family="Menlo,monospace" font-size="8.3" font-weight="bold" opacity=".72" filter="url(#bloom)">{chars}</g>
<g font-family="Menlo,monospace" font-size="8.3" font-weight="bold">{chars}</g>
<rect x="30" y="90" width="540" height="710" fill="url(#scan)"/><rect x="30" y="90" width="540" height="710" fill="url(#shade)"/>
<path d="M45 107 Q285 81 549 108 L523 259 Q300 169 45 219Z" fill="url(#reflection)"/>
<text x="61" y="129" fill="#569b70" font-family="Menlo,monospace" font-size="8.5">ARCANA / VT-78     {number}     SIGNAL LOCKED</text>
<text x="61" y="769" fill="#60b880" font-family="Menlo,monospace" font-size="8">&gt; {html.escape(caption.upper())}</text></g>
<text x="32" y="49" font-family="Menlo,monospace" font-size="11" letter-spacing="2" fill="#839584">PHOSPHOR / ARCANA</text>
<circle cx="546" cy="46" r="3" fill="#8dffc1"/><circle cx="546" cy="46" r="6" fill="#8dffc1" opacity=".45" filter="url(#bloom)"/>
<text x="300" y="844" text-anchor="middle" font-family="Georgia,serif" font-size="27" fill="#cfffe0">{html.escape(title)}</text>
<text x="300" y="871" text-anchor="middle" font-family="Menlo,monospace" font-size="9" letter-spacing="2" fill="#728677">{number} / {cid.upper()} / ORIGINAL TERMINAL ART</text></svg>"""
    return svg, chars


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    for cid, title, number, caption, build in [
        ("major-0", "The Fool", "00", "The edge is an invitation", fool),
        ("major-2", "The High Priestess", "II", "Listen beneath the signal", priestess),
        ("major-16", "The Tower", "XVI", "The false walls cannot hold", tower),
    ]:
        scene = build()
        svg, chars = ascii_svg(scene, cid, title, number, caption)
        (OUT / f"{cid}.svg").write_text(svg)
        scene.image.save(OUT / f"{cid}-tonal.png")
        print(cid, "distinct tonal field", hashlib.sha256(chars.encode()).hexdigest()[:16])


if __name__ == "__main__":
    main()
