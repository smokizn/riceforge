"""Engraving toolkit for the NACRE · Visionary plates.

Everything works on float32 "ink" masks in [0, 1] (1 = a bright engraved
line on the dark plate). Tone becomes line through line screens: parallel
lines whose width follows the tone, with a cross-hatch added in the deepest
values, the way a burin renders shade. Vector work (rings, rays, the serpent,
the eye, lettering) goes through cairo and comes back as masks too.
"""
import math

import cairo
import numpy as np
from PIL import Image, ImageFilter

# palette (RGB 0..255)
INK = np.array([11, 10, 10], np.float32)
CHARCOAL = np.array([21, 20, 19], np.float32)
BONE = np.array([230, 223, 207], np.float32)
PARCHMENT = np.array([214, 203, 178], np.float32)
SILVER = np.array([185, 188, 194], np.float32)
BRASS = np.array([179, 154, 94], np.float32)
SEPIA = np.array([138, 117, 89], np.float32)

SERIF_CANDIDATES = ["Cormorant SC", "Cormorant", "Noto Serif"]


# ── noise ────────────────────────────────────────────────────────────
def value_noise(h, w, cell, rng):
    gh, gw = h // cell + 3, w // cell + 3
    g = rng.random((gh, gw)).astype(np.float32)
    img = Image.fromarray((g * 255).astype(np.uint8)).resize(
        (gw * cell, gh * cell), Image.BICUBIC)
    a = np.asarray(img, np.float32)[:h, :w] / 255.0
    return a


def fractal(h, w, rng, base=256, octaves=6, persistence=0.5):
    out = np.zeros((h, w), np.float32)
    amp, total, cell = 1.0, 0.0, base
    for _ in range(octaves):
        out += amp * value_noise(h, w, max(2, int(cell)), rng)
        total += amp
        amp *= persistence
        cell /= 2
    return out / total


# ── tone → line ──────────────────────────────────────────────────────
def line_screen(tone, angle_deg, period, softness=0.9, offset=0.0):
    """parallel engraved lines; line width ~ tone (0 none .. 1 solid)."""
    h, w = tone.shape
    a = math.radians(angle_deg)
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    u = (xx * math.cos(a) + yy * math.sin(a)) / period + offset
    d = np.abs(u - np.round(u)) * 2.0          # 0 at line centre .. 1 between lines
    half = np.clip(tone, 0, 1)                  # wanted coverage
    edge = softness / period
    # the presence term keeps zero tone at exactly zero (no ghost lines)
    return np.clip((half - d) / max(edge, 1e-3) + 0.5, 0, 1) * np.clip(half * 10, 0, 1)


def engrave_tone(tone, angle=-28, period=4.2, cross_at=0.62, wave=None):
    """burin rendering of a tone map: one screen, cross-hatch in the darks.

    wave: optional array added to the screen phase, so lines follow form.
    """
    if wave is not None:
        h, w = tone.shape
        a = math.radians(angle)
        yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
        u = (xx * math.cos(a) + yy * math.sin(a)) / period + wave
        d = np.abs(u - np.round(u)) * 2.0
        t = np.clip(tone, 0, 1)
        main = np.clip((t - d) / (0.9 / period) + 0.5, 0, 1) * np.clip(t * 10, 0, 1)
    else:
        main = line_screen(tone, angle, period)
    deep = np.clip((tone - cross_at) / (1 - cross_at), 0, 1)
    cross = line_screen(deep * 0.8, angle + 74, period * 1.15)
    return np.maximum(main, cross)


def stipple(tone, rng, density=0.35, size=1):
    """random dots, probability ~ tone."""
    m = (rng.random(tone.shape) < np.clip(tone, 0, 1) * density).astype(np.float32)
    if size > 1:
        m = np.asarray(Image.fromarray((m * 255).astype(np.uint8)).filter(
            ImageFilter.MaxFilter(size)), np.float32) / 255.0
    return m


def contours(field, levels, width=0.012):
    """engraved isolines of a scalar field (e.g. mountain height)."""
    out = np.zeros_like(field)
    for lv in levels:
        out = np.maximum(out, np.clip(1 - np.abs(field - lv) / width, 0, 1))
    return out


# ── terrain ──────────────────────────────────────────────────────────
def ridged(h, w, rng, base=300, octaves=6):
    n = fractal(h, w, rng, base, octaves)
    return 1 - np.abs(n * 2 - 1)


def blur(a, r):
    im = Image.fromarray((np.clip(a, 0, 1) * 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(r))
    return np.asarray(im, np.float32) / 255.0


def mountain_range(h, w, rng, horizon, height, base=260, jag=1.0):
    """a range of peaks: (mask, shade, top, form).

    shade: lit tone of the faces (light from the upper left), smooth enough
    for engraving. form: a height field used to bend the hatching so lines
    follow the slopes instead of lying flat on them.
    """
    prof = fractal(1, w, rng, base, 7)[0]
    prof = (prof - prof.min()) / (np.ptp(prof) + 1e-6)
    peaks = 1 - np.abs(fractal(1, w, rng, base * 2, 3)[0] * 2 - 1)
    prof = np.clip(0.55 * prof + 0.45 * peaks, 0, 1) ** (1.25 / jag)
    top = horizon - prof * height
    yy = np.arange(h, dtype=np.float32)[:, None]
    mask = (yy >= top[None, :]).astype(np.float32)
    # form: distance below the ridge, modulated by large ridged noise (spurs and gullies)
    below = np.clip((yy - top[None, :]) / (height + 1), 0, 1)
    spurs = blur(ridged(h, w, rng, base // 2, 4), 3)
    form = blur(np.clip(1 - below * 1.3 + (spurs - 0.5) * 0.6, 0, 1), 2)
    gy, gx = np.gradient(form)
    light = np.clip(0.5 + (-gx * 1.0 - gy * 0.35) * 55, 0, 1)
    shade = blur(np.clip(0.18 + 0.82 * light * (1 - 0.55 * below), 0, 1), 1.5)
    return mask, shade, top, form


def ridge_line(top, h, lw=1.4):
    """the silhouette stroked as one bright engraved line."""
    w = top.shape[0]
    v = Vec(w, h)
    v.cr.set_line_width(lw)
    v.cr.move_to(0, float(top[0]))
    for x in range(1, w, 2):
        v.cr.line_to(x, float(top[x]))
    v.cr.stroke()
    return v.mask()


def cloud_billows(w, h, rng, cy, x0, x1, size=46, rows=2):
    """engraved cumulus: scalloped outlines, shaded underneath."""
    v = Vec(w, h)
    cr = v.cr
    fill = Vec(w, h)
    x = x0
    while x < x1:
        r = size * rng.uniform(0.7, 1.25)
        for row in range(rows):
            yy = cy - row * r * 0.55 + rng.uniform(-6, 6)
            xx = x + row * r * 0.5
            cr.set_line_width(1.2)
            cr.arc(xx, yy, r, math.pi * 1.05, math.pi * 1.95); cr.stroke()
            fill.cr.arc(xx, yy, r, 0, 2 * math.pi); fill.cr.fill()
        x += r * rng.uniform(1.1, 1.5)
    body = fill.mask()
    yy = np.arange(h, dtype=np.float32)[:, None]
    under = body * np.clip((yy - (cy - size * 0.2)) / (size * 1.2), 0, 1)
    shade = line_screen(under * 0.6, 0, 3.4)
    return np.maximum(v.mask(), shade), body


def stratus(h, w, rng, cy, thickness=60, x0=0, x1=None, period=3.6, coverage=0.5):
    """cloud bank as engravers drew it: wavy horizontal lines in a soft band."""
    x1 = w if x1 is None else x1
    yy = np.arange(h, dtype=np.float32)[:, None]
    n = fractal(h, w, rng, 160, 5)
    edge = cy + (fractal(1, w, rng, 90, 4)[0] - 0.5) * thickness * 1.2
    band = np.exp(-((yy - edge[None, :]) / thickness) ** 2)
    body = np.clip((n - 0.42) * 3.2, 0, 1) * band
    xs = np.arange(w, dtype=np.float32)[None, :]
    body *= np.clip((xs - x0) / 80, 0, 1) * np.clip((x1 - xs) / 80, 0, 1)
    wave = (fractal(h, w, rng, 120, 3) - 0.5) * 2.2
    h2, w2 = body.shape
    u = yy / period + wave
    d = np.abs(u - np.round(u)) * 2.0
    lines = np.clip((body * coverage - d) / (0.9 / period) + 0.5, 0, 1) * np.clip(body * 10, 0, 1)
    occl = np.clip(body * 1.6, 0, 1)
    return lines, occl


# ── cairo vectors ────────────────────────────────────────────────────
class Vec:
    """cairo canvas that hands back an ink mask."""

    def __init__(self, w, h):
        self.w, self.h = w, h
        self.surf = cairo.ImageSurface(cairo.FORMAT_A8, w, h)
        self.cr = cairo.Context(self.surf)
        self.cr.set_line_cap(cairo.LINE_CAP_ROUND)
        self.cr.set_line_join(cairo.LINE_JOIN_ROUND)

    def mask(self):
        self.surf.flush()
        stride = self.surf.get_stride()
        buf = np.frombuffer(self.surf.get_data(), np.uint8).reshape(self.h, stride)[:, :self.w]
        return buf.astype(np.float32) / 255.0

    # primitives
    def ring(self, cx, cy, r, lw=1.2, dash=None):
        cr = self.cr
        cr.new_path(); cr.set_line_width(lw)
        cr.set_dash(dash or [])
        cr.arc(cx, cy, r, 0, 2 * math.pi); cr.stroke(); cr.set_dash([])

    def ellipse(self, cx, cy, rx, ry, rot=0.0, lw=1.2, dash=None):
        cr = self.cr
        cr.save(); cr.translate(cx, cy); cr.rotate(rot); cr.scale(rx, ry)
        cr.new_path(); cr.arc(0, 0, 1, 0, 2 * math.pi); cr.restore()
        cr.set_line_width(lw); cr.set_dash(dash or []); cr.stroke(); cr.set_dash([])

    def ticks(self, cx, cy, r1, r2, n, lw=1.0, major=None, r_major=None, phase=0.0):
        cr = self.cr; cr.set_line_width(lw)
        for i in range(n):
            a = phase + 2 * math.pi * i / n
            rr = r_major if (major and i % major == 0 and r_major) else r2
            cr.move_to(cx + r1 * math.cos(a), cy + r1 * math.sin(a))
            cr.line_to(cx + rr * math.cos(a), cy + rr * math.sin(a))
        cr.stroke()

    def rays(self, cx, cy, r1, r2, n, rng, lw=1.0, jitter=0.35, wavy=False):
        cr = self.cr; cr.set_line_width(lw)
        for i in range(n):
            a = 2 * math.pi * i / n + rng.uniform(-0.3, 0.3) * (2 * math.pi / n)
            L = r1 + (r2 - r1) * (1 - jitter * rng.random())
            if wavy and i % 2:
                # flame-like ray (the sun's alternate rays in old engravings)
                cr.move_to(cx + r1 * math.cos(a), cy + r1 * math.sin(a))
                steps = 14
                for s in range(1, steps + 1):
                    t = s / steps
                    rr = r1 + (L - r1) * t
                    off = math.sin(t * math.pi * 3) * 0.035 * (1 - t)
                    cr.line_to(cx + rr * math.cos(a + off), cy + rr * math.sin(a + off))
            else:
                cr.move_to(cx + r1 * math.cos(a), cy + r1 * math.sin(a))
                cr.line_to(cx + L * math.cos(a), cy + L * math.sin(a))
        cr.stroke()

    def text(self, s, x, y, size, family=None, anchor="left", spacing=0.0, slant=False):
        cr = self.cr
        fam = family or SERIF_CANDIDATES[0]
        cr.select_font_face(fam, cairo.FONT_SLANT_ITALIC if slant else cairo.FONT_SLANT_NORMAL,
                            cairo.FONT_WEIGHT_NORMAL)
        cr.set_font_size(size)
        width = sum(cr.text_extents(ch).x_advance for ch in s) + spacing * (len(s) - 1)
        if anchor == "center":
            x -= width / 2
        elif anchor == "right":
            x -= width
        for ch in s:
            cr.move_to(x, y); cr.show_text(ch)
            x += cr.text_extents(ch).x_advance + spacing

    def arc_text(self, s, cx, cy, r, start, size, family=None, spacing=0.02):
        """lettering around a circle (zodiac ring style)."""
        cr = self.cr
        cr.select_font_face(family or SERIF_CANDIDATES[0], cairo.FONT_SLANT_NORMAL, cairo.FONT_WEIGHT_NORMAL)
        cr.set_font_size(size)
        a = start
        for ch in s:
            adv = cr.text_extents(ch).x_advance
            cr.save()
            cr.translate(cx + r * math.cos(a), cy + r * math.sin(a))
            cr.rotate(a + math.pi / 2)
            cr.move_to(-adv / 2, 0); cr.show_text(ch)
            cr.restore()
            a += (adv / r) + spacing


def serif_family():
    """first installed serif from the candidates (pango/fontconfig names)."""
    import subprocess
    try:
        fams = subprocess.run(["fc-list", ":", "family"], capture_output=True, text=True).stdout
    except OSError:
        return "Noto Serif"
    for cand in SERIF_CANDIDATES:
        if any(cand == f.split(",")[0].strip() for f in fams.splitlines()):
            return cand
    return "serif"


# ── sources ──────────────────────────────────────────────────────────
def load_gray(path, box=None, invert=False, levels=(0.0, 1.0), gamma=1.0):
    im = Image.open(path).convert("L")
    if box:
        W, H = im.size
        im = im.crop((int(box[0] * W), int(box[1] * H), int(box[2] * W), int(box[3] * H)))
    a = np.asarray(im, np.float32) / 255.0
    lo, hi = levels
    a = np.clip((a - lo) / max(hi - lo, 1e-3), 0, 1) ** gamma
    return 1 - a if invert else a


def resize(a, w, h):
    im = Image.fromarray((np.clip(a, 0, 1) * 255).astype(np.uint8))
    return np.asarray(im.resize((w, h), Image.LANCZOS), np.float32) / 255.0


def place(canvas, src, x, y):
    """paste src into canvas (max blend) at x, y with clipping."""
    H, W = canvas.shape
    h, w = src.shape
    x0, y0 = max(0, x), max(0, y)
    x1, y1 = min(W, x + w), min(H, y + h)
    if x1 <= x0 or y1 <= y0:
        return canvas
    canvas[y0:y1, x0:x1] = np.maximum(canvas[y0:y1, x0:x1], src[y0 - y:y1 - y, x0 - x:x1 - x])
    return canvas


def soft_edges(a, feather):
    """fade an image's borders to black so it sits in the plate."""
    h, w = a.shape
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    e = np.minimum.reduce([xx, yy, w - 1 - xx, h - 1 - yy]) / feather
    return a * np.clip(e, 0, 1) ** 1.5


def radial(h, w, cx, cy, r):
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    return np.sqrt((xx - cx) ** 2 + (yy - cy) ** 2) / r


# ── final print ──────────────────────────────────────────────────────
def paper(h, w, rng, base=INK, grain=3.0, vignette=0.35):
    """dark plate with grain, faint fibres and a vignette."""
    g = (rng.standard_normal((h, w)).astype(np.float32) * grain)
    fib = fractal(h, w, rng, 64, 3) - 0.5
    img = np.empty((h, w, 3), np.float32)
    img[:] = base
    img += (g + fib * 6)[..., None]
    v = radial(h, w, w / 2, h / 2, math.hypot(w, h) / 2)
    img *= (1 - vignette * np.clip(v, 0, 1) ** 2)[..., None]
    return img


def ink_on(img, mask, colour, strength=1.0):
    m = np.clip(mask, 0, 1)[..., None] * strength
    return img * (1 - m) + colour * m


def plate_mark(img, inset=26, colour=None, caption=None, credit=None, family=None, inset_top=64):
    """the plate's pressed border, caption and credit line.

    inset_top keeps the frame's top edge below the bar. The rules pass
    behind the engraving (figures break the border); the lettering never
    does: it sits on a small ink cartouche so it reads over any hatching.
    """
    h, w = img.shape[:2]
    rule = Vec(w, h)
    rule.cr.set_line_width(1.0)
    rule.cr.rectangle(inset + 0.5, inset_top + 0.5, w - 2 * inset - 1, h - inset - inset_top - 1); rule.cr.stroke()
    rule.cr.set_line_width(0.6)
    rule.cr.rectangle(inset + 5.5, inset_top + 5.5, w - 2 * inset - 11, h - inset - inset_top - 11); rule.cr.stroke()
    lum = img.mean(axis=2)
    occupied = blur(np.clip((lum - 40) / 40, 0, 1), 7)
    behind = 1 - np.clip(occupied * 4, 0, 1)
    img = ink_on(img, rule.mask() * behind, colour if colour is not None else STONE_RULE, 0.9)

    text = Vec(w, h)
    plates = Vec(w, h)
    y = h - inset - 20
    for s_, x, size, anchor, slant, spacing in ((caption, inset + 24, 15, "left", False, 2.2),
                                                 (credit, w - inset - 24, 12, "right", True, 0.0)):
        if not s_:
            continue
        cr = text.cr
        cr.select_font_face(family or SERIF_CANDIDATES[0],
                            cairo.FONT_SLANT_ITALIC if slant else cairo.FONT_SLANT_NORMAL, cairo.FONT_WEIGHT_NORMAL)
        cr.set_font_size(size)
        tw = sum(cr.text_extents(ch).x_advance for ch in s_) + spacing * (len(s_) - 1)
        x0 = x if anchor == "left" else x - tw
        pc = plates.cr
        pc.rectangle(x0 - 10, y - size - 4, tw + 20, size + 12)
        pc.fill()
        text.text(s_, x, y, size, family, anchor=anchor, spacing=spacing, slant=slant)
    img = ink_on(img, blur(plates.mask(), 2), INK, 0.82)
    return ink_on(img, text.mask(), CAPTION, 0.95)


STONE_RULE = np.array([96, 92, 86], np.float32)
CAPTION = np.array([150, 144, 132], np.float32)


def save(img, path):
    Image.fromarray(np.clip(img, 0, 255).astype(np.uint8)).save(path, optimize=True)
