#!/usr/bin/env bash
# riceforge doctor: read-only checks of packages, files, configs, services and
# running helpers. Never changes anything. Exit 1 if a required check fails.
#   --quick   skip the slower config parsers (Hyprland, GTK CSS)
set -uo pipefail
RF_SRC="${RF_SRC:-$(cd "$(dirname "$(readlink -f "${BASH_SOURCE[0]}")")/.." && pwd -P)}"
export RF_SRC
# shellcheck source=lib.sh
. "$RF_SRC/install/lib.sh"
# shellcheck source=dependencies.sh
. "$RF_SRC/install/dependencies.sh"

QUICK=0; [[ "${1:-}" == --quick ]] && QUICK=1
FAIL=0; WARN=0
fail() { warn "$*"; FAIL=1; }
soft() { warn "$*"; WARN=$((WARN+1)); }

load_machine
[[ -z "$FEATURES" ]] && FEATURES=$(awk -F'\t' '!/^#/ && $2=="on" {printf "%s ", $1}' "$RF_SRC/manifests/features.tsv")

check_packages() {
    say "packages (features: $FEATURES)"
    local pkg s feat tier cmds _ c
    while IFS=$'\t' read -r pkg s feat tier cmds _; do
        feature_on "$feat" || continue
        if ! satisfied "$pkg"; then
            if [[ "$tier" == 1 ]]; then fail "missing required package $pkg ($s)"; else soft "missing $feat package $pkg ($s)"; fi
            continue
        fi
        [[ "$cmds" == - ]] && continue
        IFS=, read -ra cl <<< "$cmds"
        for c in "${cl[@]}"; do
            have "$c" && continue
            if [[ "$tier" == 1 ]]; then fail "$pkg is installed but '$c' is not on PATH"; else soft "$pkg is installed but '$c' is not on PATH"; fi
        done
    done < <(manifest_rows packages.tsv)
    (( FAIL )) || ok "selected packages present"
}

check_files() {
    say "files"
    local mode src dst bad=0
    [[ "$(readlink -f "$RF")" == "$RF_SRC" ]] || { fail "$RF does not point at this checkout"; bad=1; }
    while IFS=$'\t' read -r mode src dst; do
        local t="$HOME/$dst"
        case "$mode" in
            link)
                if [[ ! -L "$t" ]]; then fail "~/$dst is not a Riceforge link (run ./setup)"; bad=1
                elif [[ "$(readlink "$t")" != "$RF/$src" ]]; then fail "~/$dst points to $(readlink "$t"), expected $RF/$src"; bad=1
                elif [[ ! -e "$t" ]]; then fail "~/$dst is a dangling link"; bad=1; fi ;;
            seed) [[ -e "$t" ]] || { soft "~/$dst missing (./setup seeds it)"; bad=1; } ;;
        esac
    done < <(manifest_rows deploy.tsv)
    (( bad )) || ok "$(manifest_rows deploy.tsv | wc -l) deployed entries resolve"
    local active; active=$(basename "$(readlink "$RF_SRC/current" 2>/dev/null)" 2>/dev/null)
    if [[ -z "$active" || ! -d "$RF_SRC/themes/$active" ]]; then fail "no active theme (current link)"; else ok "active theme: $active"; fi
    [[ -e "$RF_SRC/current/wallpaper.png" ]] && ok "wallpaper: $(basename "$(readlink -f "$RF_SRC/current/wallpaper.png")")" \
        || fail "active theme has no wallpaper (riceforge session-start repairs it)"
    local f
    for f in "$RF_SRC"/themes/*/walker/*.in; do [[ -e "$f" && ! -e "${f%.in}" ]] && fail "template not rendered: ${f%.in}"; done
    [[ -f "$RF_LOCAL/machine.conf" ]] && ok "machine layer: ~/.config/riceforge-local (profile ${PROFILE:-?})" || soft "no ~/.config/riceforge-local/machine.conf (run ./setup)"
    # every ~/ path the configs reference must exist (catches dangling script paths)
    local ref missing=0 src p
    while IFS=: read -r src ref; do
        p="${ref/#\~/$HOME}"
        if [[ "$src" == "$RF_SRC"/themes/* ]]; then      # a theme's own current/... is that theme
            local th="${src#"$RF_SRC"/themes/}"; th="${th%%/*}"
            p="${p/#$HOME\/.config\/riceforge\/current\//$RF_SRC/themes/$th/}"
        fi
        [[ -e "$p" ]] || { soft "referenced but missing: $ref (in ${src#"$RF_SRC"/})"; missing=1; }
    done < <(grep -roE '~/\.config/[A-Za-z0-9_./-]+\.(sh|py|xml|png|conf|lua)' \
                "$RF_SRC/config" "$RF_SRC/themes"/*/waybar/config.jsonc "$RF_SRC/themes"/*/hyprlock.conf 2>/dev/null \
             | grep -v -e 'riceforge-local' -e 'kitty/local' | sort -u)
    (( missing )) || ok "every ~/.config path the configs reference exists"
}

check_configs() {
    say "configuration syntax"
    if (( QUICK )); then note "skipped (--quick)"; return; fi
    if [[ -z "${XDG_RUNTIME_DIR:-}" ]]; then
        export XDG_RUNTIME_DIR; XDG_RUNTIME_DIR=$(mktemp -d); chmod 700 "$XDG_RUNTIME_DIR"
    fi
    if have Hyprland && [[ -e "$HOME/.config/hypr/hyprland.lua" ]]; then
        local out; out=$(Hyprland --verify-config -c "$HOME/.config/hypr/hyprland.lua" 2>&1 | sed -n '/Config parsing result/,$p' | tail -n +3)
        [[ "$out" == "config ok" ]] && ok "Hyprland: full config ok" || fail "Hyprland config: $out"
    fi
    local t
    for t in "$RF_SRC"/themes/*/; do
        RICEFORGE_NO_LIVE=1 "$RF_SRC/bin/riceforge" verify "$(basename "$t")" >/dev/null 2>"$RF_STATE/.verify.err" \
            && ok "theme $(basename "$t") verifies" || fail "theme $(basename "$t"): $(tail -3 "$RF_STATE/.verify.err" 2>/dev/null)"
    done
    rm -f "$RF_STATE/.verify.err"
    # duplicate keybinds across files make one keypress fire twice
    local dups
    dups=$(grep -rhoE 'hl\.bind\("[^"]+",' "$HOME/.config/hypr/hyprlua" "$HOME/.config/hypr/custom" "$RF_LOCAL" \
               $(awk '/^dofile/ {gsub(/.*riceforge\/|".*/, ""); print "'"$RF_SRC"'/" $0}' "$RF_LOCAL/hypr.lua" 2>/dev/null) 2>/dev/null \
           | sort | uniq -d | sed 's/hl.bind("//; s/",$//')
    [[ -z "$dups" ]] && ok "no duplicate keybinds" || soft "keys bound more than once (check ~/.config/hypr/custom): $(echo $dups)"
}

check_services() {
    say "services"
    local s
    for s in NetworkManager bluetooth; do
        if systemctl is-active --quiet "$s.service" 2>/dev/null; then ok "$s active"
        elif [[ "$s" == bluetooth ]] && ! compgen -G '/sys/class/bluetooth/hci*' >/dev/null; then note "bluetooth: no adapter"
        else soft "$s.service is not active (Wi-Fi/Bluetooth panels need it)"; fi
    done
    for s in pipewire pipewire-pulse wireplumber; do
        systemctl --user is-active --quiet "$s" 2>/dev/null && ok "$s (user) active" || soft "$s (user) not active"
    done
    local dm; dm=$(readlink -f /etc/systemd/system/display-manager.service 2>/dev/null)
    [[ -n "$dm" && -e "$dm" ]] && ok "display manager: $(basename "$dm" .service)" || note "no display manager (console login + uwsm start hyprland.desktop)"
}

check_processes() {
    say "running session"
    if [[ -z "${HYPRLAND_INSTANCE_SIGNATURE:-}" ]]; then note "not inside Hyprland; skipped"; return; fi
    local active; active=$(basename "$(readlink "$RF_SRC/current")")
    local p n want
    for p in waybar swaync walker elephant hypridle riceforge-shell nm-applet blueman-applet swaybg awww-daemon; do
        n=$(pgrep -cx "$p" 2>/dev/null || true); n=${n:-0}
        case "$p" in
            riceforge-shell) [[ "$active" == nacre ]] && want=1 || want=0 ;;
            nm-applet|blueman-applet) [[ "$active" == nacre ]] && want=0 || want=1 ;;
            swaybg|awww-daemon) want=any ;;
            *) want=1 ;;
        esac
        if [[ "$want" == any ]]; then (( n <= 1 )) && note "$p: $n" || fail "$p running $n times (duplicated)"
        elif (( n == want )); then ok "$p: $n"
        elif (( n > 1 )); then fail "$p running $n times (duplicated)"
        else soft "$p: $n running, expected $want for theme $active"; fi
    done
    local u
    for u in "app-nm\\x2dapplet@autostart.service" "app-blueman@autostart.service"; do
        systemctl --user is-active --quiet "$u" 2>/dev/null \
            && soft "$u was started by XDG autostart (log out and in once after ./setup to stop that)"
    done
    if pgrep -x swaybg >/dev/null && pgrep -x awww-daemon >/dev/null; then soft "both swaybg and awww-daemon are running"; fi
}

check_packages; check_files; check_configs; check_services; check_processes
echo
if (( FAIL )); then say "doctor: problems found (see ✗/! above)"; exit 1
elif (( WARN )); then say "doctor: OK with $WARN warning(s)"
else say "doctor: all checks passed"; fi
