#!/usr/bin/env python3
"""NACRE wallpaper generator.

Glass is only visible when there is colour behind it, so each wallpaper
sets one of the engravings in ~/Pictures/Wallpapers as a lit object in a
smoky field of soft nacre light (lavender, ice, pearl, a little rose).
Blur from Hyprland then picks those colours up through every glass surface.
Film grain is added so the gradients never band. Originals are untouched.

usage: make_wallpapers.py OUT_DIR [WIDTH HEIGHT]
"""
import random
import sys
from pathlib import Path
from PIL import Image, ImageChops, ImageDraw, ImageFilter, ImageOps

WALLS = Path.home() / "Pictures/Wallpapers"

TOP = (17, 17, 26)
BOTTOM = (6, 6, 11)
PEARL = (236, 234, 248)

# (cx, cy, radius) as fractions of width, then colour and strength.
# few, saturated pools on deep smoke: glass needs contrast, not haze.
FIELDS = {
    "fenestra": [
        ((0.16, 0.22, 0.24), (118, 92, 236), 0.78),    # lavender
        ((0.86, 0.80, 0.26), (52, 160, 226), 0.70),    # ice
        ((0.70, 0.06, 0.15), (232, 132, 190), 0.50),   # pearl rose
        ((0.50, 0.50, 0.12), (150, 136, 250), 0.40),   # light behind the window
    ],
    "draco": [
        ((0.80, 0.66, 0.24), (70, 140, 236), 0.72),
        ((0.14, 0.20, 0.22), (128, 96, 230), 0.70),
        ((0.40, 0.98, 0.16), (226, 134, 190), 0.45),
    ],
    "trigonum": [
        ((0.50, 0.28, 0.18), (132, 104, 240), 0.62),
        ((0.12, 0.86, 0.24), (56, 156, 220), 0.66),
        ((0.90, 0.84, 0.18), (228, 136, 192), 0.45),
    ],
}
SOURCES = {
    "fenestra": "wallhaven-zpvqyj.png",
    "draco": "wallhaven-w53de7.png",
    "trigonum": "wallhaven-9ok23k.jpg",
}


def gradient(w, h):
    g = Image.new("RGB", (1, h))
    for y in range(h):
        t = y / (h - 1)
        g.putpixel((0, y), tuple(round(a + (b - a) * t) for a, b in zip(TOP, BOTTOM)))
    return g.resize((w, h))


def light_field(w, h, spec):
    base = gradient(w, h)
    for (fx, fy, fr), colour, strength in spec:
        layer = Image.new("L", (w, h), 0)
        r = fr * w
        ImageDraw.Draw(layer).ellipse(
            (fx * w - r, fy * h - r, fx * w + r, fy * h + r), fill=round(255 * strength))
        layer = layer.filter(ImageFilter.GaussianBlur(r * 0.62))
        base = Image.composite(Image.new("RGB", (w, h), colour), base, layer)
    return base


def engraving_mask(src, w, h):
    img = ImageOps.fit(Image.open(src).convert("L"), (w, h), Image.LANCZOS)
    # lift the linework, crush the near-black paper to nothing
    return img.point(lambda v: 0 if v < 28 else min(255, int((v - 28) * 1.25)))


def grain(img, amount=5, seed=7):
    rnd = random.Random(seed)
    w, h = img.size
    small = Image.new("L", (w // 2, h // 2))
    small.putdata([128 + rnd.randint(-amount, amount) for _ in range(small.width * small.height)])
    noise = small.resize((w, h), Image.NEAREST).convert("RGB")
    return Image.blend(img, ImageChops.overlay(img, noise), 0.5)


def build(name, out, w, h):
    src = WALLS / SOURCES[name]
    if not src.exists():
        return
    field = light_field(w, h, FIELDS[name])
    mask = engraving_mask(src, w, h)

    # a soft bloom of light around the linework, as if lit from behind
    bloom = mask.filter(ImageFilter.GaussianBlur(40)).point(lambda v: min(255, v * 2))
    field = Image.composite(Image.new("RGB", (w, h), (160, 146, 246)), field,
                            bloom.point(lambda v: int(v * 0.22)))
    # the engraving itself in pearl
    field = Image.composite(Image.new("RGB", (w, h), PEARL), field, mask.point(lambda v: int(v * 0.92)))

    grain(field).save(out / f"{name}.png", optimize=True)
    print(out / f"{name}.png")


def main():
    out = Path(sys.argv[1])
    w, h = (int(sys.argv[2]), int(sys.argv[3])) if len(sys.argv) > 3 else (1920, 1080)
    out.mkdir(parents=True, exist_ok=True)
    for name in SOURCES:
        build(name, out, w, h)


if __name__ == "__main__":
    main()
