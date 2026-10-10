"""Complete authored tonal tarot compositions for the Phosphor Arcana terminal."""

import hashlib
import json
import math
from pathlib import Path

from PIL import Image

from crt_ascii_studies import Tonal, ascii_svg, fool, priestess, tower
from crt_catalogue import MAJOR_MOTTOS, MINOR_MOTTOS, RANKS, ROMANS

ROOT = Path(__file__).resolve().parents[1]


def poly(s, x, y, scale, pts, light=190):
    s.shape([(x + a * scale, y + b * scale) for a, b in pts], light)


def actor(s, x, y, scale=1, pose="stand", crown=False, light=205):
    """Clothed solid figure with modeled face, hair, sleeves, hands and folds."""
    if pose == "seat":
        body = [(-21, -161), (-42, -140), (-40, -95), (-61, -44), (-52, -9), (55, -9), (65, -44), (37, -103), (34, -140), (17, -163)]
    elif pose == "kneel":
        body = [(-21, -161), (-39, -135), (-24, -79), (-43, -45), (-71, -20), (-61, -7), (66, -7), (56, -28), (24, -63), (29, -139), (15, -162)]
    elif pose == "walk":
        body = [(-21, -162), (-38, -138), (-24, -89), (-56, -37), (-14, -21), (11, -47), (49, -29), (63, -45), (26, -93), (30, -138), (16, -163)]
    else:
        body = [(-21, -162), (-37, -138), (-32, -89), (-52, -12), (-24, -4), (4, -10), (27, -3), (50, -12), (30, -94), (31, -140), (18, -163)]
    poly(s, x, y, scale, body, light)
    for offset in (-27, -14, 2, 15, 28):
        s.line([(x + offset * 0.35 * scale, y - 127 * scale), (x + offset * scale, y - 20 * scale)], max(36, int(light * 0.31)), max(1, int(3 * scale)))
    if pose == "walk":
        poly(s, x, y, scale, [(-12, -27), (-21, -8), (-48, 3), (-39, 11), (-7, 5), (7, -19)], light * 0.75)
        poly(s, x, y, scale, [(24, -33), (45, -20), (63, -9), (61, 2), (44, 0), (16, -14)], light * 0.9)
    elif pose not in ("seat", "kneel"):
        poly(s, x, y, scale, [(-21, -12), (-24, 3), (-38, 5), (-39, 12), (-13, 13), (-4, -9)], light * 0.72)
        poly(s, x, y, scale, [(13, -10), (15, 5), (35, 7), (38, 14), (8, 14), (3, -10)], light * 0.91)
    # Head has a plane of nose and eye-sockets, rather than an icon face.
    poly(s, x, y, scale, [(-21, -194), (-13, -209), (9, -207), (22, -194), (20, -173), (10, -160), (-3, -157), (-17, -171)], light + 22)
    poly(
        s, x, y, scale, [(-22, -195), (-17, -211), (4, -216), (23, -200), (24, -180), (15, -187), (8, -202), (-9, -198), (-15, -174), (-24, -165)], light * 0.38
    )
    s.line([(x - 12 * scale, y - 186 * scale), (x - 3 * scale, y - 188 * scale)], 28, max(1, int(2 * scale)))
    s.line([(x + 6 * scale, y - 187 * scale), (x + 15 * scale, y - 186 * scale)], 25, max(1, int(2 * scale)))
    s.line([(x + scale, y - 185 * scale), (x - 2 * scale, y - 174 * scale), (x + 3 * scale, y - 173 * scale)], 100, max(1, int(2 * scale)))
    s.line([(x - 6 * scale, y - 167 * scale), (x + 6 * scale, y - 166 * scale)], 40, max(1, int(2 * scale)))
    if pose in ("raise", "pray"):
        poly(s, x, y, scale, [(-27, -145), (-42, -135), (-61, -177), (-51, -191), (-33, -159)], light * 0.9)
        poly(s, x, y, scale, [(24, -144), (39, -135), (67, -182), (55, -194), (31, -162)], light * 0.85)
        s.ellipse((x - 57 * scale, y - 203 * scale, x - 46 * scale, y - 186 * scale), 225)
        s.ellipse((x + 52 * scale, y - 206 * scale, x + 63 * scale, y - 188 * scale), 225)
    elif pose == "bound":
        for k in (0, 10, 20):
            s.line([(x - 29 * scale, y + (-123 + k) * scale), (x + 27 * scale, y + (-113 + k) * scale)], 193, max(1, int(3 * scale)))
        s.line([(x - 17 * scale, y - 187 * scale), (x + 18 * scale, y - 184 * scale)], 206, max(1, int(6 * scale)))
    elif pose == "grief":
        poly(s, x, y, scale, [(-29, -141), (-42, -119), (-25, -151), (-9, -174), (0, -167), (-14, -130)], light * 0.85)
        poly(s, x, y, scale, [(25, -139), (39, -115), (28, -149), (12, -173), (3, -166), (17, -131)], light * 0.85)
    else:
        poly(s, x, y, scale, [(-28, -142), (-43, -123), (-45, -83), (-32, -80), (-24, -122)], light * 0.76)
        poly(s, x, y, scale, [(27, -144), (42, -120), (36, -87), (23, -91), (28, -120)], light * 0.82)
        s.ellipse((x - 42 * scale, y - 87 * scale, x - 29 * scale, y - 74 * scale), 215)
        s.ellipse((x + 24 * scale, y - 94 * scale, x + 37 * scale, y - 80 * scale), 219)
    if crown:
        poly(s, x, y, scale, [(-21, -207), (-26, -233), (-9, -222), (0, -240), (10, -221), (26, -231), (22, -207)], 231)
    return s


def orb(s, x, y, r=32, moon=False, light=210):
    s.glow((x, y), r * 1.8, 56)
    s.ellipse((x - r, y - r, x + r, y + r), light)
    if moon:
        s.ellipse((x - r * 0.38, y - r * 1.2, x + r * 1.18, y + r * 0.52), 8)
    else:
        s.ellipse((x - r * 0.58, y - r * 0.58, x + r * 0.6, y + r * 0.6), int(light * 0.7))
        for angle in range(0, 360, 30):
            a = math.radians(angle)
            s.line([(x + math.cos(a) * r * 1.15, y + math.sin(a) * r * 1.15), (x + math.cos(a) * r * 1.55, y + math.sin(a) * r * 1.55)], 180, 2)


def star(s, x, y, r=18):
    pts = []
    for i in range(16):
        a = i * math.pi / 8 - math.pi / 2
        rad = r if i % 2 == 0 else r * 0.22
        pts.append((x + math.cos(a) * rad, y + math.sin(a) * rad))
    s.shape(pts, 255, edge=245)


def waves(s, start=390, light=95):
    for i, y in enumerate(range(start, 640, 12)):
        pts = [(x, y + math.sin(x * 0.023 + i * 0.75) * 8) for x in range(0, 481, 6)]
        s.line(pts, max(18, light - i * 2), 4 if i % 3 == 0 else 2)


def garden(s):
    s.shape([(0, 481), (59, 455), (167, 480), (275, 436), (388, 465), (480, 450), (480, 640), (0, 640)], 85)
    for i in range(29):
        x = 12 + i * 17
        y = 543 + math.sin(i * 1.72) * 46
        s.line([(x, 640), (x + 4, y)], 80 + i % 4 * 15, 3)
        for k in range(3):
            a = x + 4
            b = y + k * 19
            s.shape([(a, b), (a - 14, b - 10), (a - 18, b - 21), (a - 5, b - 17), (a + 3, b + 5)], 112)
            s.shape([(a, b + 8), (a + 15, b - 1), (a + 20, b - 16), (a + 6, b - 11)], 151)


def tree(s, x, y, scale=1):
    poly(s, x, y, scale, [(-20, 0), (-10, -148), (-38, -194), (-29, -200), (0, -156), (26, -200), (34, -194), (10, -139), (22, 0)], 115)
    for dx, dy, r in [(-40, -197, 51), (28, -211, 58), (-12, -247, 57), (64, -177, 46), (-71, -167, 46), (4, -176, 67)]:
        s.ellipse((x + (dx - r) * scale, y + (dy - r) * scale, x + (dx + r) * scale, y + (dy + r) * scale), 68 + int(abs(dx) * 0.6))
        for k in range(3):
            s.line([(x + (dx - r * 0.6) * scale, y + (dy + k * 9) * scale), (x + (dx + r * 0.7) * scale, y + (dy - 7 + k * 9) * scale)], 40, 2)


def architecture(s, style="arch"):
    s.glow((240, 225), 180, 42)
    if style == "city":
        for i in range(11):
            x = i * 46
            top = 201 + ((i * 47) % 113)
            s.shape([(x, top), (x + 32, top - 17), (x + 37, 484), (x, 484)], 69 + i % 4 * 19)
            for y in range(top + 28, 461, 30):
                for xx in (x + 7, x + 22):
                    s.shape([(xx, y), (xx + 5, y), (xx + 5, y + 10), (xx, y + 10)], 18)
    else:
        s.shape([(60, 520), (60, 142), (118, 142), (118, 520)], 113)
        s.shape([(362, 520), (362, 142), (420, 142), (420, 520)], 138)
        s.shape(
            [
                (54, 153),
                (102, 89),
                (176, 39),
                (240, 23),
                (310, 44),
                (380, 92),
                (427, 152),
                (391, 166),
                (358, 117),
                (294, 72),
                (240, 56),
                (181, 76),
                (126, 120),
                (91, 167),
            ],
            161,
        )
        for x in (73, 87, 102, 375, 389, 404):
            s.line([(x, 172), (x, 500)], 37, 3)
    for y in range(510, 640, 22):
        s.line([(0, y), (480, y)], 52, 3)
    for x in range(-220, 721, 60):
        s.line([(240, 445), (x, 640)], 40, 2)


def throne(s, x=240, y=566, scale=1):
    poly(s, x, y, scale, [(-91, 0), (-91, -320), (-68, -351), (65, -351), (94, -324), (94, 0)], 117)
    poly(s, x, y, scale, [(-70, -22), (-70, -307), (70, -307), (70, -22)], 35)
    for dx in (-94, 76):
        poly(s, x, y, scale, [(dx, 0), (dx, -111), (dx + 20, -127), (dx + 29, -112), (dx + 29, 0)], 173)
    for dx in (-72, 72):
        s.ellipse((x + (dx - 10) * scale, y - 334 * scale, x + (dx + 10) * scale, y - 314 * scale), 191)


def cup(s, x, y, scale=1, spilled=False):
    if spilled:
        poly(s, x, y, scale, [(-26, -9), (-25, -29), (12, -30), (20, -14), (7, 9), (-17, 6)], 205)
        s.line([(x + 20 * scale, y), (x + 51 * scale, y + 10 * scale)], 157, 3)
        return
    poly(s, x, y, scale, [(-26, -39), (-21, -14), (-9, -3), (10, -3), (21, -16), (25, -39)], 228)
    s.ellipse((x - 26 * scale, y - 43 * scale, x + 26 * scale, y - 31 * scale), 224)
    s.ellipse((x - 21 * scale, y - 40 * scale, x + 21 * scale, y - 34 * scale), 35)
    poly(s, x, y, scale, [(-4, -5), (-4, 17), (-20, 23), (-20, 27), (21, 27), (21, 23), (5, 17), (5, -5)], 193)
    s.line(
        [(x - 23 * scale, y - 31 * scale), (x - 34 * scale, y - 28 * scale), (x - 30 * scale, y - 12 * scale), (x - 15 * scale, y - 10 * scale)],
        177,
        max(1, int(3 * scale)),
    )
    s.line(
        [(x + 23 * scale, y - 31 * scale), (x + 34 * scale, y - 28 * scale), (x + 30 * scale, y - 12 * scale), (x + 15 * scale, y - 10 * scale)],
        177,
        max(1, int(3 * scale)),
    )


def wand(s, x, y, scale=1, angle=0):
    a = math.radians(angle)

    def point(dx, dy):
        return (x + (dx * math.cos(a) - dy * math.sin(a)) * scale, y + (dx * math.sin(a) + dy * math.cos(a)) * scale)

    s.shape([point(-5, 0), point(-4, -158), point(3, -180), point(7, -159), point(5, 0)], 198)
    for k in range(4):
        for flip in (-1, 1):
            yoff = -40 - k * 32
            s.shape([point(0, yoff), point(flip * 13, yoff - 3), point(flip * 27, yoff - 20), point(flip * 11, yoff - 18)], 171)


def sword(s, x, y, scale=1, angle=0):
    a = math.radians(angle)

    def point(dx, dy):
        return (x + (dx * math.cos(a) - dy * math.sin(a)) * scale, y + (dx * math.sin(a) + dy * math.cos(a)) * scale)

    s.shape([point(-8, -36), point(-7, -165), point(0, -194), point(8, -165), point(8, -36)], 241)
    s.shape([point(0, -192), point(8, -165), point(8, -36), point(0, -36)], 118)
    s.shape([point(-27, -42), point(-27, -33), point(-5, -29), point(-5, -4), point(5, -4), point(5, -29), point(27, -33), point(27, -42)], 205)
    px, py = point(0, 0)
    s.ellipse((px - 8 * scale, py - 8 * scale, px + 8 * scale, py + 8 * scale), 205)


def coin(s, x, y, r=25):
    s.ellipse((x - r, y - r, x + r, y + r), 211)
    s.ellipse((x - r * 0.83, y - r * 0.83, x + r * 0.83, y + r * 0.83), 46)
    pts = [(x + math.sin(i * math.tau / 5) * r * 0.72, y - math.cos(i * math.tau / 5) * r * 0.72) for i in (0, 2, 4, 1, 3, 0)]
    s.line(pts, 230, max(2, int(r / 12)))
    s.ellipse((x - r * 0.98, y - r * 0.98, x - r * 0.67, y - r * 0.67), 234)


def symbol(s, suit, x, y, scale=1, angle=0):
    if suit == "wands":
        wand(s, x, y, scale, angle)
    elif suit == "cups":
        cup(s, x, y, scale)
    elif suit == "swords":
        sword(s, x, y, scale, angle)
    else:
        coin(s, x, y, 29 * scale)


def horse(s, x, y, scale=1, charge=False):
    poly(
        s,
        x,
        y,
        scale,
        [
            (-93, -80),
            (-64, -112),
            (16, -113),
            (45, -143),
            (50, -190),
            (66, -201),
            (86, -188),
            (90, -164),
            (72, -150),
            (68, -107),
            (42, -61),
            (-62, -56),
            (-82, -73),
        ],
        204,
    )
    poly(s, x, y, scale, [(-61, -61), (-52, -45), (-66, 9), (-91, 18), (-92, 6), (-79, -5), (-76, -64)], 142)
    poly(s, x, y, scale, [(26, -67), (46, -62), (56, -25), (82, -7), (82, 5), (56, 2), (34, -20)], 181)
    poly(s, x, y, scale, [(-8, -60), (12, -60), (-1, -7), (20, 9), (11, 17), (-19, 7), (-17, -15)], 118)
    poly(s, x, y, scale, [(61, -112), (82, -132), (104, -91), (122, -100), (125, -89), (107, -77), (84, -96)], 196)
    s.line([(x + 76 * scale, y - 182 * scale), (x + 80 * scale, y - 181 * scale)], 18, max(2, int(3 * scale)))
    poly(s, x, y, scale, [(53, -195), (43, -180), (32, -146), (43, -128), (52, -153), (62, -180)], 75)
    for k in range(6):
        s.line([(x - 86 * scale, y + (-84 + k * 4) * scale), (x - 124 * scale, y + (-107 + k * 7) * scale)], 98, 3)
    if charge:
        for k in range(7):
            s.line([(0, y - 170 + k * 21), (x - 105 * scale, y - 181 + k * 21)], 42 + k * 3, 2)


def bird(s, x, y, scale=1):
    poly(s, x, y, scale, [(0, 6), (-11, -7), (-39, -15), (-73, -51), (-34, -39), (-8, -21), (1, -35), (9, -23), (27, -36), (70, -50), (37, -9), (12, 3)], 187)
    s.ellipse((x - 5 * scale, y - 35 * scale, x + 7 * scale, y - 22 * scale), 226)


def base(kind="land"):
    s = Tonal()
    s.stars()
    if kind == "land":
        s.landscape()
    elif kind == "water":
        waves(s, 347, 83)
    elif kind == "garden":
        garden(s)
    elif kind in ("arch", "city"):
        architecture(s, kind)
    return s


def major(index):
    if index == 0:
        return fool()
    if index == 2:
        return priestess()
    if index == 16:
        return tower()
    s = base(
        {
            1: "garden",
            3: "garden",
            4: "land",
            5: "arch",
            6: "land",
            7: "city",
            8: "garden",
            9: "land",
            10: "water",
            11: "arch",
            12: "garden",
            13: "land",
            14: "water",
            15: "arch",
            17: "water",
            18: "water",
            19: "garden",
            20: "water",
            21: "land",
        }[index]
    )
    if index == 1:
        s.glow((238, 160), 92, 54)
        actor(s, 240, 513, 1.38, "raise")
        s.shape([(107, 388), (373, 388), (396, 431), (87, 431)], 211)
        s.shape([(104, 431), (122, 431), (122, 595), (104, 595)], 154)
        s.shape([(350, 431), (368, 431), (368, 595), (350, 595)], 156)
        cup(s, 172, 384, 0.56)
        coin(s, 286, 404, 22)
        sword(s, 346, 391, 0.62, 90)
        wand(s, 126, 402, 0.54, 64)
        s.line([(206, 156), (219, 147), (236, 155), (251, 162), (272, 155), (275, 146), (261, 142), (246, 151), (230, 163), (212, 163), (206, 156)], 233, 3)
    elif index == 3:
        tree(s, 52, 445, 0.9)
        tree(s, 431, 464, 0.83)
        throne(s, 247, 560, 1.0)
        actor(s, 247, 566, 1.33, "seat", True)
        orb(s, 372, 111, 36)
        coin(s, 157, 487, 37)
        for x in range(80, 423, 24):
            s.line([(x, 640), (x - 6, 549)], 149, 2)
            for k in range(4):
                s.ellipse((x - 13, 541 + k * 11, x - 2, 554 + k * 11), 195 - k * 17)
    elif index == 4:
        throne(s, 240, 566, 1.15)
        actor(s, 240, 572, 1.42, "seat", True)
        sword(s, 354, 487, 0.95)
        coin(s, 123, 452, 29)
        for x in (141, 340):
            s.ellipse((x - 23, 188, x + 23, 232), 178)
            s.ellipse((x - 12, 197, x + 12, 219), 21)
        s.shape([(214, 356), (264, 356), (277, 425), (236, 450), (205, 420)], 156)
    elif index == 5:
        throne(s, 240, 506, 0.84)
        actor(s, 240, 515, 1.3, "seat", True)
        wand(s, 341, 416, 1.4)
        actor(s, 133, 625, 0.62, "kneel", light=158)
        actor(s, 347, 625, 0.62, "kneel", light=142)
        for x in (218, 263):
            s.ellipse((x - 14, 540, x + 14, 568), 186)
            s.line([(x, 564), (x, 607), (x + 14, 607)], 195, 6)
    elif index == 6:
        tree(s, 44, 511, 0.9)
        tree(s, 433, 513, 0.95)
        actor(s, 135, 582, 1.1, "stand", light=225)
        actor(s, 342, 582, 1.1, "stand", light=201)
        bird(s, 240, 162, 2.1)
        orb(s, 240, 83, 29)
        s.glow((240, 148), 122, 55)
        for x in (419, 435, 448):
            s.ellipse((x - 9, 376, x + 9, 394), 234)
    elif index == 7:
        s.shape([(105, 215), (374, 215), (393, 263), (88, 263)], 182)
        s.shape([(108, 263), (116, 263), (116, 423), (108, 423)], 184)
        s.shape([(367, 263), (375, 263), (375, 423), (367, 423)], 184)
        for x in range(121, 373, 32):
            star(s, x, 239, 8)
        actor(s, 240, 431, 0.94, "seat", True)
        horse(s, 153, 591, 0.85)
        horse(s, 346, 595, 0.85)
        s.shape([(151, 409), (329, 409), (339, 491), (146, 491)], 147)
        coin(s, 242, 455, 29)
    elif index == 8:
        actor(s, 232, 542, 1.33, "stand", light=227)
        s.shape([(149, 557), (165, 506), (241, 484), (314, 508), (339, 547), (319, 573), (164, 578)], 159)
        s.ellipse((291, 453, 375, 537), 172)
        s.ellipse((307, 466, 361, 523), 218)
        for x in (176, 231, 308):
            s.shape([(x, 559), (x + 10, 559), (x + 13, 614), (x - 5, 615)], 156)
        s.line([(333, 483), (339, 483)], 23, 3)
        s.line([(330, 509), (348, 510)], 35, 3)
        s.line([(170, 88), (184, 77), (204, 88), (222, 101), (240, 88), (238, 76), (222, 75), (204, 92), (185, 102), (173, 94), (170, 88)], 209, 3)
    elif index == 9:
        s.shape([(0, 640), (82, 547), (155, 593), (249, 485), (346, 596), (480, 640)], 171)
        actor(s, 249, 506, 1.49, "stand", light=150)
        s.shape([(209, 184), (239, 164), (267, 179), (278, 204), (267, 240), (219, 250), (202, 217)], 118)
        s.line([(197, 271), (175, 570)], 208, 6)
        s.shape([(300, 213), (348, 213), (348, 280), (300, 280)], 127)
        star(s, 324, 245, 17)
        s.glow((324, 245), 53, 111)
        orb(s, 88, 71, 25, True)
    elif index == 10:
        for r, value in ((169, 151), (156, 32), (125, 190), (118, 15), (66, 156), (58, 20)):
            s.ellipse((240 - r, 311 - r, 240 + r, 311 + r), value)
        for i in range(12):
            a = i * math.tau / 12
            s.line([(240 + math.cos(a) * 61, 311 + math.sin(a) * 61), (240 + math.cos(a) * 123, 311 + math.sin(a) * 123)], 173, 6)
            coin(s, 240 + math.cos(a) * 164, 311 + math.sin(a) * 164, 9)
        bird(s, 73, 109, 0.7)
        bird(s, 405, 109, 0.7)
        star(s, 76, 530, 27)
        star(s, 408, 530, 27)
    elif index == 11:
        throne(s, 240, 562, 1)
        actor(s, 240, 567, 1.35, "seat", True)
        sword(s, 346, 477, 1.27)
        s.line([(129, 306), (129, 394)], 205, 5)
        s.line([(73, 327), (186, 327)], 206, 5)
        for x in (76, 180):
            s.line([(x, 327), (x - 24, 392), (x + 24, 392), (x, 327)], 178, 2)
            s.shape([(x - 26, 393), (x + 26, 393), (x + 14, 407), (x - 14, 407)], 200)
    elif index == 12:
        tree(s, 95, 604, 1.8)
        tree(s, 404, 602, 1.75)
        s.line([(110, 174), (390, 172)], 192, 15)
        figure = Tonal()
        actor(figure, 240, 430, 1.05, "walk", light=229)
        patch = figure.image.crop((158, 180, 325, 450)).rotate(180)
        s.image.paste(patch, (160, 217), patch.point(lambda v: 255 if v else 0))
        s.line([(238, 177), (238, 246)], 220, 6)
        orb(s, 240, 450, 26)
    elif index == 13:
        orb(s, 392, 168, 32)
        horse(s, 223, 564, 1.52)
        actor(s, 215, 389, 1.0, "seat", light=225)
        s.shape([(196, 177), (231, 177), (237, 205), (230, 218), (200, 218), (188, 204)], 174)
        s.ellipse((197, 191, 208, 202), 10)
        s.ellipse((217, 189, 228, 201), 10)
        s.line([(301, 270), (316, 516)], 189, 5)
        s.shape([(302, 239), (415, 223), (425, 321), (308, 321)], 64)
        star(s, 367, 276, 30)
        coin(s, 105, 611, 23)
    elif index == 14:
        bird(s, 241, 253, 2.64)
        actor(s, 238, 565, 1.44, "stand", light=223)
        cup(s, 152, 381, 0.86)
        cup(s, 329, 401, 0.86)
        s.line([(169, 360), (185, 373), (270, 392), (310, 398)], 239, 5)
        s.shape([(199, 573), (279, 573), (308, 612), (171, 612)], 112)
        orb(s, 238, 111, 24)
    elif index == 15:
        throne(s, 240, 510, 1.0)
        bird(s, 240, 262, 2.65)
        actor(s, 240, 474, 1.28, "seat", light=193)
        s.shape([(220, 202), (198, 177), (190, 136), (212, 169), (226, 175)], 217)
        s.shape([(255, 204), (279, 177), (292, 137), (269, 162), (254, 176)], 211)
        actor(s, 103, 620, 0.7, "stand", light=139)
        actor(s, 373, 620, 0.7, "stand", light=157)
        for flip, x in ((-1, 118), (1, 354)):
            pts = [(x + k * flip * 9, 510 + math.sin(k * 0.32) * 16 + k * 2) for k in range(13)]
            s.line(pts, 175, 3)
        star(s, 240, 80, 26)
    elif index == 17:
        for x, y, r in [(240, 77, 47), (69, 162, 15), (138, 47, 13), (370, 137, 15), (405, 59, 12), (338, 244, 13), (107, 276, 14), (441, 300, 10)]:
            star(s, x, y, r)
        actor(s, 228, 570, 1.1, "kneel", light=233)
        cup(s, 145, 475, 0.68, True)
        cup(s, 327, 480, 0.75, True)
        s.line([(157, 487), (192, 524), (203, 583)], 227, 5)
        s.line([(336, 487), (367, 532), (418, 547)], 221, 5)
        s.shape([(0, 552), (80, 519), (153, 577), (222, 601), (0, 640)], 90)
    elif index == 18:
        orb(s, 240, 119, 75, True, 234)
        for x in (53, 369):
            s.shape([(x, 481), (x, 241), (x + 16, 219), (x + 42, 219), (x + 61, 241), (x + 61, 481)], 124)
            s.shape([(x + 19, 271), (x + 40, 271), (x + 40, 314), (x + 19, 314)], 15)
        s.shape([(159, 640), (203, 498), (261, 418), (253, 334), (280, 367), (278, 441), (232, 512), (208, 640)], 144)
        for x in (109, 347):
            s.shape([(x - 26, 510), (x - 20, 470), (x + 11, 444), (x + 21, 450), (x + 18, 476), (x + 36, 503), (x + 23, 516)], 177)
            s.line([(x - 20, 505), (x - 33, 555)], 156, 7)
            s.line([(x + 20, 510), (x + 30, 553)], 176, 7)
        s.ellipse((219, 582, 254, 622), 165)
        s.line([(225, 592), (198, 568), (200, 552)], 220, 4)
        s.line([(248, 592), (276, 568), (276, 553)], 220, 4)
    elif index == 19:
        orb(s, 240, 116, 69, False, 246)
        horse(s, 243, 565, 1.33)
        actor(s, 240, 377, 0.83, "seat", light=237)
        s.line([(348, 281), (370, 540)], 188, 6)
        s.shape([(348, 270), (439, 294), (397, 337), (432, 362), (359, 344)], 234)
        for x in (32, 77, 398, 440):
            s.line([(x, 640), (x, 479)], 158, 4)
            orb(s, x, 471, 17)
    elif index == 20:
        bird(s, 240, 154, 2.22)
        actor(s, 240, 260, 0.68, "raise", light=218)
        s.shape([(267, 140), (326, 155), (332, 181), (280, 168)], 240)
        for x in (104, 239, 375):
            s.shape([(x - 49, 578), (x + 50, 578), (x + 57, 624), (x - 51, 624)], 98)
            actor(s, x, 588, 0.9, "raise", light=216)
        for x in range(92, 416, 37):
            s.line([(277, 189), (x, 455)], 60, 1)
    elif index == 21:
        for i in range(41):
            a = i * math.tau / 41
            x = 240 + math.sin(a) * 152
            y = 316 + math.cos(a) * 231
            s.shape([(x - 9, y), (x, y - 13), (x + 11, y), (x, y + 13)], 165 + i % 3 * 20)
        actor(s, 237, 462, 1.27, "walk", light=234)
        s.shape([(188, 303), (181, 337), (261, 367), (297, 339), (276, 329), (243, 344)], 164)
        for x, y in ((52, 70), (430, 78), (51, 566), (430, 559)):
            bird(s, x, y, 0.52)
    return s


def boat(s, x, y, scale=1):
    poly(s, x, y, scale, [(-88, -28), (84, -35), (60, 10), (-56, 18)], 159)
    s.line([(x - 60 * scale, y), (x + 61 * scale, y - 9 * scale)], 43, 4)


def fish(s, x, y, scale=1):
    poly(s, x, y, scale, [(-31, 0), (-12, -15), (21, -12), (38, 0), (22, 13), (-10, 15), (-31, 0), (-49, -16), (-49, 16)], 186)
    s.ellipse((x + 19 * scale, y - 5 * scale, x + 23 * scale, y - scale), 17)
    for dx in (-12, -1, 10):
        s.line([(x + dx * scale, y - 9 * scale), (x + (dx - 5) * scale, y + 8 * scale)], 60, 2)


def court(suit, rank):
    # Each court has a composed situation and emblematic companion, not recolors.
    kinds = {
        ("wands", "page"): "land",
        ("cups", "page"): "water",
        ("swords", "page"): "land",
        ("pentacles", "page"): "garden",
        ("wands", "knight"): "land",
        ("cups", "knight"): "water",
        ("swords", "knight"): "land",
        ("pentacles", "knight"): "garden",
        ("wands", "queen"): "garden",
        ("cups", "queen"): "water",
        ("swords", "queen"): "city",
        ("pentacles", "queen"): "garden",
        ("wands", "king"): "arch",
        ("cups", "king"): "water",
        ("swords", "king"): "arch",
        ("pentacles", "king"): "garden",
    }
    s = base(kinds[(suit, rank)])
    if rank == "page":
        if suit == "wands":
            s.shape([(0, 530), (104, 463), (217, 488), (327, 452), (480, 511), (480, 640), (0, 640)], 157)
            actor(s, 222, 551, 1.4, "walk", light=227)
            wand(s, 324, 531, 1.95)
            orb(s, 112, 126, 36)
            tree(s, 421, 555, 0.65)
            s.shape([(82, 497), (106, 487), (121, 503), (107, 514), (84, 509)], 203)
        elif suit == "cups":
            architecture(s, "city")
            waves(s, 448, 84)
            s.shape([(90, 532), (347, 523), (355, 589), (83, 599)], 117)
            actor(s, 232, 548, 1.4, "stand", light=227)
            cup(s, 310, 381, 1.04)
            fish(s, 313, 330, 0.58)
            bird(s, 86, 230, 0.48)
            orb(s, 395, 83, 29, True)
            s.line([(105, 591), (105, 624), (81, 638)], 168, 4)
        elif suit == "swords":
            for k in range(11):
                s.line([(0, 110 + k * 30), (480, 81 + k * 30)], 51, 3)
            s.shape([(0, 640), (67, 562), (183, 541), (305, 576), (408, 499), (480, 546), (480, 640)], 144)
            actor(s, 236, 560, 1.4, "walk", light=226)
            sword(s, 306, 468, 1.61, -18)
            bird(s, 115, 165, 0.57)
            bird(s, 341, 144, 0.47)
            bird(s, 416, 213, 0.37)
            s.shape([(147, 477), (130, 413), (159, 449), (173, 480)], 198)
        else:
            tree(s, 67, 496, 0.78)
            tree(s, 433, 507, 0.92)
            actor(s, 235, 565, 1.38, "stand", light=222)
            coin(s, 281, 366, 47)
            s.shape([(181, 383), (216, 374), (250, 365), (256, 381), (213, 395)], 219)
            for x in (103, 365, 391):
                s.ellipse((x, 556, x + 15, 568), 229)
            orb(s, 153, 100, 27)
    elif rank == "knight":
        if suit == "wands":
            s.shape([(0, 492), (99, 437), (209, 467), (345, 391), (480, 445), (480, 640), (0, 640)], 150)
            horse(s, 241, 577, 1.48, True)
            actor(s, 224, 388, 1.05, "seat", True, 218)
            wand(s, 306, 442, 1.75, -14)
            s.shape([(204, 229), (117, 250), (84, 232), (131, 218), (211, 220)], 177)
            orb(s, 399, 111, 34)
            for x in range(19, 470, 43):
                s.shape([(x, 611), (x + 17, 572), (x + 25, 621)], 184)
        elif suit == "cups":
            s.shape([(0, 373), (82, 284), (151, 332), (160, 442), (72, 506), (0, 481)], 138)
            s.shape([(55, 332), (70, 332), (70, 449), (42, 496), (30, 491), (49, 435)], 210)
            horse(s, 235, 572, 1.39)
            actor(s, 218, 381, 1.03, "seat", light=224)
            cup(s, 296, 272, 0.92)
            fish(s, 383, 550, 0.73)
            orb(s, 378, 95, 34, True)
            s.line([(306, 302), (348, 311), (384, 299)], 173, 3)
        elif suit == "swords":
            s.glow((100, 129), 80, 53)
            for k in range(17):
                s.line([(0, 110 + k * 25), (480, 35 + k * 25)], 41 + k % 3 * 9, 2)
            horse(s, 234, 547, 1.58, True)
            actor(s, 226, 331, 1.07, "seat", True, 234)
            sword(s, 315, 309, 1.45, -38)
            s.shape([(202, 218), (112, 265), (74, 264), (141, 208), (204, 203)], 162)
            bird(s, 392, 129, 0.6)
            s.shape([(0, 640), (39, 585), (138, 595), (239, 572), (404, 600), (480, 559), (480, 640)], 96)
        else:
            tree(s, 390, 435, 0.8)
            for y in range(476, 637, 26):
                s.line([(0, y), (480, y - 19)], 72, 4)
            horse(s, 228, 576, 1.4)
            actor(s, 214, 385, 1.06, "seat", True, 224)
            coin(s, 292, 299, 39)
            s.shape([(64, 529), (90, 492), (117, 500), (124, 538), (92, 546)], 101)
            orb(s, 100, 117, 29)
    elif rank == "queen":
        if suit == "wands":
            tree(s, 36, 453, 0.84)
            throne(s, 241, 568, 1.08)
            actor(s, 240, 570, 1.46, "seat", True, 223)
            wand(s, 349, 480, 1.48)
            s.line([(132, 351), (132, 471)], 182, 5)
            orb(s, 132, 339, 22)
            s.shape([(190, 609), (195, 575), (204, 562), (215, 575), (224, 562), (234, 579), (233, 609)], 169)
            s.ellipse((196, 580, 203, 586), 235)
            s.ellipse((219, 579, 226, 585), 235)
            s.line([(231, 605), (253, 586), (260, 608)], 159, 6)
        elif suit == "cups":
            s.shape([(0, 542), (0, 227), (71, 174), (106, 211), (100, 514)], 116)
            s.shape([(385, 527), (390, 217), (433, 172), (480, 236), (480, 549)], 87)
            throne(s, 238, 568, 0.93)
            actor(s, 238, 568, 1.39, "seat", True, 221)
            cup(s, 327, 363, 1.12)
            s.shape([(296, 317), (358, 317), (352, 299), (311, 295)], 226)
            for x, y in ((104, 563), (399, 586), (364, 631)):
                s.ellipse((x - 27, y - 15, x + 27, y + 15), 135)
                for dx in range(-19, 22, 8):
                    s.line([(x, y + 11), (x + dx, y - 10)], 67, 2)
            fish(s, 80, 610, 0.58)
        elif suit == "swords":
            s.shape([(0, 516), (480, 502), (480, 580), (0, 591)], 99)
            throne(s, 240, 548, 0.97)
            actor(s, 240, 552, 1.43, "seat", True, 235)
            sword(s, 344, 472, 1.6)
            orb(s, 91, 118, 35, True)
            for k in range(7):
                s.line([(0, 159 + k * 27), (480, 122 + k * 27)], 44, 2)
            bird(s, 417, 212, 0.47)
            s.shape([(130, 376), (101, 358), (93, 370), (124, 395)], 233)
        else:
            tree(s, 51, 471, 1.03)
            tree(s, 435, 463, 1.0)
            throne(s, 240, 568, 1.0)
            actor(s, 240, 566, 1.4, "seat", True, 224)
            coin(s, 238, 439, 46)
            s.shape([(367, 591), (361, 574), (373, 561), (389, 568), (399, 559), (416, 573), (409, 592)], 206)
            s.shape([(379, 567), (377, 535), (385, 528), (389, 561)], 220)
            s.shape([(391, 567), (399, 535), (407, 530), (402, 569)], 188)
            s.line([(387, 588), (401, 588)], 35, 2)
            for x in (72, 110, 344):
                s.ellipse((x, 598, x + 17, 614), 220)
    else:
        if suit == "wands":
            throne(s, 240, 568, 1.14)
            actor(s, 240, 573, 1.46, "seat", True, 221)
            wand(s, 348, 489, 1.66)
            for x, y in ((118, 231), (363, 231)):
                s.ellipse((x - 32, y - 32, x + 32, y + 32), 153)
                s.ellipse((x - 20, y - 21, x + 20, y + 22), 215)
                s.line([(x - 9, y), (x + 9, y)], 37, 3)
            s.shape([(81, 611), (96, 580), (140, 580), (162, 596), (158, 615)], 157)
            s.ellipse((133, 557, 172, 596), 199)
            orb(s, 84, 103, 24)
        elif suit == "cups":
            throne(s, 235, 562, 0.96)
            s.shape([(109, 554), (367, 554), (383, 598), (85, 598)], 142)
            actor(s, 235, 565, 1.4, "seat", True, 226)
            cup(s, 129, 389, 0.92)
            fish(s, 359, 485, 0.72)
            boat(s, 369, 224, 0.63)
            s.line([(369, 204), (369, 116)], 158, 4)
            s.shape([(369, 122), (431, 202), (369, 201)], 182)
            orb(s, 82, 114, 28, True)
            waves(s, 588, 123)
        elif suit == "swords":
            throne(s, 240, 568, 1.05)
            actor(s, 240, 570, 1.46, "seat", True, 227)
            sword(s, 345, 477, 1.66, -8)
            for x in (82, 395):
                s.shape([(x, 92), (x - 35, 208), (x - 22, 204), (x - 42, 275), (x + 40, 275), (x + 23, 212), (x + 36, 218)], 69)
            bird(s, 106, 583, 0.6)
            orb(s, 390, 90, 25, True)
            s.shape([(211, 397), (269, 397), (280, 467), (231, 490), (205, 462)], 149)
        else:
            tree(s, 39, 418, 0.9)
            tree(s, 444, 439, 0.98)
            throne(s, 240, 568, 1.16)
            actor(s, 240, 573, 1.48, "seat", True, 222)
            coin(s, 145, 431, 48)
            for x in (119, 361):
                s.shape([(x - 22, 231), (x - 38, 207), (x - 35, 188), (x - 13, 218), (x + 17, 214), (x + 34, 187), (x + 33, 212), (x + 18, 232)], 214)
            for x, y in ((353, 542), (382, 565), (362, 594), (115, 570)):
                s.ellipse((x - 10, y - 10, x + 10, y + 10), 143)
                s.line([(x, y - 10), (x + 7, y - 21)], 194, 2)
            s.line([(351, 619), (367, 533), (385, 493)], 139, 6)
    return s


def minor(suit, rank):
    if rank in ("page", "knight", "queen", "king"):
        return court(suit, rank)
    n = RANKS.index(rank) + 1
    s = base({"wands": "land", "cups": "water", "swords": "city", "pentacles": "garden"}[suit])
    if n == 1:
        # Four elemental visions, each with a modeled hand emerging from cloud.
        for x, y, r in ((84, 325, 46), (45, 353, 50), (115, 362, 61), (76, 401, 48)):
            s.ellipse((x - r, y - r, x + r, y + r), 59)
        s.shape(
            [
                (50, 402),
                (89, 347),
                (118, 326),
                (163, 336),
                (183, 320),
                (217, 320),
                (226, 333),
                (213, 348),
                (171, 352),
                (158, 365),
                (185, 370),
                (208, 367),
                (213, 379),
                (190, 395),
                (137, 402),
                (89, 429),
            ],
            226,
        )
        if suit != "pentacles":
            symbol(s, suit, 251, 366, 1.68)
        if suit == "wands":
            orb(s, 398, 97, 31)
            tree(s, 431, 533, 0.62)
            s.shape([(185, 611), (213, 527), (261, 509), (284, 587), (335, 617)], 123)
        elif suit == "cups":
            bird(s, 251, 194, 0.54)
            for x in (224, 245, 266):
                s.line([(x, 384), (x - 15, 449), (x + 8, 513)], 227, 4)
            for x, y in ((167, 563), (316, 604), (383, 567)):
                s.ellipse((x - 21, y - 5, x + 21, y + 5), 171)
        elif suit == "swords":
            s.shape([(201, 164), (199, 135), (215, 151), (232, 129), (243, 150), (262, 135), (263, 165)], 238)
            s.line([(197, 161), (263, 161)], 190, 4)
            for x in (200, 291):
                tree(s, x, 613, 0.43)
        else:
            architecture(s, "arch")
            coin(s, 253, 242, 75)
            tree(s, 49, 597, 0.55)
            tree(s, 430, 594, 0.6)
        return s
    if suit == "wands":
        if n == 2:
            architecture(s, "city")
            s.shape([(0, 545), (480, 545), (480, 605), (0, 605)], 132)
            actor(s, 245, 550, 1.3, "stand", light=219)
            wand(s, 139, 550, 1.82)
            wand(s, 355, 550, 1.77)
            coin(s, 283, 384, 28)
            waves(s, 588, 72)
        elif n == 3:
            waves(s, 450, 110)
            s.shape([(0, 577), (167, 543), (321, 561), (413, 533), (480, 546), (480, 640), (0, 640)], 120)
            actor(s, 242, 568, 1.22, "stand", light=224)
            for x, y in ((107, 580), (356, 579), (289, 596)):
                wand(s, x, y, 1.71)
            for x, y in ((82, 453), (390, 475), (191, 503)):
                boat(s, x, y, 0.3)
                s.line([(x, y), (x, y - 38)], 155, 2)
                s.shape([(x, y - 37), (x + 26, y - 5), (x, y - 5)], 190)
        elif n == 4:
            for x in (93, 168, 313, 386):
                wand(s, x, 574, 2.06)
            s.line([(87, 241), (164, 215), (319, 217), (391, 241)], 142, 12)
            for x in range(93, 393, 24):
                s.ellipse((x - 8, 224 + math.sin(x * 0.025) * 13, x + 8, 240 + math.sin(x * 0.025) * 13), 218)
            actor(s, 223, 583, 0.8, "raise", light=215)
            actor(s, 283, 585, 0.78, "raise", light=229)
        elif n == 5:
            for i, (x, y, a) in enumerate(((62, 550, -29), (151, 574, 30), (243, 545, -16), (332, 587, 31), (423, 543, -25))):
                actor(s, x, y, 0.91, "walk", light=171 + i * 12)
                wand(s, x + 21, y - 110, 1.4, a)
            s.shape([(0, 600), (127, 590), (269, 601), (390, 583), (480, 597), (480, 640), (0, 640)], 73)
        elif n == 6:
            horse(s, 255, 579, 1.37)
            actor(s, 230, 390, 0.93, "seat", True, 230)
            for x in (56, 111, 349, 402, 449):
                wand(s, x, 594, 1.56)
            wand(s, 306, 432, 1.7)
            for a in range(0, 360, 30):
                rad = math.radians(a)
                s.ellipse((305 + math.cos(rad) * 26 - 5, 138 + math.sin(rad) * 26 - 5, 305 + math.cos(rad) * 26 + 5, 138 + math.sin(rad) * 26 + 5), 193)
        elif n == 7:
            s.shape([(0, 640), (97, 557), (212, 463), (359, 516), (480, 573), (480, 640)], 169)
            actor(s, 236, 504, 1.17, "walk", light=225)
            wand(s, 224, 355, 1.39, 74)
            for x, a in ((32, 17), (110, -20), (178, 7), (315, -18), (391, 24), (462, -25)):
                wand(s, x, 720, 1.42, a)
        elif n == 8:
            waves(s, 479, 70)
            for i in range(8):
                wand(s, 79 + i * 43, 359 + i * 31, 1.53, 41)
            s.shape([(0, 597), (57, 527), (111, 555), (181, 521), (301, 591), (480, 588), (480, 640), (0, 640)], 77)
            s.line([(21, 390), (163, 583)], 131, 2)
        elif n == 9:
            for x in (31, 85, 137, 187, 295, 347, 396, 449):
                wand(s, x, 592, 1.73)
            actor(s, 242, 585, 1.25, "stand", light=229)
            wand(s, 278, 588, 1.63)
            s.line([(221, 329), (258, 332)], 239, 7)
            s.shape([(0, 609), (480, 609), (480, 640), (0, 640)], 83)
        else:
            actor(s, 232, 586, 1.3, "walk", light=190)
            for i in range(10):
                wand(s, 193 + i * 13, 508 - i * 2, 1.65, -21 + i * 2)
            s.shape([(304, 563), (343, 468), (390, 464), (417, 574)], 102)
            s.shape([(364, 548), (364, 502), (378, 502), (378, 548)], 14)
    elif suit == "cups":
        if n == 2:
            actor(s, 130, 583, 1.26, "stand", light=228)
            actor(s, 353, 583, 1.26, "stand", light=211)
            cup(s, 190, 397, 0.85)
            cup(s, 291, 397, 0.85)
            s.line([(238, 149), (238, 322)], 194, 5)
            for k in range(2):
                s.line([(238 + math.sin(j * 0.5 + k * math.pi) * 20, 166 + j * 8) for j in range(18)], 162, 4)
            bird(s, 239, 164, 1.23)
        elif n == 3:
            garden(s)
            actor(s, 111, 581, 1.0, "raise", light=220)
            actor(s, 240, 597, 1.2, "raise", light=233)
            actor(s, 376, 582, 1.0, "raise", light=212)
            for x, y in ((62, 352), (305, 319), (431, 355)):
                cup(s, x, y, 0.74)
            for x in range(60, 435, 38):
                s.ellipse((x, 600, x + 16, 612), 181)
        elif n == 4:
            tree(s, 127, 593, 1.33)
            actor(s, 228, 590, 1.25, "seat", light=177)
            for x, y in ((133, 600), (227, 611), (331, 599)):
                cup(s, x, y, 0.78)
            s.glow((371, 336), 55, 48)
            cup(s, 373, 370, 0.96)
            s.shape([(458, 347), (429, 334), (399, 335), (390, 349), (415, 354), (451, 365)], 207)
        elif n == 5:
            architecture(s, "arch")
            waves(s, 510, 69)
            actor(s, 229, 570, 1.48, "grief", light=153)
            for x, y in ((92, 590), (147, 614), (183, 579)):
                cup(s, x, y, 0.83, True)
            cup(s, 341, 595, 0.82)
            cup(s, 405, 593, 0.82)
            s.line([(66, 482), (194, 461), (386, 493)], 122, 11)
        elif n == 6:
            architecture(s, "city")
            s.shape([(48, 538), (430, 538), (446, 590), (33, 590)], 107)
            actor(s, 181, 580, 1.05, "stand", light=211)
            actor(s, 307, 582, 0.84, "stand", light=231)
            for x, y in ((91, 560), (158, 612), (247, 610), (336, 611), (411, 556), (247, 433)):
                cup(s, x, y, 0.75)
                star(s, x, y - 31, 8)
            s.shape([(209, 440), (243, 429), (259, 441), (240, 452)], 208)
        elif n == 7:
            for x, y, r in ((129, 304, 65), (260, 300, 72), (377, 305, 69), (211, 450, 83), (352, 450, 81)):
                s.glow((x, y), r, 50)
            positions = [(82, 248), (236, 248), (390, 248), (59, 395), (184, 395), (302, 395), (424, 395)]
            for x, y in positions:
                cup(s, x, y, 0.86)
            coin(s, 82, 180, 24)
            s.shape([(216, 190), (226, 164), (243, 149), (257, 175), (249, 195)], 206)
            fish(s, 390, 176, 0.55)
            star(s, 59, 321, 27)
            s.shape([(161, 343), (162, 289), (201, 289), (204, 343)], 167)
            s.shape([(282, 340), (280, 307), (293, 320), (302, 294), (312, 319), (325, 307), (324, 340)], 230)
            bird(s, 424, 326, 0.39)
            actor(s, 238, 641, 0.83, "stand", light=93)
        elif n == 8:
            orb(s, 352, 103, 44, True)
            actor(s, 304, 469, 1.12, "walk", light=156)
            s.shape([(0, 640), (183, 563), (357, 439), (394, 395), (437, 451), (305, 566), (270, 640)], 104)
            for x, y in ((60, 526), (128, 526), (196, 526), (93, 454), (163, 454), (31, 604), (111, 604), (194, 604)):
                cup(s, x, y, 0.7)
            s.line([(358, 269), (343, 497)], 194, 6)
        elif n == 9:
            s.shape([(22, 283), (458, 283), (458, 308), (22, 308)], 125)
            for i in range(9):
                cup(s, 43 + i * 49, 268, 0.62)
            throne(s, 240, 582, 0.58)
            actor(s, 240, 591, 1.17, "seat", light=229)
            s.shape([(109, 533), (371, 533), (386, 599), (96, 599)], 147)
        else:
            for i in range(10):
                a = math.pi + (i / 9) * math.pi
                x = 240 + math.cos(a) * 198
                y = 299 + math.sin(a) * 178
                cup(s, x, y, 0.58)
            s.line([(46, 284), (85, 195), (163, 150), (240, 131), (322, 152), (394, 201), (438, 280)], 73, 10)
            actor(s, 154, 583, 1.12, "raise", light=218)
            actor(s, 322, 583, 1.1, "raise", light=231)
            actor(s, 228, 600, 0.56, "walk", light=220)
            actor(s, 264, 600, 0.55, "walk", light=229)
            s.shape([(30, 551), (37, 492), (72, 472), (107, 502), (106, 551)], 149)
    elif suit == "swords":
        if n == 2:
            waves(s, 394, 101)
            orb(s, 370, 110, 34, True)
            s.shape([(152, 543), (321, 543), (325, 574), (145, 574)], 113)
            actor(s, 235, 554, 1.34, "bound", light=210)
            sword(s, 319, 401, 1.43, -42)
            sword(s, 156, 401, 1.43, 42)
            s.line([(182, 324), (288, 381)], 173, 12)
            s.line([(290, 325), (184, 381)], 193, 12)
        elif n == 3:
            s.image = Image.new("L", (480, 640), 13)
            s.glow((244, 307), 181, 60)
            s.shape(
                [(242, 482), (76, 310), (68, 254), (96, 194), (146, 177), (190, 190), (241, 234), (288, 191), (336, 176), (392, 202), (413, 258), (398, 315)],
                211,
            )
            s.shape([(240, 247), (243, 480), (354, 373), (397, 298), (392, 240), (367, 213), (332, 216)], 115)
            sword(s, 238, 544, 1.89)
            sword(s, 358, 490, 1.62, -31)
            sword(s, 126, 490, 1.63, 31)
            for x in range(18, 475, 27):
                s.line([(x, 0), (x - 52, 113)], 70, 2)
        elif n == 4:
            architecture(s, "arch")
            s.shape([(74, 492), (405, 492), (426, 561), (54, 561)], 170)
            body = Tonal()
            actor(body, 240, 501, 1.0, "stand", light=181)
            patch = body.image.crop((185, 275, 293, 519)).rotate(90, expand=True)
            s.image.paste(patch, (121, 418), patch.point(lambda v: 255 if v else 0))
            for x in (153, 242, 331):
                sword(s, x, 308, 0.92)
            sword(s, 368, 566, 1.19, 90)
            star(s, 240, 91, 24)
        elif n == 5:
            waves(s, 451, 84)
            actor(s, 151, 579, 1.32, "stand", light=229)
            actor(s, 326, 470, 0.68, "walk", light=119)
            actor(s, 397, 448, 0.54, "walk", light=89)
            sword(s, 76, 462, 1.28, -17)
            sword(s, 226, 470, 1.35, 19)
            sword(s, 167, 406, 1.02, 39)
            sword(s, 183, 609, 1.12, 87)
            sword(s, 395, 588, 1.15, 103)
            s.shape([(0, 624), (186, 611), (480, 630), (480, 640), (0, 640)], 45)
        elif n == 6:
            waves(s, 397, 100)
            boat(s, 242, 577, 1.62)
            actor(s, 174, 551, 0.8, "seat", light=147)
            actor(s, 262, 534, 0.91, "stand", light=207)
            s.line([(296, 377), (411, 602)], 196, 7)
            for x in (145, 184, 223, 264, 306, 345):
                sword(s, x, 561, 1.04)
            orb(s, 384, 124, 27, True)
        elif n == 7:
            s.shape([(32, 436), (73, 314), (144, 319), (173, 438)], 100)
            s.shape([(326, 436), (358, 302), (420, 314), (443, 438)], 111)
            actor(s, 240, 580, 1.22, "walk", light=228)
            for i in range(5):
                sword(s, 195 + i * 24, 393 + i * 10, 0.98, 50)
            sword(s, 351, 590, 1.31)
            sword(s, 405, 591, 1.34)
            s.shape([(97, 311), (94, 283), (139, 283), (142, 314)], 180)
        elif n == 8:
            waves(s, 563, 69)
            actor(s, 241, 579, 1.35, "bound", light=209)
            for x, y in ((46, 583), (99, 574), (153, 559), (338, 558), (391, 570), (444, 585), (119, 640), (373, 640)):
                sword(s, x, y, 1.27)
            s.shape([(210, 615), (240, 594), (271, 616), (267, 640), (203, 640)], 99)
        elif n == 9:
            s.image = Image.new("L", (480, 640), 8)
            s.shape([(80, 566), (419, 566), (421, 613), (75, 613)], 139)
            s.shape([(61, 598), (61, 387), (91, 383), (99, 598)], 178)
            actor(s, 252, 569, 1.22, "grief", light=212)
            for i in range(9):
                sword(s, 395, 87 + i * 34, 1.13, 90)
            for x in range(101, 410, 30):
                for y in range(575, 615, 18):
                    s.shape([(x, y), (x + 12, y), (x + 12, y + 8), (x, y + 8)], 79)
        else:
            s.image = Image.new("L", (480, 640), 5)
            s.glow((245, 402), 172, 52)
            s.shape([(0, 488), (92, 439), (208, 476), (370, 419), (480, 482), (480, 640), (0, 640)], 84)
            body = Tonal()
            actor(body, 240, 519, 1.17, "stand", light=161)
            patch = body.image.crop((171, 259, 308, 540)).rotate(90, expand=True)
            s.image.paste(patch, (102, 494), patch.point(lambda v: 255 if v else 0))
            for i in range(10):
                sword(s, 87 + i * 33, 566 + int(math.sin(i) * 13), 0.89, (-9 + i * 2))
            s.line([(0, 388), (480, 388)], 155, 3)
    else:
        if n == 2:
            waves(s, 474, 96)
            actor(s, 233, 550, 1.33, "walk", light=222)
            coin(s, 140, 359, 47)
            coin(s, 336, 415, 47)
            pts = [(240 + math.sin(a) * 103, 387 + math.sin(a) * math.cos(a) * 75) for a in [i * math.tau / 100 for i in range(101)]]
            s.line(pts, 162, 5)
            boat(s, 105, 575, 0.41)
            boat(s, 396, 520, 0.31)
        elif n == 3:
            architecture(s, "arch")
            for x, y in ((171, 157), (240, 105), (309, 157)):
                coin(s, x, y, 34)
            actor(s, 245, 561, 1.21, "stand", light=226)
            actor(s, 111, 592, 1.0, "stand", light=165)
            actor(s, 374, 592, 1.04, "stand", light=190)
            s.shape([(182, 421), (302, 421), (309, 441), (172, 441)], 151)
            s.line([(268, 344), (294, 410)], 207, 6)
            s.shape([(282, 404), (312, 404), (312, 417), (282, 417)], 232)
        elif n == 4:
            architecture(s, "city")
            throne(s, 240, 566, 0.78)
            actor(s, 240, 566, 1.3, "seat", True, 218)
            coin(s, 240, 401, 50)
            coin(s, 241, 229, 35)
            coin(s, 156, 588, 33)
            coin(s, 325, 588, 33)
            s.shape([(0, 608), (480, 608), (480, 640), (0, 640)], 63)
        elif n == 5:
            s.image = Image.new("L", (480, 640), 7)
            architecture(s, "arch")
            s.shape([(144, 137), (336, 137), (336, 389), (144, 389)], 23)
            for x, y in ((195, 190), (284, 190), (241, 257), (195, 323), (284, 323)):
                coin(s, x, y, 29)
            actor(s, 152, 609, 0.97, "walk", light=154)
            actor(s, 343, 615, 1.11, "grief", light=195)
            s.line([(113, 439), (71, 640)], 201, 5)
            for row in range(15):
                for col in range(9):
                    x = (col * 57 + row * 17) % 480
                    y = 16 + row * 42
                    s.line([(x, y), (x + 4, y + 6)], 108, 2)
        elif n == 6:
            architecture(s, "city")
            actor(s, 240, 578, 1.37, "stand", light=225)
            actor(s, 101, 613, 0.83, "kneel", light=157)
            actor(s, 375, 613, 0.84, "kneel", light=189)
            for x, y in ((98, 177), (159, 204), (111, 262), (349, 177), (409, 204), (357, 262)):
                coin(s, x, y, 27)
            s.line([(330, 342), (410, 342)], 180, 4)
            s.line([(347, 343), (329, 387), (366, 387), (347, 343)], 198, 2)
            s.line([(398, 343), (381, 387), (418, 387), (398, 343)], 198, 2)
            s.shape([(198, 407), (158, 417), (136, 438), (140, 449), (170, 438), (208, 426)], 206)
        elif n == 7:
            tree(s, 122, 588, 1.31)
            actor(s, 339, 583, 1.32, "stand", light=215)
            s.line([(259, 414), (244, 625)], 190, 6)
            for x, y in ((85, 291), (149, 314), (185, 379), (81, 409), (123, 473), (171, 533), (185, 593)):
                coin(s, x, y, 31)
            s.shape([(0, 625), (170, 602), (480, 621), (480, 640), (0, 640)], 83)
        elif n == 8:
            architecture(s, "city")
            actor(s, 295, 588, 1.25, "seat", light=218)
            for i in range(6):
                coin(s, 89, 118 + i * 65, 27)
            s.shape([(185, 433), (424, 433), (441, 458), (168, 458)], 172)
            s.shape([(190, 458), (211, 458), (204, 620), (183, 620)], 133)
            s.shape([(391, 458), (412, 458), (426, 620), (403, 620)], 118)
            coin(s, 221, 423, 33)
            coin(s, 357, 607, 30)
            s.line([(297, 351), (269, 408)], 212, 6)
            s.shape([(253, 401), (286, 401), (286, 414), (253, 414)], 228)
        elif n == 9:
            tree(s, 44, 460, 0.91)
            tree(s, 436, 462, 0.93)
            actor(s, 239, 579, 1.47, "stand", light=225)
            bird(s, 324, 345, 0.38)
            s.shape([(260, 379), (318, 353), (326, 366), (280, 397)], 211)
            for x, y in ((60, 231), (124, 287), (72, 351), (409, 235), (352, 284), (404, 354), (94, 498), (388, 511), (240, 612)):
                coin(s, x, y, 28)
        else:
            architecture(s, "arch")
            tree(s, 39, 545, 0.83)
            actor(s, 346, 591, 1.17, "stand", light=215)
            actor(s, 136, 602, 1.19, "seat", light=179)
            actor(s, 282, 616, 0.57, "stand", light=231)
            s.shape([(42, 594), (40, 572), (59, 555), (80, 565), (97, 557), (115, 574), (107, 596)], 188)
            for x, y in ((61, 81), (128, 118), (240, 78), (352, 118), (419, 81), (58, 251), (425, 255), (91, 425), (406, 428), (238, 625)):
                coin(s, x, y, 27)
    return s


def back():
    s = Tonal()
    s.stars()
    s.glow((240, 311), 190, 62)
    for r, brightness in ((206, 148), (196, 11), (167, 115), (158, 11), (72, 175), (66, 17)):
        s.ellipse((240 - r, 311 - r, 240 + r, 311 + r), brightness)
    for i in range(24):
        a = i * math.tau / 24
        s.line([(240 + math.sin(a) * 83, 311 + math.cos(a) * 83), (240 + math.sin(a) * 151, 311 + math.cos(a) * 151)], 86 + i % 3 * 25, 3)
        coin(s, 240 + math.sin(a) * 184, 311 + math.cos(a) * 184, 7)
    orb(s, 240, 311, 50, True)
    star(s, 240, 313, 32)
    for x, y in ((85, 159), (395, 159), (85, 463), (395, 463)):
        star(s, x, y, 23)
    bird(s, 240, 90, 1.0)
    bird(s, 240, 578, 1.0)
    return s


def main():
    out = ROOT / "art/crt"
    out.mkdir(exist_ok=True)
    catalogue = []
    registry = json.loads((ROOT / "registry.json").read_text())
    for card in registry["cards"]:
        cid = card["id"]
        if cid.startswith("major-"):
            index = int(cid.split("-")[1])
            scene = major(index)
            code = ROMANS[index]
            motto = MAJOR_MOTTOS[index]
        else:
            suit, rank = cid.split("-")
            scene = minor(suit, rank)
            code = rank.upper()
            motto = MINOR_MOTTOS[suit][RANKS.index(rank)]
        svg, _ = ascii_svg(scene, cid, card["name"], code, motto)
        (out / f"{cid}.svg").write_text(svg)
        catalogue.append(
            {
                "id": cid,
                "name": card["name"],
                "scene_sha256": hashlib.sha256(scene.image.tobytes()).hexdigest(),
                "motto": motto,
                "svg": f"{cid}.svg",
                "png": f"{cid}.png",
                "style": "modeled ASCII phosphor",
            }
        )
    svg, _ = ascii_svg(back(), "back", "Phosphor Arcana", "78", "EVERY CARD HAS A CURRENT")
    (out / "back.svg").write_text(svg)
    (out / "catalogue.json").write_text(
        json.dumps(
            {
                "deck": "crt",
                "name": "Phosphor Arcana",
                "license": "MIT",
                "style": "Original tonal compositions translated into curved ASCII CRT phosphor",
                "cards": catalogue,
            },
            indent=2,
        )
        + "\n"
    )
    assert len({c["scene_sha256"] for c in catalogue}) == 78
    print("Authored 78 distinct tonal ASCII scenes and terminal back.")


if __name__ == "__main__":
    main()
