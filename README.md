# riceforge

Whole-desktop looks for this Hyprland setup, switchable and reversible.
Themes carry **looks only**. Keybinds, execs and window rules stay in `~/.config/hypr`.

## Commands

    ~/.config/riceforge/bin/riceforge list           # themes
    ~/.config/riceforge/bin/riceforge status         # active theme + link health
    ~/.config/riceforge/bin/riceforge verify etch    # validate without applying
    ~/.config/riceforge/bin/riceforge apply etch     # verify, switch, live-reload
    ~/.config/riceforge/bin/riceforge revert         # back to your pre-riceforge look
    ~/.config/riceforge/bin/riceforge preview-bar X  # a theme's waybar for 8s, beside yours
    ~/.config/riceforge/bin/riceforge detach         # remove riceforge, restore plain files

## How it is wired

`current -> themes/<name>`, and these files in `~/.config` are symlinks through it:

| link                          | theme file          |
|-------------------------------|---------------------|
| hypr/riceforge.lua            | hypr.lua            |
| hypr/hyprlock.conf            | hyprlock.conf       |
| waybar/config.jsonc           | waybar/config.jsonc |
| waybar/style.css              | waybar/style.css    |
| kitty/riceforge-theme.conf    | kitty.conf          |
| swaync/style.css              | swaync.css          |
| walker/themes/<name>          | themes/<name>/walker|

One-time edits made by `attach` (all undone by `detach`):

- `hypr/hyprland.lua`: a marked block that loads `riceforge.lua` last, before shell overrides
- `hypr/hyprlua/execs.lua`: swaybg reads `current/wallpaper.png`
- `kitty/kitty.conf`: `globinclude riceforge-*.conf`
- `walker/config.toml`: the `theme =` line

## Safety nets

- `backups/pre-riceforge-2026-10-17.tar.gz`: hypr, waybar, walker, elephant, kitty before anything changed.
  Restore: `tar xzf ~/.config/riceforge/backups/pre-riceforge-2026-10-17.tar.gz -C ~/.config`
- `backups/attach-*/`: the four edited files exactly as they were before attach.
- `themes/original/`: your previous look as a switchable theme.

## ETCH

An etcher's studio. Graphite plates, zinc greys, one mordant accent.

| token  | hex       | used for                                   |
|--------|-----------|--------------------------------------------|
| ink    | `#0a0a0b` | bar, launcher, terminal ground             |
| page   | `#111113` | cards, menus, notifications                |
| rule   | `#2a2a2e` | hairlines, inactive borders                |
| faded  | `#6b6b70` | secondary text                             |
| silver | `#b4b4b8` | body text                                  |
| paper  | `#ececea` | emphasis, hover                            |
| lichen | `#c2d94c` | **focus only**: active window, folio, selection, caret |
| rose   | `#d35d6e` | **critical only**: battery, urgent, failures |

Type: Iosevka (instruments), Noto Serif italic (captions, folios, input).
Motion: `bite` (expo-out arrivals), `lift` (quad-in exits, always faster), `pull` (ease-in-out workspaces).
No blur, no glow, no gradients.

Wallpapers: `themes/etch/tools/make_plates.py OUT_DIR` regenerates the plates from
`~/Pictures/Wallpapers`. Point `themes/etch/wallpaper.png` at `plate-i/ii/iii.png`.
