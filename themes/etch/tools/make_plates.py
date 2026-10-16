#!/usr/bin/env python3
"""ETCH plate generator.

Turns the engravings in ~/Pictures/Wallpapers into catalogued "plates":
duotoned into graphite + zinc, framed by a hairline rule with lichen
printer's crop marks, and captioned like a museum catalogue.
Originals are never modified.

usage: make_plates.py OUT_DIR [WIDTH HEIGHT]
"""
import sys
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont, ImageOps

INK = (10, 10, 11)
ZINC = (226, 226, 224)
RULE = (42, 42, 46)
MUTED = (107, 107, 112)
LICHEN = (194, 217, 76)

SERIF_I = "/usr/share/fonts/noto/NotoSerif-LightItalic.ttf"
MONO = "/usr/share/fonts/TTF/IosevkaNerdFont-Regular.ttf"

WALLS = Path.home() / "Pictures/Wallpapers"
PLATES = [
    ("wallhaven-9ok23k.jpg", "I", "Trigonum oculorum, the watchers above and below"),
    ("wallhaven-w53de7.png", "II", "Draco, descending from the right margin"),
    ("wallhaven-zpvqyj.png", "III", "Fenestra, a window in three lights"),
]


def spaced(draw, xy, text, font, fill, tracking):
    x, y = xy
    for ch in text:
        draw.text((x, y), ch, font=font, fill=fill)
        x += draw.textlength(ch, font=font) + tracking
    return x


def plate(src, numeral, caption, out, w, h):
    img = Image.open(src).convert("L")
    img = ImageOps.fit(img, (w, h), Image.LANCZOS)
    img = ImageOps.colorize(img, black=INK, white=ZINC, mid=(112, 112, 116))
    d = ImageDraw.Draw(img)

    # page margins: top is deeper to clear the running head (waybar)
    l, t, r, b = 40, 56, w - 41, h - 41
    d.rectangle((l, t, r, b), outline=RULE, width=1)

    # printer's crop marks just outside each corner
    m, gap = 14, 6
    for cx, cy, sx, sy in ((l, t, -1, -1), (r, t, 1, -1), (l, b, -1, 1), (r, b, 1, 1)):
        d.line((cx + sx * gap, cy, cx + sx * (gap + m), cy), fill=LICHEN, width=1)
        d.line((cx, cy + sy * gap, cx, cy + sy * (gap + m)), fill=LICHEN, width=1)

    mono = ImageFont.truetype(MONO, 12)
    serif = ImageFont.truetype(SERIF_I, 15)
    folio = ImageFont.truetype(SERIF_I, 13)

    base = b - 30
    x = spaced(d, (l + 22, base + 2), f"PL. {numeral}", mono, LICHEN, 3)
    d.text((x + 14, base - 1), caption, font=serif, fill=MUTED)
    ftxt = f"fol. {numeral.lower()} r"
    d.text((r - 22 - d.textlength(ftxt, font=folio), base), ftxt, font=folio, fill=RULE)

    img.save(out, optimize=True)
    print(out)


def main():
    out = Path(sys.argv[1])
    w, h = (int(sys.argv[2]), int(sys.argv[3])) if len(sys.argv) > 3 else (1920, 1080)
    out.mkdir(parents=True, exist_ok=True)
    for name, numeral, caption in PLATES:
        src = WALLS / name
        if src.exists():
            plate(src, numeral, caption, out / f"plate-{numeral.lower()}.png", w, h)


if __name__ == "__main__":
    main()
