#!/usr/bin/env python3
"""Waybar custom module: the moon's phase as a CSS class (moon-0 .. moon-7)."""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import astro  # noqa: E402

m = astro.moon_at()
print(json.dumps({
    "text": "\u2009",          # waybar hides modules with empty text
    "class": f"moon-{m.index}",
    "tooltip": f"{m.name} · {m.illumination * 100:.0f}% lit\n"
               f"full {m.next_full.astimezone():%a %d %b %H:%M} · new {m.next_new.astimezone():%a %d %b %H:%M}",
}))
