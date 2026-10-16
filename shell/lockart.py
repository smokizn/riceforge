#!/usr/bin/env python3
"""Art for hyprlock.

    lockart.py ring OUT.png     the engraved astrolabe ring (static, built once)
    lockart.py moon             today's moon -> ~/.cache/riceforge/moon.png, prints the path
                                (hyprlock's image reload_cmd)
"""
import math
import sys
from pathlib import Path

import cairo

sys.path.insert(0, str(Path(__file__).resolve().parent))
import astro  # noqa: E402

BONE = (0.90, 0.87, 0.81)
SILVER = (0.73, 0.74, 0.76)
BRASS = (0.70, 0.60, 0.37)
STONE = (0.43, 0.42, 0.39)
PARCHMENT = (0.84, 0.80, 0.70)
ZODIAC = ["ARIES", "TAVRVS", "GEMINI", "CANCER", "LEO", "VIRGO",
          "LIBRA", "SCORPIVS", "SAGITTARIVS", "CAPRICORNVS", "AQVARIVS", "PISCES"]


def ring(out, size=760):
    s = cairo.ImageSurface(cairo.FORMAT_ARGB32, size, size)
    cr = cairo.Context(s)
    c = size / 2
    cr.set_line_cap(cairo.LINE_CAP_ROUND)

    def circle(r, lw, rgb, a=1.0, dash=None):
        cr.set_source_rgba(*rgb, a); cr.set_line_width(lw); cr.set_dash(dash or [])
        cr.new_path()   # show_text leaves a current point; don't connect to it
        cr.arc(c, c, r, 0, 2 * math.pi); cr.stroke(); cr.set_dash([])

    R = size / 2 - 8
    circle(R, 1.4, SILVER, 0.75)
    circle(R - 6, 0.7, SILVER, 0.45)
    # degree scale
    for i in range(360):
        a = math.radians(i) - math.pi / 2
        L = 14 if i % 30 == 0 else 8 if i % 5 == 0 else 4
        cr.set_source_rgba(*BONE, 0.7 if i % 5 == 0 else 0.35)
        cr.set_line_width(1.0 if i % 30 == 0 else 0.6)
        cr.move_to(c + (R - 6) * math.cos(a), c + (R - 6) * math.sin(a))
        cr.line_to(c + (R - 6 - L) * math.cos(a), c + (R - 6 - L) * math.sin(a)); cr.stroke()
    # zodiac band
    rz = R - 42
    circle(rz + 14, 0.7, SILVER, 0.5)
    circle(rz - 14, 0.7, SILVER, 0.5)
    cr.select_font_face("Cormorant SC", cairo.FONT_SLANT_NORMAL, cairo.FONT_WEIGHT_NORMAL)
    cr.set_font_size(13)
    for i, name in enumerate(ZODIAC):
        a0 = -math.pi / 2 + i * math.pi / 6
        cr.set_source_rgba(*SILVER, 0.6); cr.set_line_width(0.7)
        cr.move_to(c + (rz - 14) * math.cos(a0), c + (rz - 14) * math.sin(a0))
        cr.line_to(c + (rz + 14) * math.cos(a0), c + (rz + 14) * math.sin(a0)); cr.stroke()
        # letters along the arc, centred in the sign's 30°
        width = sum(cr.text_extents(ch).x_advance for ch in name) + 1.6 * (len(name) - 1)
        a = a0 + math.pi / 12 - (width / rz) / 2
        cr.set_source_rgba(*PARCHMENT, 0.75)
        for ch in name:
            adv = cr.text_extents(ch).x_advance
            cr.save()
            cr.translate(c + rz * math.cos(a), c + rz * math.sin(a))
            cr.rotate(a + math.pi / 2)
            cr.move_to(-adv / 2, 4.5); cr.show_text(ch)
            cr.restore()
            a += (adv + 1.6) / rz
    # inner dotted orbit and a brass sun at its top
    circle(rz - 40, 0.8, STONE, 0.8, [1.2, 5])
    sx, sy = c, c - (rz - 40)
    cr.set_source_rgba(*BRASS, 0.95)
    cr.new_path(); cr.arc(sx, sy, 6, 0, 2 * math.pi); cr.fill()
    cr.set_line_width(1.0)
    for i in range(16):
        b = i * math.pi / 8
        L = 15 if i % 2 == 0 else 11
        cr.move_to(sx + 9 * math.cos(b), sy + 9 * math.sin(b))
        cr.line_to(sx + L * math.cos(b), sy + L * math.sin(b))
    cr.stroke()
    s.write_to_png(str(out))


def moon(size=150):
    m = astro.moon_at()
    out = Path.home() / ".cache/riceforge"
    out.mkdir(parents=True, exist_ok=True)
    path = out / "moon.png"
    s = cairo.ImageSurface(cairo.FORMAT_ARGB32, size, size)
    cr = cairo.Context(s)
    cx = cy = size / 2
    r = size / 2 - 3
    cr.save(); cr.arc(cx, cy, r, 0, 2 * math.pi); cr.clip()
    cr.set_source_rgba(0.04, 0.04, 0.04, 0.85); cr.paint()
    cr.set_source_rgba(*STONE, 0.5); cr.set_line_width(0.8)
    for k in range(-size * 2, size * 2, 4):
        cr.move_to(cx + k - r, cy - r); cr.line_to(cx + k + r, cy + r)
    cr.stroke()
    c = math.cos(2 * math.pi * m.fraction)
    cr.set_source_rgba(*PARCHMENT, 0.95)
    steps = 120
    left, right = [], []
    for i in range(steps + 1):
        y = -r + 2 * r * i / steps
        w = math.sqrt(max(r * r - y * y, 0))
        a, b = (c * w, w) if m.waxing else (-w, -c * w)
        left.append((cx + a, cy + y)); right.append((cx + b, cy + y))
    cr.move_to(*left[0])
    for p in left[1:]:
        cr.line_to(*p)
    for p in reversed(right):
        cr.line_to(*p)
    cr.close_path(); cr.fill()
    cr.restore()
    cr.set_source_rgba(*SILVER, 0.9); cr.set_line_width(1.5)
    cr.arc(cx, cy, r, 0, 2 * math.pi); cr.stroke()
    s.write_to_png(str(path))
    print(path)


if __name__ == "__main__":
    if len(sys.argv) > 2 and sys.argv[1] == "ring":
        ring(Path(sys.argv[2]))
    elif len(sys.argv) > 1 and sys.argv[1] == "moon":
        moon()
    else:
        print(__doc__); sys.exit(2)
