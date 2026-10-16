#!/usr/bin/env python3
"""Compose the NACRE · Visionary plates.

usage: compose.py OUT_DIR [plate-id ...]

Writes OUT_DIR/<id>.png (1920x1080) and OUT_DIR/plates.json. Each plate
records whether it is procedural (drawn here) or built on a public-domain
source (fetched by sources.py, attribution carried through).
"""
import json
import math
import sys
from pathlib import Path

import numpy as np
import cairo

sys.path.insert(0, str(Path(__file__).resolve().parent))
import engrave as E  # noqa: E402

W, H = 1920, 1080
HERE = Path(__file__).resolve().parent
SRC = HERE / "sources"
WALLS = Path.home() / "Pictures/Wallpapers"
FAM = E.serif_family()

# printed credit lines: the work's author, not the digitising institution
CREDITS = {
    "flammarion": "after the Flammarion engraving, 1888",
    "nasmyth-crater": "after James Nasmyth, 1874",
    "vesalius-musculorum": "after Andreas Vesalius, 1543",
    "dore-empyrean": "after Gustave Doré",
    "fludd-macrocosm": "after Robert Fludd, 1617–21",
}

ZODIAC = ["ARIES", "TAVRVS", "GEMINI", "CANCER", "LEO", "VIRGO",
          "LIBRA", "SCORPIVS", "SAGITTARIVS", "CAPRICORNVS", "AQVARIVS", "PISCES"]
ROMAN = ["I", "II", "III", "IV", "V", "VI", "VII", "VIII", "IX", "X", "XI", "XII"]


def cairo_matrix(xx, yx, xy, yy, x0, y0):
    """local (x, y) -> x*(xx, yx) + y*(xy, yy) + (x0, y0)"""
    return cairo.Matrix(xx, yx, xy, yy, x0, y0)


def src_meta(slug):
    meta = json.loads((SRC / "sources.json").read_text())
    return meta[slug]


def starfield(rng, density=0.0016, bright=0.00012, mask=None):
    m = E.stipple(np.ones((H, W), np.float32), rng, density)
    b = E.stipple(np.ones((H, W), np.float32), rng, bright, size=3)
    s = np.maximum(m * 0.7, b)
    return s * (1 if mask is None else mask)


def orbit_diagram(v, cx, cy, rng, scale=1.0, labels=True):
    """concentric orbits, planets, zodiac band: an armillary seen from above."""
    for i, r in enumerate((150, 230, 300, 380)):
        r *= scale
        v.ring(cx, cy, r, lw=0.9 if i % 2 else 1.3, dash=[2, 5] if i == 2 else None)
        a = rng.uniform(0, 2 * math.pi)
        px, py = cx + r * math.cos(a), cy + r * math.sin(a)
        v.ring(px, py, 6 + 2 * i, lw=1.0)
        v.cr.arc(px, py, 2.2, 0, 2 * math.pi); v.cr.fill()
    rz = 420 * scale
    v.ring(cx, cy, rz, lw=1.2); v.ring(cx, cy, rz + 44 * scale, lw=1.2)
    v.ticks(cx, cy, rz, rz + 8 * scale, 360, lw=0.5, major=5, r_major=rz + 14 * scale)
    v.ticks(cx, cy, rz, rz + 44 * scale, 12, lw=1.0)
    if labels:
        for i, name in enumerate(ZODIAC):
            a0 = -math.pi / 2 + i * (2 * math.pi / 12) + 0.05
            v.arc_text(name, cx, cy, rz + 30 * scale, a0, 13 * scale, FAM, spacing=0.004)


def sun(v, cx, cy, r, rng, rays=64, reach=2.6):
    v.ring(cx, cy, r, lw=1.6); v.ring(cx, cy, r * 0.82, lw=0.8)
    v.ticks(cx, cy, r * 0.86, r * 0.96, 48, lw=0.6)
    v.rays(cx, cy, r * 1.12, r * reach, rays, rng, lw=1.1, wavy=True)


# ── plates ───────────────────────────────────────────────────────────
def machina_mundi(rng):
    img = E.paper(H, W, rng)
    fl = E.load_gray(SRC / "flammarion.jpg", (0.015, 0.015, 0.985, 0.985), invert=True, levels=(0.12, 0.92))
    h = 1000; w = int(h * fl.shape[1] / fl.shape[0])
    fl = E.soft_edges(E.resize(fl, w, h), 70)
    lines = np.zeros((H, W), np.float32)
    E.place(lines, fl, W - w - 30, 40)
    v = E.Vec(W, H)
    orbit_diagram(v, 470, 540, rng, scale=0.95)
    lines = np.maximum(lines, v.mask() * 0.9)
    s = E.Vec(W, H); sun(s, 470, 540, 52, rng, rays=48, reach=2.4)
    img = E.ink_on(img, starfield(rng) * (1 - (E.radial(H, W, 470, 540, 470) < 1)), E.BONE, 0.55)
    img = E.ink_on(img, lines, E.BONE)
    img = E.ink_on(img, s.mask(), E.BRASS)
    return img, "ink · bone · brass", "cosmology", "flammarion"


def selenographia(rng):
    img = E.paper(H, W, rng, vignette=0.25)
    m = E.load_gray(SRC / "nasmyth-crater.jpg", (0.215, 0.215, 0.815, 0.735), levels=(0.04, 0.88), gamma=1.15)
    h = int(W * m.shape[0] / m.shape[1])
    m = E.resize(m, W, h)[h - H + 40: h + 40] if h > H else E.resize(m, W, H)
    m = m[:H]
    if m.shape[0] < H:
        m = np.vstack([np.zeros((H - m.shape[0], W), np.float32), m])
    img = E.ink_on(img, m, E.SILVER)
    # a row of engraved phases across the black sky
    v = E.Vec(W, H); hatch = np.zeros((H, W), np.float32)
    n = 9; r = 20
    for i in range(n):
        cx, cy = W / 2 + (i - (n - 1) / 2) * 92, 120
        v.ring(cx, cy, r, lw=1.1)
        k = i / (n - 1)  # 0 new .. 1 new again
        lit = 1 - abs(1 - 2 * k)  # 0..1..0
        # lit region via terminator ellipse; hatch the dark side
        side = 1 if k < 0.5 else -1
        disc = E.radial(H, W, cx, cy, r) < 1
        yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
        tx = (xx - cx) / r
        bound = np.sqrt(np.clip(1 - ((yy - cy) / r) ** 2, 0, 1)) * (1 - 2 * lit)
        dark = disc & ((side * tx) < bound)
        hatch = np.maximum(hatch, E.line_screen(dark.astype(np.float32) * 0.45, 35, 3.2))
    v.cr.set_line_width(0.7)
    v.cr.move_to(W / 2 - 420, 170); v.cr.line_to(W / 2 + 420, 170); v.cr.stroke()
    v.text("SELENOGRAPHIA", W / 2, 205, 17, FAM, anchor="center", spacing=6)
    img = E.ink_on(img, np.maximum(v.mask(), hatch), E.SILVER, 0.95)
    return img, "ink · lunar silver", "lunar", "nasmyth-crater"


def engraved_range(rng2, horizon, height, base, tone_k, ang, period, jag=1.0):
    mask, shade, top, form = E.mountain_range(H, W, rng2, horizon, height, base, jag)
    hatch = E.engrave_tone(shade * tone_k, angle=ang, period=period, cross_at=0.7, wave=form * 7)
    cont = E.contours(form, np.linspace(0.15, 0.9, 6), 0.006) * 0.35 * tone_k
    ridge = E.ridge_line(top, H, 1.5)
    return mask, np.maximum(hatch, cont), ridge


def anatomia_montium(rng):
    img = E.paper(H, W, rng)
    ves = E.load_gray(SRC / "vesalius-musculorum.jpg", (0.0, 0.03, 1.0, 1.0), invert=True, levels=(0.16, 0.66))
    hh, ww = ves.shape
    ves[0:int(0.125 * hh), int(0.03 * ww):int(0.355 * ww)] = 0  # the printed caption
    h = 1080; w = int(h * ww / hh)
    ves = E.soft_edges(E.resize(ves, w, h), 60)
    fx = 230
    lines = np.zeros((H, W), np.float32)
    covered = np.zeros((H, W), np.float32)
    rng2 = np.random.default_rng(11)
    # far range first; each nearer range occludes what is behind it
    for horizon, height, tk, base, ang, per in [(760, 330, 0.5, 340, -24, 5.2),
                                                (880, 270, 0.75, 260, -34, 4.6),
                                                (1000, 200, 1.0, 200, -42, 4.2)]:
        mask, hatch, ridge = engraved_range(rng2, horizon, height, base, tk, ang, per)
        taper = np.clip((np.arange(W) - (fx + w * 0.62)) / 420.0, 0, 1)[None, :]
        mask = mask * taper
        lines = lines * (1 - mask) + hatch * mask
        lines = np.maximum(lines * (1 - ridge * taper), ridge * taper * 0.95)
        covered = np.maximum(covered, mask)
    cl, body = E.stratus(H, W, rng2, 745, 40, x0=fx + w * 0.6, x1=W - 30)
    lines = lines * (1 - body) + cl
    covered = np.maximum(covered, body)
    E.place(lines, ves, fx, 0)
    s = E.Vec(W, H); sun(s, 1480, 290, 66, rng, rays=56, reach=2.7)
    img = E.ink_on(img, starfield(rng, 0.0008) * (1 - covered), E.BONE, 0.5)
    img = E.ink_on(img, lines, E.BONE)
    img = E.ink_on(img, s.mask() * (1 - covered), E.BRASS)
    return img, "ink · bone · brass", "anatomy & landscape", "vesalius-musculorum"


def empyrean(rng):
    img = E.paper(H, W, rng, vignette=0.45)
    d = E.load_gray(SRC / "dore-empyrean.jpg", (0.012, 0.012, 0.988, 0.985), levels=(0.06, 0.95), gamma=1.15)
    h = 1080; w = int(h * d.shape[1] / d.shape[0])
    d = E.resize(d, w, h)
    x0 = (W - w) // 2
    lines = np.zeros((H, W), np.float32); E.place(lines, d, x0, 0)
    cx, cy = W / 2, 0.40 * H
    # light falls off from the rose, not from the print's rectangle
    fall = np.clip(1.25 - E.radial(H, W, cx, cy + 90, 560), 0, 1) ** 1.4
    lines *= fall
    v = E.Vec(W, H)
    for i, r in enumerate((520, 590, 660, 760)):
        v.ring(cx, cy, r, lw=0.8, dash=[1.5, 6] if i % 2 else None)
    v.ticks(cx, cy, 660, 672, 180, lw=0.6)
    outside = np.clip((np.abs(np.arange(W) - W / 2) - w / 2 + 60) / 120, 0, 1)[None, :]
    lines = np.maximum(lines, v.mask() * outside * 0.7)
    img = E.ink_on(img, starfield(rng, 0.0022) * outside, E.BONE, 0.6)
    img = E.ink_on(img, lines, E.PARCHMENT)
    return img, "ink · parchment", "celestial", "dore-empyrean"


def macrocosm(rng):
    img = E.paper(H, W, rng)
    f = E.load_gray(SRC / "fludd-macrocosm.png", (0.0, 0.0, 1.0, 1.0), invert=True, levels=(0.25, 0.92))
    h = 880; w = int(h * f.shape[1] / f.shape[0])
    f = E.resize(f, w, h)
    lines = np.zeros((H, W), np.float32); E.place(lines, f, (W - w) // 2, (H - h) // 2 + 6)
    cx, cy = W / 2, H / 2
    v = E.Vec(W, H)
    v.ring(cx, cy, 500, lw=1.2); v.ring(cx, cy, 512, lw=0.7)
    v.ticks(cx, cy, 500, 508, 360, lw=0.5, major=10, r_major=516)
    for i, n in enumerate(ROMAN):
        a = -math.pi / 2 + i * math.pi / 6
        v.text(n, cx + 535 * math.cos(a), cy + 535 * math.sin(a) + 5, 14, FAM, anchor="center")
    gold = E.Vec(W, H); sun(gold, cx, cy - 500 - 70, 16, rng, rays=24, reach=2.2)
    silver = E.Vec(W, H)
    silver.cr.arc(cx, cy + 570, 20, 0, 2 * math.pi)
    silver.cr.arc_negative(cx + 9, cy + 566, 17, 2 * math.pi, 0)
    silver.cr.fill()
    img = E.ink_on(img, starfield(rng, 0.0015) * (E.radial(H, W, cx, cy, 520) > 1), E.BONE, 0.55)
    img = E.ink_on(img, np.maximum(lines, v.mask() * 0.85), E.BONE)
    img = E.ink_on(img, gold.mask(), E.BRASS)
    img = E.ink_on(img, silver.mask(), E.SILVER)
    return img, "ink · bone · brass · silver", "hermetic diagram", "fludd-macrocosm"


def ouroboros_eclipse(rng):
    img = E.paper(H, W, rng)
    cx, cy = W / 2, H / 2
    v = E.Vec(W, H)
    # corona
    v.rays(cx, cy, 156, 330, 520, rng, lw=0.7, jitter=0.6)
    v.ring(cx, cy, 152, lw=2.0)
    corona = v.mask()
    glow = np.clip(1.25 - E.radial(H, W, cx, cy, 300), 0, 1) * (E.radial(H, W, cx, cy, 152) > 1)
    corona = np.maximum(corona * 0.85, E.stipple(glow, rng, 0.5))
    # ouroboros: a serpent eating its tail around the eclipse
    sv = E.Vec(W, H); R = 420
    head_a = -math.pi / 2
    neck_a = head_a + 0.17                 # where the body leaves the head
    span = 2 * math.pi - 0.14              # body runs round until its tail is in the mouth
    def width(t):  # t 0 (neck) .. 1 (tail tip)
        return 44 * (1 - 0.84 * t ** 1.5)
    N = 440
    outer, inner = [], []
    for k in range(N + 1):
        t = k / N
        a = neck_a + t * span
        wv = width(t)
        outer.append((cx + (R + wv / 2) * math.cos(a), cy + (R + wv / 2) * math.sin(a)))
        inner.append((cx + (R - wv / 2) * math.cos(a), cy + (R - wv / 2) * math.sin(a)))
    cr = sv.cr; cr.set_line_width(1.6)
    # both flanks, joined only at the tail tip (the neck runs into the head)
    cr.move_to(*outer[0])
    for p_ in outer[1:]:
        cr.line_to(*p_)
    for p_ in reversed(inner):
        cr.line_to(*p_)
    cr.stroke()
    # scales: chevrons across the body
    cr.set_line_width(0.8)
    for k in range(4, N - 4, 3):
        t = k / N
        a = neck_a + t * span
        wv = width(t)
        da = 0.012 * (1 - 0.5 * t)
        cr.move_to(cx + (R + wv / 2) * math.cos(a), cy + (R + wv / 2) * math.sin(a))
        cr.line_to(cx + R * math.cos(a + da), cy + R * math.sin(a + da))
        cr.line_to(cx + (R - wv / 2) * math.cos(a), cy + (R - wv / 2) * math.sin(a))
    cr.stroke()
    # the head, in a frame aligned to the ring: +x toward the tail, +y outward
    ha = head_a + 0.075
    hx, hy = cx + R * math.cos(ha), cy + R * math.sin(ha)
    dx, dy = math.sin(ha), -math.cos(ha)          # tangent, toward decreasing angle
    rx, ry = math.cos(ha), math.sin(ha)           # radial, outward
    cr.save()
    cr.transform(cairo_matrix(dx, dy, rx, ry, hx, hy))
    cr.scale(1.3, 1.3)
    cr.set_line_width(1.25)
    # upper jaw: neck -> brow -> snout
    cr.move_to(-36, 22); cr.curve_to(-18, 30, 10, 28, 28, 14)
    cr.curve_to(36, 9, 42, 6, 44, 4)
    # lower jaw, hinged open around the tail
    cr.move_to(-36, -22); cr.curve_to(-14, -26, 12, -22, 36, -14)
    cr.stroke()
    cr.set_line_width(1.0)
    cr.move_to(44, 4); cr.curve_to(30, 2, 14, 0, 0, -2)        # upper lip
    cr.move_to(36, -14); cr.curve_to(24, -10, 12, -6, 0, -2)   # lower lip
    cr.stroke()
    cr.set_line_width(0.7)                                     # brow scales
    for i in range(5):
        x = -24 + i * 9
        cr.move_to(x, 23 - i * 1.6); cr.curve_to(x + 3, 18 - i, x + 7, 18 - i, x + 9, 22 - i * 1.6)
    cr.stroke()
    cr.set_line_width(1.1)
    cr.arc(6, 14, 5.2, 0, 2 * math.pi); cr.stroke()             # eye
    cr.arc(6, 14, 2.0, 0, 2 * math.pi); cr.fill()
    cr.arc(36, 8.5, 1.2, 0, 2 * math.pi); cr.fill()             # nostril
    cr.restore()
    # body shading: hatch the lower half of the ring
    body = (np.abs(E.radial(H, W, cx, cy, 1) - R) < 18).astype(np.float32)
    yy = np.arange(H)[:, None]
    shade = body * np.clip((yy - cy) / R, 0, 1)
    sv_mask = np.maximum(sv.mask(), E.line_screen(shade * 0.55, 60, 3.4))
    # outer dial
    d = E.Vec(W, H)
    d.ring(cx, cy, 500, lw=1.2); d.ring(cx, cy, 506, lw=0.6)
    d.ticks(cx, cy, 500, 492, 360, lw=0.5, major=30, r_major=480)
    for i, n in enumerate(ROMAN):
        a = -math.pi / 2 + i * math.pi / 6
        d.text(n, cx + 528 * math.cos(a), cy + 528 * math.sin(a) + 5, 14, FAM, anchor="center")
    # baily's bead
    b = E.Vec(W, H); a = -0.75
    bx, by = cx + 152 * math.cos(a), cy + 152 * math.sin(a)
    b.cr.arc(bx, by, 5, 0, 2 * math.pi); b.cr.fill()
    b.rays(bx, by, 9, 46, 16, rng, lw=0.8)
    img = E.ink_on(img, starfield(rng, 0.0018) * (E.radial(H, W, cx, cy, 520) > 1), E.BONE, 0.6)
    img = E.ink_on(img, corona, E.SILVER)
    img = E.ink_on(img, np.maximum(sv_mask, d.mask() * 0.8), E.BONE)
    img = E.ink_on(img, b.mask(), E.BRASS)
    return img, "ink · bone · silver · brass", "eclipse & serpent", None


def montes_lunae(rng):
    img = E.paper(H, W, rng)
    lines = np.zeros((H, W), np.float32)
    covered = np.zeros((H, W), np.float32)
    rng2 = np.random.default_rng(23)
    specs = [(720, 250, 0.32, 380, -18, 5.6, 1.3), (850, 270, 0.6, 300, -30, 4.9, 1.2),
             (990, 220, 1.0, 230, -42, 4.3, 1.0)]
    clouds = [(735, 30), (868, 36)]
    for i, (horizon, height, tk, base, ang, per, jag) in enumerate(specs):
        mask, hatch, ridge = engraved_range(rng2, horizon, height, base, tk, ang, per, jag)
        lines = lines * (1 - mask) + hatch * mask
        lines = np.maximum(lines * (1 - ridge), ridge * 0.95)
        covered = np.maximum(covered, mask)
        if i < len(clouds):
            cy, sz = clouds[i]
            cl, body = E.stratus(H, W, rng2, cy, sz, x0=0, x1=W)
            lines = lines * (1 - body) + cl
            covered = np.maximum(covered, body)
    # the moon: engraved disc, maria stippled, dark limb hatched
    mx, my, mr = 1450, 250, 150
    disc = (E.radial(H, W, mx, my, mr) < 1).astype(np.float32)
    maria = np.clip((E.fractal(H, W, rng2, 70, 4) - 0.52) * 5, 0, 1) * disc
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    limb = np.clip(((xx - mx) / mr + 0.35) * 1.4, 0, 1) * disc
    moon_lines = np.maximum(E.stipple(maria * 0.9, rng2, 0.55), E.line_screen(limb * 0.5, 120, 3.2))
    v = E.Vec(W, H); v.ring(mx, my, mr, lw=1.5); v.ring(mx, my, mr + 26, lw=0.6, dash=[1.5, 6])
    moon = np.maximum(moon_lines, v.mask()) * (1 - covered)
    img = E.ink_on(img, starfield(rng, 0.0016) * (1 - covered) * (1 - disc), E.BONE, 0.6)
    img = E.ink_on(img, lines, E.BONE)
    img = E.ink_on(img, moon, E.SILVER)
    return img, "ink · bone · silver", "landscape & lunar", None


def oculus(rng):
    img = E.paper(H, W, rng)
    cx, cy = W / 2, H / 2 + 20
    gold = E.Vec(W, H)
    gold.rays(cx, cy, 300, 640, 96, rng, lw=0.9, jitter=0.45, wavy=True)
    rays = gold.mask() * (E.radial(H, W, cx, cy, 300) > 1)
    v = E.Vec(W, H)
    side = 560; hgt = side * math.sqrt(3) / 2
    for k, lw in ((0, 1.6), (14, 0.7)):
        s2 = side - 2 * k * math.sqrt(3)
        h2 = s2 * math.sqrt(3) / 2
        v.cr.set_line_width(lw)
        v.cr.move_to(cx, cy - 2 * h2 / 3); v.cr.line_to(cx + s2 / 2, cy + h2 / 3)
        v.cr.line_to(cx - s2 / 2, cy + h2 / 3); v.cr.close_path(); v.cr.stroke()
    # the eye
    ey = cy + 18; ew = 170
    cr = v.cr; cr.set_line_width(1.6)
    cr.move_to(cx - ew, ey); cr.curve_to(cx - 70, ey - 95, cx + 70, ey - 95, cx + ew, ey)
    cr.curve_to(cx + 70, ey + 95, cx - 70, ey + 95, cx - ew, ey); cr.stroke()
    v.ring(cx, ey, 58, lw=1.4)
    v.ticks(cx, ey, 24, 56, 120, lw=0.6)
    cr.arc(cx, ey, 22, 0, 2 * math.pi); cr.fill()
    # lids: fine parallel lines above and below
    lid = ((E.radial(H, W, cx, ey, 1) > 62) &
           (np.abs(np.mgrid[0:H, 0:W][0] - ey) < 60)).astype(np.float32)
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    inside = (((xx - cx) / ew) ** 2 + ((yy - ey) / 70) ** 2 < 1).astype(np.float32)
    lid_hatch = E.line_screen(lid * inside * 0.35, 0, 3.0)
    o = E.Vec(W, H)
    for r in (400, 470):
        o.ring(cx, cy, r, lw=0.8, dash=[1.5, 6] if r == 470 else None)
    o.ticks(cx, cy, 400, 410, 120, lw=0.5)
    hl = E.Vec(W, H); hl.cr.arc(cx + 14, ey - 12, 6, 0, 2 * math.pi); hl.cr.fill()
    img = E.ink_on(img, starfield(rng, 0.0014) * (E.radial(H, W, cx, cy, 650) > 1), E.BONE, 0.55)
    img = E.ink_on(img, rays, E.BRASS, 0.75)
    img = E.ink_on(img, np.maximum(np.maximum(v.mask(), lid_hatch), o.mask() * 0.7), E.BONE)
    img = E.ink_on(img, hl.mask(), E.INK)
    return img, "ink · bone · brass", "occult geometry", None


def reprint(name, file, scale=0.92, colour=E.BONE):
    def fn(rng):
        img = E.paper(H, W, rng, vignette=0.3)
        g = E.load_gray(WALLS / file, levels=(0.10, 1.0))
        h = int(H * scale); w = int(h * g.shape[1] / g.shape[0])
        if w > W:
            w = W; h = int(w * g.shape[0] / g.shape[1])
        g = E.soft_edges(E.resize(g, w, h), 40)
        lines = np.zeros((H, W), np.float32); E.place(lines, g, (W - w) // 2, (H - h) // 2)
        img = E.ink_on(img, lines, colour)
        return img, "ink · bone", "your engravings", None
    fn.__name__ = name
    return fn


PLATES = [
    ("machina-mundi",     "Machina Mundi",      machina_mundi),
    ("anatomia-montium",  "Anatomia Montium",   anatomia_montium),
    ("ouroboros-eclipse", "Ouroboros Eclipsis", ouroboros_eclipse),
    ("montes-lunae",      "Montes Lunae",       montes_lunae),
    ("oculus",            "Oculus Mundi",       oculus),
    ("empyrean",          "The Empyrean",       empyrean),
    ("macrocosm",         "Macrocosmus",        macrocosm),
    ("selenographia",     "Selenographia",      selenographia),
    ("fenestra",          "Fenestra",           reprint("fenestra", "wallhaven-zpvqyj.png")),
    ("draco",             "Draco",              reprint("draco", "wallhaven-w53de7.png", 1.0)),
    ("trigonum",          "Trigonum",           reprint("trigonum", "wallhaven-9ok23k.jpg")),
]


def main():
    out = Path(sys.argv[1]); out.mkdir(parents=True, exist_ok=True)
    only = set(sys.argv[2:])
    index_path = out / "plates.json"
    index = {p["id"]: p for p in json.loads(index_path.read_text())} if index_path.exists() else {}
    for n, (pid, title, fn) in enumerate(PLATES, start=1):
        if only and pid not in only:
            continue
        rng = np.random.default_rng(n * 101)
        img, palette, category, source = fn(rng)
        caption = f"PL. {ROMAN[n - 1] if n <= 12 else n}  ·  {title.upper()}"
        credit = None
        attribution = None
        if source:
            m = src_meta(source)
            credit = CREDITS.get(source) or f"after {m['artist'].split(',')[0]}"
            attribution = {"title": m["title"], "artist": m["artist"], "date": m["date"],
                           "licence": m["licence"], "page": m["page"]}

        img = E.plate_mark(img, caption=caption, credit=credit, family=FAM)
        E.save(img, out / f"{pid}.png")
        index[pid] = {
            "id": pid, "title": title, "file": f"{pid}.png", "palette": palette,
            "category": category, "aspect": "16:9", "size": [W, H],
            "origin": "public-domain composite" if source else
                      ("re-print of user wallpaper" if fn.__name__ in ("fenestra", "draco", "trigonum") else "procedural"),
            "attribution": attribution, "order": n,
        }
        print(f"{pid:18} {index[pid]['origin']}")
    index_path.write_text(json.dumps(sorted(index.values(), key=lambda p: p["order"]), indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
