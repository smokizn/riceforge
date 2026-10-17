# Credits and licences

## Code

| what | licence |
|---|---|
| Riceforge's own code and configs (`bin/`, `install/`, `shell/`, `config/`, `themes/*` except below, `tests/`) | MIT, see [LICENSE](LICENSE) |
| `themes/*/walker/` (layout and item XML, derived from Walker's default theme) | GPL-3.0-or-later, from [Walker](https://github.com/abenz1267/walker). See each directory's `NOTICE` and `LICENSE` |
| `config/waybar/scripts/mediaplayer.py` | MIT, from [Waybar](https://github.com/Alexays/Waybar) `resources/custom_modules` |
| `config/hypr/hyprlua/` | started from the Lua port of [end-4/dots-hyprland](https://github.com/end-4/dots-hyprland) (GPL-3.0) and heavily edited. Treat this directory as GPL-3.0 as well |

## Plates (NACRE wallpapers)

Made at 1920×1080 by `themes/nacre/tools/plates/compose.py` (engraving code: `engrave.py`).
No image-generation model was used. The source records, with Wikimedia Commons metadata,
are in `themes/nacre/tools/plates/sources/sources.json`.

| plate | source | licence |
|---|---|---|
| I · Machina Mundi | Flammarion engraving, anonymous, 1888 ([Commons](https://commons.wikimedia.org/wiki/File:Flammarion.jpg)) + procedural orbits | public domain |
| II · Anatomia Montium | Vesalius, *Tertia musculorum tabula*, 1543, National Library of Medicine ([Commons](https://commons.wikimedia.org/wiki/File:Tertia_musculorum_tabula_(37053621276).jpg)) + procedural mountains | public domain ("no known restrictions") |
| III · Ouroboros Eclipsis, IV · Montes Lunae, V · Oculus Mundi | procedural (Riceforge code) | MIT, like the code |
| VI · The Empyrean | Gustave Doré, *Paradiso* Canto 31 ([Commons](https://commons.wikimedia.org/wiki/File:Paradiso_Canto_31_(no_caption).jpg)) | public domain |
| VII · Macrocosmus | Robert Fludd, *Utriusque Cosmi*, 1617–21 ([Commons](https://commons.wikimedia.org/wiki/File:UtriusqueCosmiMacrocosm.png)) | public domain |
| VIII · Selenographia | James Nasmyth, *Normal lunar crater*, 1874 ([Commons](https://commons.wikimedia.org/wiki/File:Normal_lunar_crater_-_J._Nasmyth._LCCN2001700463.jpg)) | public domain |

**Not distributed:** NACRE's IX–XI (*Fenestra*, *Draco*, *Trigonum*), ETCH's three plates and
the original theme's wallpaper are re-prints of wallpapers downloaded from wallhaven, whose
licence can't be verified. They're ignored by git and stay on the machine that made them.
The gallery hides them where they're absent, and those themes fall back to a public-domain
plate (`DEFAULT_WALLPAPER` in each `theme.env`).

## Icons and lock art

The 65 hairline SVG icons (`themes/nacre/icons`, built by `tools/build_icons.py`) and the
lock-screen ring and moon (`shell/lockart.py`) are original Riceforge work (MIT).

## Fonts

No fonts are bundled. They're installed from Arch packages under their own licences:
Cormorant (`otf-cormorant`, OFL-1.1), Noto (`noto-fonts`, OFL-1.1), Iosevka Nerd Font
(`ttf-iosevka-nerd`, OFL-1.1 + MIT), Symbols Nerd Font (`ttf-nerd-fonts-symbols`, MIT),
Adwaita Sans (`adwaita-fonts`, OFL-1.1).

## Software

Riceforge configures, but doesn't include, Hyprland, hyprlock, hypridle, Waybar, SwayNC,
Walker, Elephant, Kitty, fish, NetworkManager, BlueZ and the other packages in
[`manifests/packages.tsv`](manifests/packages.tsv). Each is under its own licence.
