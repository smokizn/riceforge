# Dependencies

[`manifests/packages.tsv`](../manifests/packages.tsv) is the single source of truth. Setup
installs from it, `riceforge doctor` checks against it, and `tests/check_static.py` fails if
any config runs a command that no manifest package provides.

## How the list was built

The list comes from what the configuration actually executes, not from what happened to be
installed. On 2026-10-17 the audit read:

- every `exec_cmd(...)` in the Hyprland Lua tree, plus hypridle and hyprlock commands;
- every `exec`, `exec-if`, `on-click*` and `on-scroll*` in the three Waybar configs, and the
  `menu-actions` of the power menu;
- the theme `session` hooks and `bin/session-lib.sh` (helpers they start and stop);
- riceforge-shell's imports and GObject typelibs (`Gtk 4.0`, `Gdk 4.0`, `Gtk4LayerShell 1.0`,
  `NM 1.0`, `PangoCairo 1.0`, `GdkPixbuf 2.0`), its `LD_PRELOAD` of `libgtk4-layer-shell.so`
  and its subprocesses (`awww`, `swaybg`, `pgrep`);
- every font family named in the CSS, kitty and hyprlock files;
- Walker's provider prefixes (each one needs an Elephant provider package);
- every `~/...` script path, checked to exist and to be deployed by the repo.

Each command maps to its owning package (`pacman -Qo`). AUR versus official status was checked
with `pacman -Si` and the AUR RPC.

## Tiers

| tier | meaning | examples |
|---|---|---|
| 1 | required for a working desktop | hyprland, hyprlock, hypridle, waybar, swaync, kitty, fish, pipewire, portals, hyprpolkitagent, fonts, walker/elephant (AUR) |
| 2 | needed by a Riceforge feature | NetworkManager/libnm and BlueZ (panels), gtk4-layer-shell, Elephant providers, tray applets for original/etch, hyprpicker, btop |
| 3 | optional aesthetics | otf-cormorant (display serif, falls back to Noto Serif), awww (crossfades, falls back to swaybg), fortune-mod |
| 4 | hardware/login specific | sddm (only when no display manager is enabled) |
| 5 | development | python-pillow, python-numpy (plate generators), lua (`luac` in tests) |

A missing tier-1 package makes `doctor` fail. Missing tier 2–5 packages produce warnings, and
the affected feature degrades. For example, without awww the plate archive switches
wallpapers instantly instead of crossfading.

## AUR

Never assumed. Setup uses `--aur-helper`, then `AUR_HELPER` from `machine.conf`, then the first of
paru, yay, pikaur, aura or trizen that is installed. If none exists it asks whether to build
`paru-bin` or `yay-bin` with `makepkg`, and defaults to skipping. AUR packages are
user-submitted; review the PKGBUILDs your helper shows you.

| package | why it's AUR |
|---|---|
| walker-bin, elephant, elephant-* | Walker/Elephant aren't in the official repos. `walker-bin` is x86_64-only; build `walker` from source elsewhere |
| hypremoji | emoji picker (SUPER+.) |
| wlogout | session menu (CTRL+ALT+Del, original theme bar) |
| zen-browser-bin | personal feature only |

## Not pinned, on purpose

No versions are pinned. Arch is rolling, and pinning one package while the rest of the system
moves leads to partial upgrades, which Arch doesn't support. The real compatibility
constraints are:

- **Hyprland ≥ 0.56**: the config is Lua (`hl.*` API, `hl.curve` springs). Older Hyprland can't read it.
- **Walker 2.x / Elephant 2.x**: the theme XML and provider names follow their 2.x layout.
- **GTK 4.10+** for riceforge-shell (`Gtk.CssProvider.load_from_string`).

`riceforge doctor` and `tests/clean-container.sh` show breakage early. When an upstream
change breaks something, fix the config. Don't pin.

## Problems the audit found and fixed

| finding | fix |
|---|---|
| `polkit-gnome` agent started from autostart but not installed: no GUI auth prompts | `hyprpolkitagent` (official), started as its user unit |
| SUPER+V ran `rofi` + `cliphist`, neither installed | `walker -m clipboard` (elephant-clipboard); the dead cliphist watchers were removed |
| Elephant providers for `calc`, `files`, `clipboard`, `runner`, `providerlist`, `websearch`, `todo`, `bookmarks`, `windows` not installed, so most Walker prefixes did nothing | added as feature `launcher-extras` |
| original/etch Bluetooth click ran a missing `rofi-bluetooth`; original Wi-Fi click a missing `rofi-wifi-menu.sh` | `blueman-manager` / `nm-connection-editor` |
| original theme's lock screen calls `fortune` (not installed) | `fortune-mod` (tier 3) |
| `nm-applet`, `blueman-applet` run by original/etch but not listed | `network-manager-applet`, `blueman` |
| bar gun toy used `mpv` (not installed) and a hard-coded `/home/<user>` sound path | sound optional; plays only if `mpv` and `~/.config/waybar/gunshot.mp3` exist |
| fan widgets read Acer-only sysfs paths and showed `0/0 RPM` elsewhere | `exec-if` gates them on `linuwu_sense` / `fan-toggle` |
| SUPER+SHIFT+S failed on a fresh system (no `~/Pictures/Screenshots`) | `mkdir -p` first |
| absolute `/home/<user>/` paths in the nacre bar CSS, the Walker layout, `riceforge` itself and keybinds | relative CSS urls (verified to load through the symlink), a rendered `layout.xml.in` template, `~/` paths |
| quickshell gestures and env from an older setup | removed (layer rules kept; harmless) |
| `discord` autostart (only `discord-ptb` installed), FluxCap from `~/.cargo/bin` | moved to the opt-in `personal` extra, each guarded by `command -v` |
| under uwsm, XDG autostart started `nm-applet`/`blueman-applet` at login alongside nacre's riceforge-shell (racing the session hook); found by `riceforge doctor` on the live desktop | per-user `Hidden=true` overrides in `~/.config/autostart/`, so theme sessions alone own the applets |
| `hyprland.lua` as a symlink made Lua `require` resolve against the repo, so `custom/` and the theme layer would not load | `package.path` is pinned to `~/.config/hypr` (found by the sandbox test) |

## Not needed

- **Spacefish.** Earlier prompts used it; NACRE now uses a native fish prompt
  (`themes/nacre/fish/theme.fish`), and nothing references Spacefish.
- **hyprpaper, swayosd, quickshell, dunst/mako, rofi, cliphist.** Referenced only by dead or
  commented lines.
- **udev rules or extra groups.** `brightnessctl` works through systemd-logind for the seat
  user, and the panels use the session bus plus NetworkManager/BlueZ polkit defaults.
