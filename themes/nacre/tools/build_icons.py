#!/usr/bin/env python3
"""NACRE · Visionary icon set.

One hand-authored hairline glyph per concept, drawn on a 24-unit grid with
1.25-unit round-capped strokes and small engraver's details (double rules,
tick marks, hatched fills). GTK3 cannot recolour SVG background images, so
each glyph is written once per palette colour:

    icons/<colour>/<name>.svg

usage: build_icons.py ICONS_DIR
"""
import math
import sys
from pathlib import Path

COLOURS = {
    "bone":    "#e6dfcf",
    "stone":   "#6e6a64",
    "silver":  "#b9bcc2",
    "brass":   "#b39a5e",
    "crimson": "#a8464f",
    "ink":     "#0b0a0a",
}
W = 1.25  # stroke width


def svg(body, c):
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" width="24" height="24" '
            f'fill="none" stroke="{c}" stroke-width="{W}" stroke-linecap="round" stroke-linejoin="round">'
            f'{body}</svg>\n')


def ticks(cx, cy, r1, r2, n, start=0.0, every=None):
    out = []
    for i in range(n):
        a = start + 2 * math.pi * i / n
        rr = r2 if (every is None or i % every == 0) else (r1 + (r2 - r1) * 0.5)
        out.append(f'<line x1="{cx + r1 * math.cos(a):.2f}" y1="{cy + r1 * math.sin(a):.2f}" '
                   f'x2="{cx + rr * math.cos(a):.2f}" y2="{cy + rr * math.sin(a):.2f}"/>')
    return "".join(out)


def hatch_clip(cid, shape, spacing=1.6, angle=-45, c=None, outer=None):
    """diagonal engraving hatch clipped to a shape (optionally also to `outer`).

    The clip sits on an untransformed outer group and only the inner group is
    rotated: clip-path resolves in the user space of the element carrying it.
    """
    lines = "".join(f'<line x1="{k * spacing}" y1="-12" x2="{k * spacing}" y2="36"/>' for k in range(-12, 28))
    inner = (f'<g clip-path="url(#{cid})"><g stroke-width="0.6" opacity="0.85" '
             f'transform="rotate({angle} 12 12)">{lines}</g></g>')
    defs = f'<clipPath id="{cid}">{shape}</clipPath>'
    if outer is not None:
        defs += f'<clipPath id="{cid}o">{outer}</clipPath>'
        inner = f'<g clip-path="url(#{cid}o)">{inner}</g>'
    return f"<defs>{defs}</defs>{inner}"


ICONS = {}

# ── celestial ────────────────────────────────────────────────────────
ICONS["sun"] = lambda c: (
    '<circle cx="12" cy="12" r="4.2"/><circle cx="12" cy="12" r="2.2" stroke-width="0.7"/>'
    + ticks(12, 12, 6.2, 9.6, 16, every=2))

def moon_phase(k):
    """k in 0..7: new, waxing crescent, first quarter, waxing gibbous, full, waning ..."""
    def f(c):
        r = 7.5
        base = f'<circle cx="12" cy="12" r="{r}"/>'
        if k == 0:
            return base + f'<circle cx="12" cy="12" r="{r - 2}" stroke-width="0.6" stroke-dasharray="0.6 1.4"/>'
        if k == 4:
            return (base + f'<circle cx="12" cy="12" r="{r}" fill="{c}" fill-opacity="0.18"/>'
                    '<circle cx="9.5" cy="10" r="1.3" stroke-width="0.6"/>'
                    '<circle cx="14.2" cy="14.4" r="0.9" stroke-width="0.6"/>')
        # lit limb: an ellipse terminator; waxing lights the right side
        frac = {1: 0.25, 2: 0.5, 3: 0.75, 5: 0.75, 6: 0.5, 7: 0.25}[k]
        rx = abs(math.cos(math.pi * frac)) * r
        right = k < 4
        sweep_outer = 1 if right else 0
        gibbous = frac > 0.5
        sweep_inner = (0 if right else 1) if not gibbous else (1 if right else 0)
        d = (f'M12 {12 - r} A{r} {r} 0 0 {sweep_outer} 12 {12 + r} '
             f'A{rx:.2f} {r} 0 0 {sweep_inner} 12 {12 - r} Z')
        lit = f'<path d="{d}" fill="{c}" fill-opacity="0.22"/>'
        return base + lit + hatch_clip(f"m{k}", f'<path d="{d}"/>', 1.5, -30)
    return f

for i in range(8):
    ICONS[f"moon-{i}"] = moon_phase(i)

ICONS["star"] = lambda c: (
    '<path d="M12 3.2 L13.6 10.4 L20.8 12 L13.6 13.6 L12 20.8 L10.4 13.6 L3.2 12 L10.4 10.4 Z"/>'
    '<path d="M12 7.5 L12.7 11.3 L16.5 12 L12.7 12.7 L12 16.5 L11.3 12.7 L7.5 12 L11.3 11.3 Z" stroke-width="0.6"/>')
ICONS["star-filled"] = lambda c: (
    f'<path d="M12 3.2 L13.6 10.4 L20.8 12 L13.6 13.6 L12 20.8 L10.4 13.6 L3.2 12 L10.4 10.4 Z" fill="{c}"/>')
ICONS["sigil"] = lambda c: (  # the launcher: sun inside a crescent, inside an orbit
    '<circle cx="12" cy="12" r="9.2"/>' + ticks(12, 12, 9.2, 10.6, 12)
    + '<path d="M15.6 6.2 A6.4 6.4 0 1 0 15.6 17.8 A5 5 0 1 1 15.6 6.2 Z"/>'
    + '<circle cx="15.2" cy="12" r="1.6"/>')
ICONS["orbit"] = lambda c: (
    '<ellipse cx="12" cy="12" rx="9" ry="4" transform="rotate(-20 12 12)"/>'
    '<circle cx="12" cy="12" r="2.6"/><circle cx="19.8" cy="9.1" r="1.1" fill="' + c + '"/>')

# ── connectivity ─────────────────────────────────────────────────────
def wifi(level, off=False, lock=False):
    def f(c):
        arcs = []
        for i, r in enumerate((4.2, 8.0, 11.8)):
            on = (i < level) and not off
            dash = '' if on else ' stroke-dasharray="0.4 1.8" stroke-width="0.9"'
            arcs.append(f'<path d="M{12 - r * 0.72:.2f} {19 - r * 0.69:.2f} '
                        f'A{r} {r} 0 0 1 {12 + r * 0.72:.2f} {19 - r * 0.69:.2f}"{dash}/>')
        dot = f'<circle cx="12" cy="19" r="1.2" fill="{c}"/>' if not off else '<circle cx="12" cy="19" r="1.2"/>'
        extra = '<line x1="4" y1="4" x2="20" y2="20"/>' if off else ''
        if lock:
            extra += ('<rect x="16.6" y="15.6" width="5.4" height="4.6" rx="0.8"/>'
                      '<path d="M17.8 15.6 V14.4 A1.5 1.5 0 0 1 20.8 14.4 V15.6"/>')
        return "".join(arcs) + dot + extra
    return f

for lv in range(4):
    ICONS[f"wifi-{lv}"] = wifi(lv)
    ICONS[f"wifi-{lv}-lock"] = wifi(lv, lock=True)
ICONS["wifi-off"] = wifi(0, off=True)

ICONS["bluetooth"] = lambda c: '<path d="M7 7.5 L17 16.5 L12 21 V3 L17 7.5 L7 16.5"/>'
ICONS["bluetooth-off"] = lambda c: (
    '<path d="M7 7.5 L17 16.5 L12 21 V3 L17 7.5 L7 16.5" stroke-dasharray="0.5 1.6"/>'
    '<line x1="4" y1="4" x2="20" y2="20"/>')
ICONS["bluetooth-connected"] = lambda c: (
    '<path d="M7 7.5 L17 16.5 L12 21 V3 L17 7.5 L7 16.5"/>'
    f'<circle cx="4" cy="12" r="0.9" fill="{c}"/><circle cx="20" cy="12" r="0.9" fill="{c}"/>')

# ── senses ───────────────────────────────────────────────────────────
def speaker(level, muted=False):
    def f(c):
        body = '<path d="M4 9.5 H7.5 L12 5.5 V18.5 L7.5 14.5 H4 Z"/>'
        if muted:
            return body + '<line x1="15.5" y1="9.5" x2="20.5" y2="14.5"/><line x1="20.5" y1="9.5" x2="15.5" y2="14.5"/>'
        waves = []
        for i, r in enumerate((3.2, 6.0, 8.8)):
            if i < level:
                waves.append(f'<path d="M{12 + r * 0.55:.2f} {12 - r * 0.83:.2f} '
                             f'A{r} {r} 0 0 1 {12 + r * 0.55:.2f} {12 + r * 0.83:.2f}"/>')
        return body + "".join(waves)
    return f

for lv in range(4):
    ICONS[f"volume-{lv}"] = speaker(lv)
ICONS["volume-muted"] = speaker(0, muted=True)
ICONS["mic"] = lambda c: (
    '<rect x="9" y="3.5" width="6" height="10.5" rx="3"/>'
    '<path d="M6 11.5 A6 6 0 0 0 18 11.5"/><line x1="12" y1="17.5" x2="12" y2="20.5"/>'
    '<line x1="9" y1="20.5" x2="15" y2="20.5"/><line x1="10.5" y1="7" x2="13.5" y2="7" stroke-width="0.6"/>'
    '<line x1="10.5" y1="9" x2="13.5" y2="9" stroke-width="0.6"/>')
ICONS["mic-off"] = lambda c: ICONS["mic"](c) + '<line x1="4" y1="4" x2="20" y2="20"/>'
ICONS["brightness"] = lambda c: (
    '<circle cx="12" cy="12" r="3.6"/>' + ticks(12, 12, 6, 8.4, 8)
    + '<path d="M12 8.4 A3.6 3.6 0 0 1 12 15.6 Z" fill="' + c + '" fill-opacity="0.5"/>')

# ── battery as an alchemist's vial ───────────────────────────────────
def vial(level, charging=False):
    def f(c):
        out = ('<path d="M10 2.8 H14 M10.6 2.8 V7 C7 8.4 5.6 11 5.6 14.2 A6.4 6.4 0 0 0 18.4 14.2 '
               'C18.4 11 17 8.4 13.4 7 V2.8"/>')
        # liquid level: 0..4
        top = 20.6 - level * 3.0
        if level > 0:
            vial_shape = ('<path d="M10.6 2.8 V7 C7 8.4 5.6 11 5.6 14.2 A6.4 6.4 0 0 0 18.4 14.2 '
                          'C18.4 11 17 8.4 13.4 7 V2.8 Z"/>')
            out += hatch_clip(f"v{level}{int(charging)}",
                              f'<rect x="4" y="{top:.2f}" width="16" height="22"/>', 1.3, 0,
                              outer=vial_shape)
            out += f'<line x1="6.6" y1="{top:.2f}" x2="17.4" y2="{top:.2f}" stroke-width="0.7"/>'
        if charging:
            out += f'<path d="M12.8 9.6 L10.2 14 H13.2 L11.2 18.4" stroke-width="1.1"/>'
        return out
    return f

for lv in range(5):
    ICONS[f"battery-{lv}"] = vial(lv)
ICONS["battery-charging"] = vial(2, charging=True)

# ── instruments ──────────────────────────────────────────────────────
ICONS["cpu"] = lambda c: (  # a sigil: square seal with radiating pins
    '<rect x="6.5" y="6.5" width="11" height="11" rx="1.2"/>'
    '<rect x="9.4" y="9.4" width="5.2" height="5.2" transform="rotate(45 12 12)" stroke-width="0.8"/>'
    + "".join(f'<line x1="{x}" y1="3.5" x2="{x}" y2="6.5"/><line x1="{x}" y1="17.5" x2="{x}" y2="20.5"/>'
              f'<line x1="3.5" y1="{x}" x2="6.5" y2="{x}"/><line x1="17.5" y1="{x}" x2="20.5" y2="{x}"/>'
              for x in (9.5, 14.5)))
ICONS["memory"] = lambda c: (
    '<rect x="3.5" y="7" width="17" height="10" rx="1"/>'
    + "".join(f'<rect x="{x}" y="9.2" width="2.4" height="5.6" stroke-width="0.8"/>' for x in (5.8, 9.4, 13, 16.6))
    + "".join(f'<line x1="{x}" y1="17" x2="{x}" y2="19"/>' for x in (6, 9, 12, 15, 18)))
ICONS["fan"] = lambda c: (
    '<circle cx="12" cy="12" r="1.6"/>'
    + "".join(f'<path d="M12 10.4 C12 6 15.5 4.6 16.8 6.6 C17.6 8 15.6 10 13.4 11" transform="rotate({a} 12 12)"/>'
              for a in (0, 120, 240)))
ICONS["power"] = lambda c: '<path d="M7.6 6.6 A7.2 7.2 0 1 0 16.4 6.6"/><line x1="12" y1="3.2" x2="12" y2="11.6"/>'
ICONS["lock"] = lambda c: (
    '<rect x="5.5" y="10.5" width="13" height="10" rx="1.6"/>'
    '<path d="M8.4 10.5 V7.6 A3.6 3.6 0 0 1 15.6 7.6 V10.5"/><circle cx="12" cy="15" r="1.2"/>'
    '<line x1="12" y1="16.2" x2="12" y2="18"/>')
ICONS["search"] = lambda c: (
    '<circle cx="10.5" cy="10.5" r="6"/><circle cx="10.5" cy="10.5" r="4.2" stroke-width="0.6"/>'
    '<line x1="15" y1="15" x2="20.5" y2="20.5"/>')
ICONS["refresh"] = lambda c: (
    '<path d="M19 12 A7 7 0 1 1 16.95 7.05"/><path d="M17.2 3.6 V7.4 H13.4"/>')
ICONS["close"] = lambda c: '<line x1="6" y1="6" x2="18" y2="18"/><line x1="18" y1="6" x2="6" y2="18"/>'
ICONS["check"] = lambda c: '<path d="M5 12.5 L10 17.5 L19 6.5"/>'
ICONS["plus"] = lambda c: '<line x1="12" y1="5" x2="12" y2="19"/><line x1="5" y1="12" x2="19" y2="12"/>'
ICONS["forget"] = lambda c: (
    '<path d="M5 7 H19 M9.5 7 V4.8 H14.5 V7 M7 7 L8 20 H16 L17 7"/>'
    '<line x1="10.4" y1="10" x2="10.6" y2="17"/><line x1="13.6" y1="10" x2="13.4" y2="17"/>')
ICONS["eye"] = lambda c: (  # the watcher: almond eye, engraved iris
    '<path d="M2.8 12 C6 6.4 18 6.4 21.2 12 C18 17.6 6 17.6 2.8 12 Z"/>'
    '<circle cx="12" cy="12" r="3.4"/>' + ticks(12, 12, 1.4, 3.2, 12)
    + f'<circle cx="12" cy="12" r="1.2" fill="{c}"/>')
ICONS["eye-off"] = lambda c: ICONS["eye"](c) + '<line x1="4" y1="4" x2="20" y2="20"/>'
ICONS["music"] = lambda c: (
    '<path d="M9 17.5 V5.5 L19 3.5 V15.5"/><ellipse cx="7" cy="17.5" rx="2.2" ry="1.7"/>'
    '<ellipse cx="17" cy="15.5" rx="2.2" ry="1.7"/><line x1="9" y1="8.8" x2="19" y2="6.8" stroke-width="0.7"/>')
ICONS["frame"] = lambda c: (  # wallpaper / plates
    '<rect x="3" y="5" width="18" height="14" rx="1"/><rect x="5" y="7" width="14" height="10" stroke-width="0.6"/>'
    '<path d="M6.5 15.5 L10 11.5 L12.6 14 L14.6 12.4 L17.5 15.5"/><circle cx="15.8" cy="9.6" r="1"/>')
ICONS["link"] = lambda c: (
    '<path d="M10 14 L14 10"/><path d="M8.4 12.2 L6.6 14 A3 3 0 0 0 10.8 18.2 L12.6 16.4"/>'
    '<path d="M15.6 11.8 L17.4 10 A3 3 0 0 0 13.2 5.8 L11.4 7.6"/>')
ICONS["ethernet"] = lambda c: (
    '<rect x="5" y="6" width="14" height="10" rx="1"/><path d="M9 16 V19 H15 V16"/>'
    + "".join(f'<line x1="{x}" y1="9" x2="{x}" y2="12" stroke-width="0.8"/>' for x in (8, 10, 12, 14, 16)))

# ── device kinds (bluetooth) ─────────────────────────────────────────
ICONS["dev-headset"] = lambda c: (
    '<path d="M4.5 15 V12 A7.5 7.5 0 0 1 19.5 12 V15"/>'
    '<rect x="3" y="13.5" width="4" height="6" rx="1.4"/><rect x="17" y="13.5" width="4" height="6" rx="1.4"/>')
ICONS["dev-earbuds"] = lambda c: (
    '<path d="M7 5.5 A3.2 3.2 0 0 1 7 11.9 V18.5"/><circle cx="6.4" cy="8.7" r="1"/>'
    '<path d="M17 5.5 A3.2 3.2 0 0 0 17 11.9 V18.5"/><circle cx="17.6" cy="8.7" r="1"/>')
ICONS["dev-speaker"] = lambda c: (
    '<rect x="6" y="3" width="12" height="18" rx="2"/><circle cx="12" cy="14.5" r="3.4"/>'
    '<circle cx="12" cy="14.5" r="1.2"/><circle cx="12" cy="7.2" r="1.3"/>')
ICONS["dev-mouse"] = lambda c: (
    '<rect x="6.5" y="3" width="11" height="18" rx="5.5"/><line x1="12" y1="3" x2="12" y2="9.5"/>'
    '<line x1="6.5" y1="9.5" x2="17.5" y2="9.5"/>')
ICONS["dev-keyboard"] = lambda c: (
    '<rect x="2.5" y="6.5" width="19" height="11" rx="1.4"/>'
    + "".join(f'<line x1="{x}" y1="10" x2="{x + 0.01}" y2="10"/>' for x in (6, 9, 12, 15, 18))
    + "".join(f'<line x1="{x}" y1="12.6" x2="{x + 0.01}" y2="12.6"/>' for x in (7.5, 10.5, 13.5, 16.5))
    + '<line x1="8" y1="15" x2="16" y2="15"/>')
ICONS["dev-gamepad"] = lambda c: (
    '<path d="M7 8 H17 C19.6 8 21 11 21 14.5 C21 17 19.4 18 18 17 L15.6 14.8 H8.4 L6 17 C4.6 18 3 17 3 14.5 C3 11 4.4 8 7 8 Z"/>'
    '<line x1="6.5" y1="12" x2="9.5" y2="12"/><line x1="8" y1="10.5" x2="8" y2="13.5"/>'
    f'<circle cx="16" cy="11" r="0.8" fill="{c}"/><circle cx="17.6" cy="12.8" r="0.8" fill="{c}"/>')
ICONS["dev-phone"] = lambda c: (
    '<rect x="7" y="2.8" width="10" height="18.4" rx="1.8"/><line x1="10.5" y1="18.4" x2="13.5" y2="18.4"/>')
ICONS["dev-computer"] = lambda c: (
    '<rect x="3.5" y="5" width="17" height="11" rx="1"/><path d="M2 19 H22 M8 16 L7 19 M16 16 L17 19"/>')
ICONS["dev-generic"] = lambda c: (
    '<circle cx="12" cy="12" r="7.5"/>' + ticks(12, 12, 7.5, 9.6, 8)
    + '<path d="M9.5 9.5 L14.5 12 L9.5 14.5"/>')


def main():
    out = Path(sys.argv[1])
    for cname, hexv in COLOURS.items():
        d = out / cname
        d.mkdir(parents=True, exist_ok=True)
        for name, fn in ICONS.items():
            (d / f"{name}.svg").write_text(svg(fn(hexv), hexv))
    print(f"{len(ICONS)} icons x {len(COLOURS)} colours -> {out}")


if __name__ == "__main__":
    main()
