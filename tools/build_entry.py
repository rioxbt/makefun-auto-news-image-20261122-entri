#!/usr/bin/env python3
"""Draw the entry image: one picture holding Sunday 22 November 2026's world news.

The picture is a flat world map with a numbered marker on each story's place,
over a strip of nine story cards that name the region and say what happened.
It is rendered once here and committed as entry.png; the graded program (main.ts)
only places those bytes at /output/entry.png.

    python3 tools/build_entry.py            # writes ./entry.png

Deterministic: the same code writes the same bytes every run.
"""

from __future__ import annotations

import math
import os

from PIL import Image, ImageDraw, ImageFont

from coastlines import LAND

# ---------------------------------------------------------------- canvas ----

W = H = 1024
M = 24
BG = (10, 14, 20)
CARD = (18, 24, 33)
CARD_EDGE = (34, 48, 63)
INK = (245, 248, 252)
MUTED = (134, 151, 171)
RULE = (37, 48, 61)
ACCENT = (229, 72, 77)

# The world map window, equirectangular: 360 degrees of longitude by 140 of
# latitude, so the two axes share one scale and the globe is not stretched.
MAP_X0, MAP_Y0, MAP_X1, MAP_Y1 = M, 176, W - M, 548
LON0, LON_SPAN = -170.0, 360.0
LAT0, LAT_SPAN = -56.0, 140.0
MARKER_GAP = 32.0
OCEAN = (14, 21, 30)
GRID = (23, 34, 47)
LAND_FILL = (39, 56, 76)
LAND_EDGE = (52, 74, 99)

FONTS = "/usr/share/fonts/truetype/dejavu"
BOLD = f"{FONTS}/DejaVuSans-Bold.ttf"
REG = f"{FONTS}/DejaVuSans.ttf"

# ---------------------------------------------------------------- stories ---
# lon, lat: where the marker sits; then its colour and the place it stands for.
# The nine cards below run in this order, so card 1 explains marker 1.
STORIES = [
    (19.4, 52.2, (239, 68, 68), "POLAND"),
    (30.7, 36.9, (34, 197, 94), "ANTALYA"),
    (-77.0, 38.9, (59, 130, 246), "USA"),
    (-53.9, -28.9, (6, 182, 212), "BRAZIL"),
    (34.5, 31.5, (249, 115, 22), "GAZA"),
    (6.0, 4.8, (168, 85, 247), "NIGERIA"),
    (96.1, 19.8, (234, 179, 8), "MYANMAR"),
    (4.4, 50.8, (236, 72, 153), "BRUSSELS"),
    (144.9, -37.8, (20, 184, 166), "MELBOURNE"),
]

# Where a place label may hang off its marker: to the right, to the left, or
# centred above or below.  The first offset that clears every marker and every
# label already set is the one used.
LABEL_SPOTS = [
    (15, -14, "l"), (-15, -14, "r"), (15, 11, "l"), (-15, 11, "r"),
    (0, -27, "c"), (0, 19, "c"), (26, -3, "l"), (-26, -3, "r"),
    (0, -45, "c"), (0, 37, "c"), (40, -18, "l"), (-40, -18, "r"),
    (40, 14, "l"), (-40, 14, "r"), (0, -63, "c"), (0, 55, "c"),
]
TAKEN: list[tuple[float, float, float, float]] = []

CARDS = [
    ("Russian missiles breach Poland", "POLAND · NATO", (239, 68, 68), "rocket"),
    ("COP31 deadlock on fossil fuels", "TÜRKIYE · CLIMATE", (34, 197, 94), "stack"),
    ("FBI crime database hacked", "USA · CYBER", (59, 130, 246), "lock"),
    ("Storm wrecks 8,000 homes", "BRAZIL · STORM", (6, 182, 212), "storm"),
    ("Israel strikes Gaza; Yemen hit", "MIDDLE EAST · WAR", (249, 115, 22), "burst"),
    ("Nigeria funeral boat: 24 dead", "NIGERIA · DISASTER", (168, 85, 247), "boat"),
    ("ICJ rules Myanmar genocide", "MYANMAR · JUSTICE", (234, 179, 8), "scales"),
    ("EU moves to tax Big Tech", "BRUSSELS · LEVY", (236, 72, 153), "euro"),
    ("Australia beat England at MCG", "MELBOURNE · SPORT", (20, 184, 166), "bat"),
]


def font(size: int, bold: bool = True) -> ImageFont.FreeTypeFont:
    return ImageFont.truetype(BOLD if bold else REG, size)


def width(d: ImageDraw.ImageDraw, text: str, fnt) -> float:
    return d.textlength(text, font=fnt)


def fit(d: ImageDraw.ImageDraw, text: str, limit: int, start: int, floor: int = 15):
    """Largest bold size at or below `start` that sets `text` within `limit`."""
    size = start
    while size > floor and width(d, text, font(size)) > limit:
        size -= 1
    return font(size)


def headline(d: ImageDraw.ImageDraw, text: str, limit: int, start: int = 28, floor: int = 19,
             most: int = 2):
    """The largest size that sets `text` in at most `most` lines, and the lines."""
    size = start
    while size > floor:
        lines = wrap(d, text, font(size), limit)
        if len(lines) <= most:
            return font(size), lines
        size -= 1
    return font(floor), wrap(d, text, font(floor), limit)[:most]


def wrap(d: ImageDraw.ImageDraw, text: str, fnt, limit: int) -> list[str]:
    """Greedy line breaking to a pixel width."""
    lines, line = [], ""
    for word in text.split():
        trial = f"{line} {word}".strip()
        if line and width(d, trial, fnt) > limit:
            lines.append(line)
            line = word
        else:
            line = trial
    if line:
        lines.append(line)
    return lines


def spaced(text: str, gap: str = " ") -> str:
    """Wide letterspacing, the way a masthead is set."""
    return gap.join(text)


# ------------------------------------------------------------------- map ----

def px(lon: float) -> float:
    return MAP_X0 + (lon - LON0) / LON_SPAN * (MAP_X1 - MAP_X0)


def py(lat: float) -> float:
    return MAP_Y0 + (LAT0 + LAT_SPAN - lat) / LAT_SPAN * (MAP_Y1 - MAP_Y0)


def draw_map(im: Image.Image) -> None:
    d = ImageDraw.Draw(im)
    TAKEN.clear()
    box = (MAP_X0, MAP_Y0, MAP_X1, MAP_Y1)
    d.rounded_rectangle(box, radius=12, fill=OCEAN)

    layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    ld = ImageDraw.Draw(layer)

    for deg in range(-120, 181, 30):
        colour = GRID + ((150 if deg % 60 == 0 else 85),)
        ld.line([(px(float(deg)), MAP_Y0), (px(float(deg)), MAP_Y1)], fill=colour)
    for deg in range(-40, 81, 20):
        ld.line([(MAP_X0, py(float(deg))), (MAP_X1, py(float(deg)))], fill=GRID + (105,))
    ld.line([(MAP_X0, py(0.0)), (MAP_X1, py(0.0))], fill=(41, 59, 81, 190))

    for ring in LAND:
        pts = [(px(ring[i]), py(ring[i + 1])) for i in range(0, len(ring) - 1, 2)]
        if len(pts) >= 3:
            ld.polygon(pts, fill=LAND_FILL + (255,), outline=LAND_EDGE + (255,))

    mask = Image.new("L", (W, H), 0)
    ImageDraw.Draw(mask).rounded_rectangle(box, radius=12, fill=255)
    alpha = layer.split()[3].point(lambda a: 255 if a > 0 else 0)
    im.paste(layer, (0, 0), Image.composite(alpha, Image.new("L", (W, H), 0), mask))

    # markers last, so no country and no label hides a number
    top = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    td = ImageDraw.Draw(top)
    num = font(16)
    tag = font(16)

    # Two stories a few degrees apart (Antalya and Gaza) would otherwise sit on
    # top of each other, so markers that crowd are pushed apart and a hairline
    # ties each one back to the place it stands for.
    true = [(px(lon), py(lat)) for lon, lat, *_ in STORIES]
    spot = list(true)
    for _ in range(24):
        shifted = False
        for a in range(len(spot)):
            for b in range(a + 1, len(spot)):
                dx, dy = spot[b][0] - spot[a][0], spot[b][1] - spot[a][1]
                gap = math.hypot(dx, dy)
                if gap < MARKER_GAP:
                    if gap < 1e-6:
                        dx, dy, gap = 0.0, 1.0, 1.0
                    push = (MARKER_GAP - gap) / 2
                    spot[a] = (spot[a][0] - dx / gap * push, spot[a][1] - dy / gap * push)
                    spot[b] = (spot[b][0] + dx / gap * push, spot[b][1] + dy / gap * push)
                    shifted = True
        if not shifted:
            break

    for i, (lon, lat, colour, place) in enumerate(STORIES, start=1):
        cx, cy = spot[i - 1]
        tx0, ty0 = true[i - 1]
        if math.hypot(cx - tx0, cy - ty0) > 2.0:
            td.line([(cx, cy), (tx0, ty0)], fill=(150, 168, 188, 190), width=1)
            td.ellipse((tx0 - 2.5, ty0 - 2.5, tx0 + 2.5, ty0 + 2.5), fill=(150, 168, 188, 235))
        cx = min(max(cx, MAP_X0 + 22), MAP_X1 - 22)
        cy = min(max(cy, MAP_Y0 + 22), MAP_Y1 - 22)
        td.ellipse((cx - 17, cy - 17, cx + 17, cy + 17), fill=(5, 9, 14, 165))
        td.ellipse((cx - 13, cy - 13, cx + 13, cy + 13), fill=colour + (255,),
                   outline=(255, 255, 255, 225), width=2)
        b = td.textbbox((0, 0), str(i), font=num)
        td.text((cx - (b[2] - b[0]) / 2 - b[0], cy - (b[3] - b[1]) / 2 - b[1]),
                str(i), font=num, fill=(8, 12, 18, 255))

        w = width(td, place, tag)
        tx, ty = place_label(cx, cy, w, spot)
        td.rounded_rectangle((tx - 7, ty - 3, tx + w + 7, ty + 20), radius=4, fill=(5, 9, 14, 215))
        td.text((tx, ty), place, font=tag, fill=(226, 234, 244, 255))
    im.paste(top, (0, 0), top)


def place_label(cx: float, cy: float, w: float, spots) -> tuple[float, float]:
    """Put a place label beside its marker, clear of every marker and of the
    labels already placed; the first free spot from a short list of offsets wins."""
    for dx, dy, side in LABEL_SPOTS:
        tx = cx + dx if side == "l" else cx + dx - w if side == "r" else cx - w / 2 + dx
        ty = cy + dy
        if tx < MAP_X0 + 6 or tx + w + 14 > MAP_X1 - 6 or ty < MAP_Y0 + 6 or ty + 24 > MAP_Y1 - 6:
            continue
        box = (tx - 9, ty - 5, tx + w + 9, ty + 22)
        if any(_hits_circle(box, mx, my, 16) for mx, my in spots):
            continue
        if any(_overlaps(box, other) for other in TAKEN):
            continue
        TAKEN.append(box)
        return tx, ty
    TAKEN.append((cx - w / 2 - 9, cy + 16, cx + w / 2 + 9, cy + 43))
    return cx - w / 2, cy + 22


def _hits_circle(box, mx: float, my: float, r: float) -> bool:
    nx = min(max(mx, box[0]), box[2])
    ny = min(max(my, box[1]), box[3])
    return (mx - nx) ** 2 + (my - ny) ** 2 < r * r


def _overlaps(a, b) -> bool:
    return not (a[2] <= b[0] or b[2] <= a[0] or a[3] <= b[1] or b[3] <= a[1])


# ------------------------------------------------------------------ icons ---

def icon(kind: str, d: ImageDraw.ImageDraw, x: float, y: float, s: float, c) -> None:
    """A shape in a 1 by 1 box, scaled to s pixels with its corner at (x, y)."""
    def T(u: float, v: float) -> tuple[float, float]:
        return x + u * s, y + v * s

    if kind == "rocket":
        d.polygon([T(0.35, 0.30), T(0.65, 0.30), T(0.65, 0.74), T(0.35, 0.74)], fill=c)
        d.polygon([T(0.35, 0.30), T(0.50, 0.02), T(0.65, 0.30)], fill=c)
        d.polygon([T(0.35, 0.50), T(0.12, 0.80), T(0.35, 0.74)], fill=c)
        d.polygon([T(0.65, 0.50), T(0.88, 0.80), T(0.65, 0.74)], fill=c)
        d.polygon([T(0.40, 0.76), T(0.60, 0.76), T(0.50, 1.00)], fill=c)
    elif kind == "stack":
        d.polygon([T(0.30, 0.40), T(0.62, 0.40), T(0.70, 1.00), T(0.22, 1.00)], fill=c)
        d.ellipse((x + 0.34 * s, y + 0.10 * s, x + 0.62 * s, y + 0.38 * s), fill=c)
        d.ellipse((x + 0.56 * s, y + 0.16 * s, x + 0.80 * s, y + 0.40 * s), fill=c)
        d.ellipse((x + 0.72 * s, y + 0.04 * s, x + 0.98 * s, y + 0.30 * s), fill=c)
    elif kind == "lock":
        d.arc((x + 0.20 * s, y + 0.00 * s, x + 0.80 * s, y + 0.64 * s), 180, 360,
              fill=c, width=max(3, int(0.14 * s)))
        d.rounded_rectangle((x + 0.10 * s, y + 0.42 * s, x + 0.90 * s, y + 0.98 * s),
                            radius=max(2, int(0.10 * s)), fill=c)
        d.polygon([T(0.43, 0.58), T(0.57, 0.58), T(0.52, 0.88), T(0.48, 0.88)], fill=CARD)
    elif kind == "storm":
        d.ellipse((x + 0.02 * s, y + 0.16 * s, x + 0.54 * s, y + 0.60 * s), fill=c)
        d.ellipse((x + 0.32 * s, y + 0.04 * s, x + 0.94 * s, y + 0.58 * s), fill=c)
        d.rounded_rectangle((x + 0.04 * s, y + 0.36 * s, x + 0.92 * s, y + 0.60 * s),
                            radius=max(2, int(0.12 * s)), fill=c)
        d.polygon([T(0.54, 0.52), T(0.30, 1.00), T(0.47, 1.00), T(0.36, 1.34),
                   T(0.72, 0.84), T(0.54, 0.84), T(0.64, 0.52)], fill=c)
    elif kind == "burst":
        pts = []
        for k in range(24):
            ang = math.pi * k / 12
            r = 0.50 if k % 2 else 0.25
            pts.append(T(0.5 + r * math.cos(ang), 0.50 + r * math.sin(ang)))
        d.polygon(pts, fill=c)
    elif kind == "boat":
        d.polygon([T(0.04, 0.58), T(0.96, 0.58), T(0.76, 0.84), T(0.24, 0.84)], fill=c)
        d.polygon([T(0.46, 0.04), T(0.46, 0.52), T(0.10, 0.52)], fill=c)
        d.polygon([T(0.54, 0.16), T(0.86, 0.52), T(0.54, 0.52)], fill=c)
        for i, yy in enumerate((0.88, 1.02)):
            t = 0.30 if i == 0 else 0.44
            d.arc((x + t * s, y + (yy - 0.09) * s, x + (1 - t) * s, y + (yy + 0.09) * s),
                  0, 180, fill=c, width=max(2, int(0.07 * s)))
    elif kind == "scales":
        d.rounded_rectangle((x + 0.46 * s, y + 0.10 * s, x + 0.54 * s, y + 0.88 * s),
                            radius=max(2, int(0.04 * s)), fill=c)
        d.rounded_rectangle((x + 0.18 * s, y + 0.12 * s, x + 0.82 * s, y + 0.21 * s),
                            radius=max(2, int(0.04 * s)), fill=c)
        d.rounded_rectangle((x + 0.26 * s, y + 0.88 * s, x + 0.74 * s, y + 0.97 * s),
                            radius=max(2, int(0.04 * s)), fill=c)
        for c0 in (0.04, 0.63):
            d.arc((x + c0 * s, y + 0.20 * s, x + (c0 + 0.33) * s, y + 0.64 * s), 0, 180,
                  fill=c, width=max(2, int(0.07 * s)))
            d.line([T(c0 + 0.165, 0.15), T(c0 + 0.165, 0.34)], fill=c, width=max(2, int(0.05 * s)))
    elif kind == "bat":
        d.polygon([T(0.26, 0.02), T(0.52, 0.02), T(0.44, 0.62), T(0.28, 0.74)], fill=c)
        d.polygon([T(0.52, 0.02), T(0.58, 0.12), T(0.42, 0.68), T(0.30, 0.74)], fill=CARD)
        d.ellipse((x + 0.56 * s, y + 0.62 * s, x + 0.98 * s, y + 1.04 * s), fill=c)
        d.arc((x + 0.60 * s, y + 0.66 * s, x + 0.94 * s, y + 1.00 * s), 40, 220,
              fill=CARD, width=max(2, int(0.05 * s)))


# ------------------------------------------------------------------- page ---

def build() -> Image.Image:
    im = Image.new("RGB", (W, H), BG)
    d = ImageDraw.Draw(im)

    d.text((M, 22), spaced("SUNDAY", "  "), font=font(23), fill=ACCENT)
    d.text((M - 2, 48), "22 NOVEMBER 2026", font=font(58), fill=INK)
    d.text((M + 2, 128), "the world's news of that day, as reported", font=font(20, False), fill=MUTED)

    f_top = font(18)
    top = "ONE PICTURE · NINE STORIES · SIX CONTINENTS"
    d.text((W - M - width(d, top, f_top), 30), top, font=f_top, fill=MUTED)

    d.rectangle((M, 160, M + 150, 163), fill=ACCENT)
    d.rectangle((M + 150, 161, W - M, 162), fill=RULE)

    draw_map(im)

    cols, rows, gap = 3, 3, 14
    cw = (W - 2 * M - (cols - 1) * gap) // cols
    gy0 = 568
    ch = (H - M - gy0 - (rows - 1) * gap) // rows
    pad = 16

    for idx, (head, pill, colour, kind) in enumerate(CARDS):
        r, c = divmod(idx, cols)
        x = M + c * (cw + gap)
        y = gy0 + r * (ch + gap)
        d.rounded_rectangle((x, y, x + cw, y + ch), radius=10, fill=CARD, outline=CARD_EDGE)
        d.rounded_rectangle((x, y + 9, x + 5, y + ch - 9), radius=2, fill=colour)

        d.ellipse((x + pad, y + 12, x + pad + 30, y + 42), fill=colour)
        b = d.textbbox((0, 0), str(idx + 1), font=font(19))
        d.text((x + pad + 15 - (b[2] - b[0]) / 2 - b[0], y + 27 - (b[3] - b[1]) / 2 - b[1]),
               str(idx + 1), font=font(19), fill=(8, 12, 18))

        if kind == "euro":
            d.text((x + cw - 48, y + 4), "€", font=font(40), fill=colour)
        else:
            icon(kind, d, x + cw - 54, y + 8, 38, colour)

        f_pill = fit(d, pill, cw - 54 - 58, 16, 13)
        d.text((x + 54, y + 18), pill, font=f_pill, fill=(152, 169, 188))

        f_head, lines = headline(d, head, cw - 2 * pad)
        for i, line in enumerate(lines):
            d.text((x + pad, y + 50 + i * 32), line, font=f_head, fill=INK)

    return im


def main() -> None:
    here = os.path.dirname(os.path.abspath(__file__))
    out = os.path.join(os.path.dirname(here), "entry.png")
    im = build()
    im.save(out, format="PNG", optimize=True, compress_level=9)
    print(f"wrote {out} ({os.path.getsize(out)} bytes, {im.size[0]}x{im.size[1]})")


if __name__ == "__main__":
    main()
