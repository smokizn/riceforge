# Hardware

One repository, many machines: the tracked config is generic, and each computer adds a small
local layer. No hardware is assumed. Riceforge has been run on exactly one physical machine
(below), so treat everything else as "should work, untested".

## Profiles

`./setup` detects a profile and lets you change it (`--profile NAME`). Profiles live in `profiles/*.conf`.

| profile | detected when | adds |
|---|---|---|
| desktop | no battery | nothing. Waybar hides battery/backlight modules it can't find |
| laptop | a battery exists | nothing extra. Backlight keys (`brightnessctl` via logind), UPower battery, touchpad natural scroll and tap-to-click are in the base config |
| acer-nitro | DMI vendor Acer and product Nitro/Predator | `config/hypr/extras/acer-nitro.lua`: Fn+F4 (`XF86Launch6`) mic toggle, `XF86Presentation` DAMX fan key |

To add a machine, create `profiles/<name>.conf` (`DESCRIPTION`, `HYPR_EXTRAS`,
`FEATURES_ADD`, `FEATURES_REMOVE`) and, if needed, `config/hypr/extras/<name>.lua`.

## Overrides that never touch the repo

| need | where |
|---|---|
| monitors, resolution, refresh rate, scale, positions | `~/.config/riceforge-local/hypr.lua`: `hl.monitor({ output = "DP-1", mode = "2560x1440@144", position = "0x0", scale = 1 })`. The base default is `preferred/auto/1` for every output |
| keyboard layout, variants, options | `./setup --kb-layout X` (managed block), or your own `hl.config({ input = { ... } })` lines in the same file |
| touchpad, mouse sensitivity | `hl.config({ input = { sensitivity = -0.2, touchpad = { natural_scroll = false } } })` in the same file |
| NVIDIA as the primary GPU | setup offers `extras/nvidia.lua` (`LIBVA_DRIVER_NAME`, `__GLX_VENDOR_LIBRARY_NAME`) when NVIDIA is the only GPU. Hybrid laptops don't need it |
| audio devices | PipeWire/WirePlumber choose devices. Media keys use `wpctl` and `playerctl`, so any MPRIS player works. The bar's now-playing follows Spotify (`--player spotify` in the theme configs) |
| Wi-Fi / Bluetooth adapters | anything NetworkManager and BlueZ support. Credentials are stored by NetworkManager, never by Riceforge |
| time zone and locale | not changed by Riceforge |
| sunrise/sunset location | `~/.config/riceforge-local/shell.toml` (seeded from the time zone's reference city) |
| fonts, cursor, crossfades | feature `aesthetic`. The cursor is your system default (Adwaita) |
| personal binds/rules/autostart | `~/.config/hypr/custom/*.lua` (seeded once, never overwritten) |

## Explicitly not handled

- GPU drivers, kernel parameters, initramfs and bootloader entries are never changed.
  Setup only warns when an NVIDIA GPU has no driver.
- Out-of-tree drivers such as Acer `linuwu_sense` and the DAMX daemon are not installed. The
  fan widgets and the DAMX key appear only when those are present (`/sys/module/linuwu_sense`,
  `/usr/local/bin/fan-toggle` plus a sudoers rule you create).
- Multi-seat, HiDPI fractional-scaling tuning, and per-monitor workspace layouts are left to your local file.

## Tested hardware

| machine | result |
|---|---|
| Acer Nitro ANV15-41: Ryzen 7 + Radeon 680M iGPU driving the panel, RTX 4050 (nvidia-open), MediaTek MT7921 Wi-Fi/BT, 1920×1080@165, Arch Linux, Hyprland 0.56.2 | daily driver; all themes, panels, pairing agent and sessions verified live (2026-10-17) |
| fresh `archlinux:latest` Docker container, x86_64 | see below: clean dependency install and deployment from nothing; no GPU, no systemd, no login |

## What was tested

| test | where | covers |
|---|---|---|
| `tests/run.sh` | author's machine, sandboxed | static checks, installer, themes/sessions, simulated hardware (Acer hybrid, NVIDIA tower, Intel laptop, aarch64), dependency handling with mocks |
| `tests/clean-container.sh` | fresh Arch container | real `pacman` install of the official packages, first run, idempotent re-run, doctor, `Hyprland --verify-config`, theme switching, uninstall |
| `shell/tests/test_live.py` | author's machine | real AP list, accepted scan, BlueZ discovery start/stop (non-disruptive) |
| `shell/tests/test_disruptive.py` | author's machine, with consent | Wi-Fi disconnect/reconnect and Bluetooth speaker disconnect/reconnect through the panels' code paths |

**Not tested:** a full graphical first login on a freshly installed physical machine, SDDM
on a fresh system, AUR installs in the clean container (no helper there), and any non-Acer
laptop or desktop hardware.
