# Riceforge

A complete, reproducible Hyprland desktop for Arch Linux, with switchable whole-desktop themes.
The default theme, **NACRE · Visionary**, is a monochrome occult-astronomical engraving look:
antique celestial plates under ink glass, parchment type, lunar silver, tarnished brass.
Two more themes ship with it: **ETCH** (graphite plates, zinc greys) and **original**
(the author's desktop before Riceforge).

It's more than dotfiles. `./setup` installs the packages, enables the services the panels
need, deploys the configs as symlinks into this repository, writes a machine-local layer for
hardware differences, and checks the result. Everything it replaces is backed up, and
`riceforge uninstall` reverses it.

```bash
git clone https://github.com/smokizn/riceforge.git ~/riceforge
cd ~/riceforge
./setup
```

> Screenshots: none are committed yet. Add your own with
> `grim docs/screenshots/desktop.png` and link them here.

## What you get

| Area | NACRE · Visionary |
|---|---|
| Compositor | Hyprland 0.56+ with a Lua config: spring-physics animations (windows unveil with 8 % overshoot, workspaces glide, scratchpads drop), engraved silver-brass focus line, blur on glass surfaces |
| Bar | Waybar: sigil orb (opens Walker), constellation workspaces, engraved clock plaque with the real moon phase, CPU/RAM drawer, NetworkManager + BlueZ connection slab, volume/mic/brightness, battery vial |
| Launcher | Walker + Elephant: manuscript header, prefixes for files `/`, calc `=`, clipboard `:`, symbols `.`, web `@`, todo `!`, bookmarks `%`, windows `$`, run `>` |
| riceforge-shell | One resident GTK4 layer-shell process: **real Wi-Fi panel** (libnm: scan, connect PSK/SAE/WEP/open/OWE, wrong-password retry, hidden networks, forget), **real Bluetooth panel** (BlueZ D-Bus: pair, trust, connect, battery, and a default pairing agent), **plate archive** (wallpaper gallery with live preview and crossfades), **desk** (astrolabe with sunrise/sunset and moon phase, now-playing, battery, CPU/RAM) |
| Notifications | SwayNC, themed |
| Lock and idle | hyprlock (astrolabe ring, today's moon); hypridle locks after 5 min and turns screens off after 10 min |
| Terminal | Kitty + fish with a native prompt that shows the moon's phase in the greeting |
| Wallpapers | Eight distributable engraved plates in NACRE (public-domain sources plus procedural engraving), see [CREDITS.md](CREDITS.md) |

Keys worth knowing: `SUPER` launcher · `SUPER+T` terminal · `SUPER+V` clipboard history ·
`SUPER+L` lock · `SUPER+ALT+W` plate archive · `SUPER+ALT+N` Wi-Fi · `SUPER+ALT+B` Bluetooth ·
`SUPER+ALT+M` lunar ephemeris · `SUPER+SHIFT+S` region screenshot · `SUPER+S` Spotify scratchpad.
The full list is in `config/hypr/hyprlua/keybinds.lua`.

## Before you start

`./setup` does **not** install Arch Linux, partition disks, or touch the bootloader. You need:

1. Arch Linux installed to disk and booted (the [installation guide](https://wiki.archlinux.org/title/Installation_guide),
   or `archinstall` with the *minimal* profile). An Arch derivative may work; it is not tested.
2. A normal user with `sudo` rights (`wheel` group), and that user logged in.
3. A working network connection. If you set up networking with `iwd` or `systemd-networkd`,
   Riceforge leaves it alone and tells you; the Wi-Fi panel needs NetworkManager.
4. A GPU driver: Mesa for AMD/Intel is pulled in automatically. For NVIDIA install
   `nvidia-open` (or `nvidia`) yourself first. Riceforge never installs or changes GPU drivers.
5. `git`, to clone: `sudo pacman -S --needed git`.
6. Optional: an AUR helper (`paru` or `yay`). Without one, setup offers to build one or skips the
   AUR packages. AUR packages are Walker, Elephant and its providers, `hypremoji` and `wlogout`.

x86_64 only for the full stack. On other architectures the AUR `-bin` packages are skipped.

## Install

```bash
git clone https://github.com/smokizn/riceforge.git ~/riceforge   # any location works
cd ~/riceforge
./setup --dry-run                         # optional: see the plan, change nothing
./setup
```

Setup walks through:

1. **Preflight.** Checks the distribution, architecture, sudo, disk space and network,
   detects GPUs, battery, Bluetooth, the display manager and other network stacks, and
   looks for an existing install. It refuses to run as root or on the live ISO.
2. **Choices.** Hardware profile (detected), features, keyboard layout and theme. Defaults are
   fine, and `--yes` accepts them all.
3. **Plan.** Lists the missing packages, the services it would enable and every existing
   file it will back up. Nothing changes until you confirm.
4. **Packages.** Official packages go through `pacman -Syu --needed` (Arch doesn't support
   partial upgrades, so your system is updated too). AUR packages go through your helper.
   Packages you already have are skipped.
5. **System.** Enables `NetworkManager` and `bluetooth` only if they're off and nothing
   conflicts. Optionally enables SDDM if no display manager exists. Nothing else system-wide.
6. **User config.** Links the repo to `~/.config/riceforge` (when cloned elsewhere), symlinks
   every file in [`manifests/deploy.tsv`](manifests/deploy.tsv), seeds `~/.config/hypr/custom/`,
   and writes `~/.config/riceforge-local/`.
7. **Theme and check.** Applies NACRE and runs `riceforge doctor`.

Then reboot, or log out, and pick **Hyprland (uwsm-managed)** at the login screen. Without
a display manager, log in on a console and run `uwsm start hyprland.desktop`.

Options: `--profile desktop|laptop|acer-nitro`, `--features +personal,-aesthetic`,
`--theme etch`, `--kb-layout de`, `--aur-helper paru|yay|none`, `--no-packages`,
`--no-system`, `--yes`, `--dry-run`. See `./setup --help`.

### Features

| feature | default | what it adds |
|---|---|---|
| core | always | Hyprland, hyprlock/idle, portals, polkit agent, Waybar, SwayNC, Kitty, fish, PipeWire, screenshots, fonts |
| launcher | on | Walker + Elephant (AUR) |
| shell | on | riceforge-shell dependencies: NetworkManager, BlueZ, UPower, gtk4-layer-shell, PyGObject/cairo |
| launcher-extras | on | Elephant providers: files, calc, clipboard, symbols, web search, todo, bookmarks, windows (AUR) |
| apps | on | hyprpicker, btop, Dolphin, hypremoji, wlogout, mpv |
| aesthetic | on | Cormorant display serif, awww wallpaper crossfades |
| personal | off | Discord, EasyEffects, Zen Browser autostart, the Discord workspace and FluxCap keys |
| display-manager | off | SDDM, offered only when none is enabled |
| dev | off | Pillow/NumPy for the plate generators, `luac` for tests |

Every package, its purpose, source, tier and alternatives: [`manifests/packages.tsv`](manifests/packages.tsv),
explained in [docs/DEPENDENCIES.md](docs/DEPENDENCIES.md).

## Day to day

```bash
riceforge list | status          # themes; link health
riceforge apply nacre|etch|original
riceforge revert                 # = apply original
riceforge verify etch            # check a theme without applying it
riceforge doctor                 # packages, links, config syntax, services, duplicate helpers
riceforge update                 # git pull --ff-only, redeploy, report new dependencies
riceforge backups                # list backups; riceforge restore <stamp>
riceforge uninstall [--dry-run]  # see below
```

`riceforge` lives in `~/.local/bin` (fish has that on `PATH`; for bash, add it).

## Machine-specific settings

Nothing machine-specific is tracked. Each computer gets `~/.config/riceforge-local/`:

| file | what | written by |
|---|---|---|
| `machine.conf` | profile, features, keyboard layout, AUR helper | setup (rewritten each run) |
| `hypr.lua` | monitors, input, GPU env, extras. Your lines are kept; only the `>>> riceforge` block is managed | setup (block only) |
| `shell.toml` | astrolabe location (seeded from your timezone) | setup, once |

Examples for `hypr.lua`:

```lua
hl.monitor({ output = "DP-1", mode = "2560x1440@144", position = "0x0", scale = 1 })
hl.monitor({ output = "eDP-1", mode = "preferred", position = "auto", scale = 1.25 })
hl.config({ input = { kb_layout = "us,de", kb_options = "grp:alt_shift_toggle", sensitivity = -0.2 } })
```

Your own binds, rules and autostart go in `~/.config/hypr/custom/*.lua`. Setup seeds them
once and never overwrites them. Kitty settings go in `~/.config/kitty/local.conf`. Hardware
profiles, tested machines and limits are in [docs/HARDWARE.md](docs/HARDWARE.md).

## How it is wired

```
~/riceforge (your clone)  ←─  ~/.config/riceforge           (symlink, if cloned elsewhere)
  config/      base desktop  ←─  ~/.config/hypr/hyprland.lua, hyprlua/, kitty.conf, walker/config.toml, …
  themes/<t>/  looks          ←─  current → themes/nacre  ←─  ~/.config/waybar/style.css, hyprlock.conf, …
  shell/       riceforge-shell (started by the nacre theme's session hook)
  manifests/   packages.tsv, features.tsv, deploy.tsv
  install/     preflight, dependencies, system, user-config, validation, uninstall
  profiles/    desktop, laptop, acer-nitro
~/.config/riceforge-local/   this machine only (never tracked)
~/.local/state/riceforge/    installed.tsv (what setup did), backups/<time>/, logs/
```

Hyprland loads: base `hyprlua/` → `custom/` → `monitors.lua` → `riceforge-local/hypr.lua`
→ the theme layer (looks and motion only). Each theme may ship a `session` script
(start|stop) that owns its long-running helpers: NACRE runs riceforge-shell and the wallpaper
daemon, while ETCH and original run nm-applet, blueman-applet and swaybg. Login runs
`riceforge session-start`, and `apply` stops the old theme's helpers before starting the
new ones, so nothing runs twice.

The plate archive remembers your wallpaper in `themes/<t>/wallpaper.png`. That file is
local state, ignored by git, and repaired from the theme's `DEFAULT_WALLPAPER` if it goes missing.

## Backups, recovery, uninstall

- Every file setup replaces is moved to `~/.local/state/riceforge/backups/<time>/` with its
  path intact. `riceforge restore <time>` puts one backup back.
- `~/.local/state/riceforge/installed.tsv` records each link, seed, gsetting, enabled service
  and installed package. Logs are in `~/.local/state/riceforge/logs/`.
- If setup stops part-way, it says so and where the backups are. Re-running `./setup`
  finishes the job because every step is idempotent.
- `riceforge uninstall` removes only links that still point into Riceforge, restores what they
  replaced, and resets the gsettings it changed. It keeps the repo, `riceforge-local`,
  wallpapers, backups, files you edited, and the network and Bluetooth services (turning
  those off could cut your connection). Add `--purge-seeds` to delete unedited seeded files,
  or `--remove-packages` to also offer `pacman -Rns` for packages Riceforge installed.
- Broken theme? `riceforge apply etch` or `riceforge revert`. Broken session? Switch to a TTY
  (`Ctrl+Alt+F3`), log in, and run `riceforge uninstall` or `riceforge apply original`.

## Troubleshooting

| symptom | try |
|---|---|
| anything | `riceforge doctor` first; it names missing packages, dangling links, config errors, duplicated helpers |
| SUPER does nothing | Walker/Elephant are AUR packages: `riceforge doctor`; `pgrep -a elephant` |
| Wi-Fi/Bluetooth panel empty | `systemctl status NetworkManager bluetooth`; panels only run under NACRE |
| a key fires twice | doctor reports duplicate binds; check `~/.config/hypr/custom/keybinds.lua` |
| Hyprland config error banner | `Hyprland --verify-config -c ~/.config/hypr/hyprland.lua` |
| display serif looks plain | install `otf-cormorant` (feature `aesthetic`) |
| wrong sunrise times | set `[location]` in `~/.config/riceforge-local/shell.toml`, then `riceforge-shell quit; riceforge session-start` |
| fan icons missing | expected unless the Acer `linuwu_sense` driver is installed (see HARDWARE.md) |

## Development and tests

```bash
tests/run.sh                 # all safe suites
tests/clean-container.sh     # fresh Arch container + real pacman (needs docker; ~1.5 GB)
```

The safe suites run in a throwaway copy of the repo with a fake `$HOME`, mocked
`pacman`/`sudo`/`systemctl`/`gsettings`, and no Hyprland session variables. Session-helper
tests run in a private PID namespace. None of them touch the live desktop, services,
packages or network. Coverage includes manifest consistency (every command the configs run
must map to a package), syntax of JSON, Lua, Python, shell and TOML, permissions, absolute
`/home` paths and private data, install/rerun/uninstall/restore, theme switching, wallpaper
repair, process duplication, profiles, timezone location and missing optional packages.
Hardware tests that really disconnect Wi-Fi or Bluetooth are opt-in:
`shell/tests/test_disruptive.py`.

What was verified, and on what, is listed in [docs/HARDWARE.md](docs/HARDWARE.md#what-was-tested).

## Credits and licence

Riceforge's own code is MIT ([LICENSE](LICENSE)). The Walker theme directories are derived from
Walker's default theme and are GPL-3.0 (see `themes/*/walker/NOTICE`). The plates use public-domain
engravings by Flammarion (anonymous), Vesalius, Doré, Fludd and Nasmyth, and fonts come from
Arch packages under their own licences. Full list: [CREDITS.md](CREDITS.md).
