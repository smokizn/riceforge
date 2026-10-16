# riceforge

Whole-desktop themes for this Hyprland setup, switchable and reversible.
Themes: `original` (your desktop before riceforge), `etch`, `nacre` (active: **Visionary**).

## Commands

    ~/.config/riceforge/bin/riceforge list            # themes
    ~/.config/riceforge/bin/riceforge status          # active theme + link health
    ~/.config/riceforge/bin/riceforge verify nacre    # validate without applying
    ~/.config/riceforge/bin/riceforge apply nacre     # verify, switch, live-reload, run session hooks
    ~/.config/riceforge/bin/riceforge revert          # back to your pre-riceforge look
    ~/.config/riceforge/bin/riceforge session-start   # (login) start the active theme's session
    ~/.config/riceforge/bin/riceforge detach          # remove riceforge, restore plain files

Re-applying the same theme after editing its Walker CSS: `RICEFORGE_RESTART_WALKER=1 riceforge apply nacre`.

## How it is wired

`current -> themes/<name>`; these files in `~/.config` are symlinks through it:
`hypr/riceforge.lua`, `hypr/hyprlock.conf`, `waybar/config.jsonc`, `waybar/style.css`,
`kitty/riceforge-theme.conf`, `swaync/style.css`, `walker/themes/<name>`.
`~/.config/fish/conf.d/riceforge.fish` sources `current/fish/theme.fish` when the theme has one.

**Session hooks.** A theme may ship `themes/<t>/session` (start|stop) owning its long-running helpers.
`apply` stops the old theme's session and starts the new one. `original` and `etch` run nm-applet,
blueman-applet and swaybg; `nacre` runs riceforge-shell (and awww-daemon if installed) instead.
At login `hyprlua/execs.lua` runs `riceforge session-start`; the applet/swaybg lines it replaced are
kept, commented with `-- riceforge-session:`, and `detach` restores them verbatim (round trip tested).

Edits outside riceforge (backed up in `backups/pre-visionary-2026-10-17.tar.gz`):
- `hypr/hyprlua/execs.lua`: duplicate `swaync`, uninstalled `swayosd-server`/`hyprpaper`, and the racing
  `systemctl --user restart elephant.service` commented out with reasons; `hypridle` added.
- `hypr/hypridle.conf`: lock 5 min, screen off 10 min, no suspend; Lua-mode dpms dispatch
  (`hyprctl dispatch 'hl.dsp.dpms({action = "off"})'`). The old config called a non-existent quickshell lock.
- `hypr/custom/keybinds.lua`: four new binds (see Controls); previous file in `backups/custom-keybinds.lua.pre-visionary`.

## NACRE · Visionary

An antique celestial instrument: engraved plates under ink glass, parchment type, lunar silver,
tarnished brass for the sun, crimson only for critical states.

| token | hex | role |
|---|---|---|
| ink / charcoal / graphite | `#0b0a0a` `#151413` `#2a2826` | grounds, glass |
| stone | `#6e6a64` | quiet text, empty states |
| lunar silver | `#b9bcc2` | rules, borders, moon |
| bone / parchment | `#e6dfcf` `#d6cbb2` | text |
| tarnished brass | `#b39a5e` | sun, active, primary actions |
| crimson | `#a8464f` | critical only |

Type: Cormorant / Cormorant SC (display; falls back to Noto Serif), Adwaita Sans (UI),
Iosevka Nerd Font Mono (terminal). Icons: 65 hand-authored hairline SVGs in 6 colours
(`themes/nacre/icons`, built by `tools/build_icons.py`).

**Hyprland** (`themes/nacre/hypr.lua`): silver-brass engraved focus line, rounding 14, blur on windows
and per-layer (bar, notifications, shell panels), real spring physics:
unveil ζ.62 (windows open, 8% overshoot, ~510 ms), glide ζ.74 (workspaces), wobble ζ.68 (moves),
drop ζ.60 (scratchpads), pop ζ.65 (layers); closing uses a swell-then-melt bezier.

**Waybar**: sigil orb (Walker) + constellation workspaces (stars on a hairline, brass = active);
engraved clock plaque with the moon's real phase (click: ephemeris); instruments drawer;
connections slab (NetworkManager `network` + `bluetooth`, clicks open the panels); senses; battery vial.

**Walker**: manuscript header (sun · INVOCATIO · moon, prefix hints), serif search line,
brass margin rule on the selected entry, provider tags (file, calc, clip, symbol, glyph, mark, pkg).

**riceforge-shell** (`shell/`, one resident GTK4 + gtk4-layer-shell process, session bus only):
- **Wi-Fi panel**: libnm async + NM signals; scan with in-flight guard and NM rate-limit handling;
  APs deduplicated by SSID with signal/security/band; connect (saved or new, PSK/SAE/WEP/open/OWE),
  success only on NM `ACTIVATED`, 45 s timeout, failure reasons from the device state reason,
  wrong-password prompt that updates the saved key, a failed new profile is deleted; disconnect,
  radio toggle, saved networks (autoconnect, forget with confirm), hidden networks.
  Passwords go straight into NM settings (system-stored); never logged or written by this code.
  802.1X/enterprise: use nm-connection-editor.
- **Bluetooth panel**: BlueZ D-Bus model fed by InterfacesAdded/Removed + PropertiesChanged and a name
  watch; power, discovery (auto-stops after 30 s), Connected/Paired/Nearby, battery, RSSI, trust;
  pair (45 s, CancelPairing on timeout), connect/disconnect, forget (two-click confirm), mapped errors.
  **Pairing agent** (`org.bluez.Agent1`, KeyboardDisplay, default agent while nacre is active): passkey
  confirmation, PIN/passkey entry, service authorization with "Always allow" (sets Trusted). It only
  answers calls whose sender is bluetoothd's own bus name.
- **Plate archive** (SUPER+ALT+W): plates + `~/Pictures/Wallpapers`; arrows to browse, Space previews on the
  desktop, Enter sets, Esc reverts; metadata and attribution; unreadable files are marked and skipped.
  Backend: awww crossfade if installed, else a flash-free swaybg swap (instant). Choice persists in
  `themes/nacre/wallpaper.png` (also used by hyprlock); a missing plate falls back to the first good one.
- **Desk** (bottom-right, BOTTOM layer): astrolabe (24 h dial, daylight arc from NOAA sunrise/sunset,
  brass sun / silver moon hand, the real moon phase) and an instrument strip (Wi-Fi, Bluetooth,
  battery via UPower, now playing via MPRIS with play/pause, CPU/RAM from /proc, current plate).
  Click the dial for the lunar ephemeris. Location: `shell/config.toml` (default: New Delhi, from your timezone).
- **Kitty / fish / swaync / hyprlock**: same palette; fish greeting shows the moon's phase; hyprlock shows an
  engraved astrolabe ring with today's moon and nothing private.

## Controls

| key / click | action |
|---|---|
| SUPER+ALT+W | plate archive (wallpapers) |
| SUPER+ALT+N, click Wi-Fi in the bar or desk | Wi-Fi panel |
| SUPER+ALT+B, click Bluetooth in the bar or desk | Bluetooth panel |
| SUPER+ALT+M, click the moon or the astrolabe | lunar ephemeris |
| Esc / clicking elsewhere | close a panel |

The binds only act while riceforge-shell runs (nacre); under other themes they do nothing.
`~/.config/riceforge/shell/riceforge-shell status` prints the live state as JSON.

## Wallpapers

Generated at 1920×1080 by `themes/nacre/tools/plates/compose.py` (sources fetched by `sources.py`,
licence checked against Commons metadata; `sources/sources.json` keeps the records).

| plate | made from |
|---|---|
| I · Machina Mundi | Flammarion engraving (anonymous, 1888), public domain + procedural orbit diagram |
| II · Anatomia Montium | Vesalius, *Tertia musculorum tabula* (1543), NLM via Commons, "no restrictions" + procedural mountains |
| III · Ouroboros Eclipsis | procedural |
| IV · Montes Lunae | procedural |
| V · Oculus Mundi | procedural |
| VI · The Empyrean | Gustave Doré, *Paradiso* Canto 31, public domain |
| VII · Macrocosmus | Robert Fludd, *Utriusque Cosmi* (1617–21), public domain |
| VIII · Selenographia | James Nasmyth, *Normal lunar crater* (1874), public domain |
| IX–XI · Fenestra, Draco, Trigonum | re-prints of your own wallpapers |

Commons pages: see `themes/nacre/tools/plates/sources/sources.json`. No image-generation model was used;
"procedural" means drawn by the Python engraving code. Your originals in `~/Pictures/Wallpapers` are untouched.

## What was tested, and how

Verified on the running desktop (2026-10-17):
- `Hyprland --verify-config`, GTK3/GTK4 CSS parsing, kitty's own config loader, `fish --no-execute`,
  `py_compile`, every icon SVG rendered, Waybar launched with the theme (no config errors).
- `shell/tests/test_logic.py`: 45 checks incl. moon phases against four real eclipse/phase events
  (all within 2 minutes), sunrise/sunset, Wi-Fi security classification, dedup, error mapping.
- `shell/tests/test_live.py` (non-disruptive): real AP list, accepted scan with advancing `last_scan`,
  BlueZ discovery start → Discovering true → stop.
- `shell/tests/test_disruptive.py`, run with your consent: Wi-Fi disconnect + reconnect of my-network through the
  panel's `Attempt` (ACTIVATED after 3.2 s); Tronsmart speaker disconnect + reconnect through
  `BtState.device_op` (BlueZ reported Connected again).
- Theme switching nacre → etch → original → nacre three times: exactly one of each helper per theme
  (applets only outside nacre, riceforge-shell only in nacre), no config errors, pairing agent re-registered
  as default; fish/kitty scoping confirmed.
- riceforge-shell idle: 0.42 % of one core over 60 s, 83 MB RSS (cairo renderer).

Not tested (checklist):
- [ ] Lock screen: press SUPER+L once (hyprlock has no dry-run; keys were checked against the binary).
- [ ] Walker's new look: press SUPER (it takes keyboard focus, so it wasn't opened during the work).
- [ ] Pairing a new device and the agent's passkey prompt (needs a device in pairing mode).
- [ ] An incoming connection from the untrusted speaker (should ask; "Always allow" marks it trusted).
- [ ] Connecting a new secured network and a wrong-password attempt (only on a network you own).
- [ ] realme Buds connect attempt.
- [ ] Gallery keyboard navigation (tested only in a focus-free test mode).

## Known limitations

- No real refraction or window deformation: blur, tint and spring-driven scale/position only.
  There is no fullscreen-specific animation leaf in Hyprland 0.56; fullscreen uses move/fade.
- swaybg cannot crossfade; install `awww` for crossfades (the session switches to it automatically).
- Cormorant isn't installed yet: display type falls back to Noto Serif until you run
  `sudo pacman -S otf-cormorant awww`, then `riceforge apply nacre` and re-run
  `themes/nacre/tools/plates/compose.py themes/nacre/wallpapers` for Cormorant captions.
- The desk surface receives clicks in its own rectangle on an empty desktop (windows always cover it).
- Moon/sun times are computed locally (minutes of accuracy); the fish greeting uses a ±half-day approximation.
- `less` is not installed, so git's pager fails in the terminal (`git --no-pager …` works).

## Recovery

- Switch away: `riceforge apply etch` / `riceforge revert` (original).
- The previous liquid-glass nacre: `git -C ~/.config/riceforge checkout nacre-glass -- themes/nacre`.
- Remove everything riceforge did: `riceforge detach`, then `rm ~/.config/fish/conf.d/riceforge.fish`.
- Full restore of the configs as they were before Visionary:
  `tar xzf ~/.config/riceforge/backups/pre-visionary-2026-10-17.tar.gz -C ~/.config`
- Original pre-riceforge snapshot: `backups/pre-riceforge-2026-10-17.tar.gz`.
- If riceforge-shell misbehaves: `riceforge-shell quit` (unregisters the pairing agent); `riceforge revert`
  brings back nm-applet and blueman-applet.
