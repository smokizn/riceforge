# User environment: put the repo at ~/.config/riceforge, deploy manifests/deploy.tsv,
# and write the machine-local files in ~/.config/riceforge-local.
# shellcheck shell=bash

ensure_repo_location() {
    if [[ "$RF_SRC" == "$RF" ]]; then return 0; fi
    if [[ -L "$RF" && "$(readlink -f "$RF")" == "$RF_SRC" ]]; then return 0; fi
    [[ -e "$RF" ]] && die "$RF exists and is not this checkout"
    run mkdir -p "$(dirname "$RF")"
    run ln -s "$RF_SRC" "$RF"
    state_put repo-link "$RF" - "$RF_SRC"
    ok "linked $RF -> $RF_SRC (keep the checkout where it is)"
}

# deploy_link <source rel> <target rel>
deploy_link() {
    local src="$RF/$1" dst="$HOME/$2" cur bk="-"
    if [[ -L "$dst" ]]; then
        cur=$(readlink "$dst")
        if [[ "$cur" == "$src" ]]; then
            state_get link "$2" >/dev/null || state_put link "$2" - "$1"
            return 0
        fi
    fi
    if [[ -e "$dst" || -L "$dst" ]]; then
        # an earlier riceforge link (e.g. old /home/<user> absolute path) is just replaced
        if [[ -L "$dst" && "$(readlink "$dst")" == */.config/riceforge/* ]]; then
            run rm -f -- "$dst"
        else
            bk=$(backup_move "$dst")
            note "backed up ~/$2"
        fi
    fi
    run mkdir -p "$(dirname "$dst")"
    run ln -sfn "$src" "$dst"
    # keep the first backup if a later run had nothing new to save
    if [[ "$bk" == - ]]; then
        local prev; prev=$(state_get link "$2" 2>/dev/null | cut -f1) || true
        [[ -n "$prev" ]] && bk="$prev"
    fi
    state_put link "$2" "$bk" "$1"
    DEPLOY_CHANGED=$((DEPLOY_CHANGED + 1))
}

deploy_seed() {
    local src="$RF_SRC/$1" dst="$HOME/$2"
    if [[ -e "$dst" ]]; then
        state_get seed "$2" >/dev/null || state_put seed "$2" - "preexisting"
        return 0
    fi
    run mkdir -p "$(dirname "$dst")"
    run cp -- "$src" "$dst"
    state_put seed "$2" - "$(sha "$src")"
    DEPLOY_CHANGED=$((DEPLOY_CHANGED + 1))
}

deploy_all() {
    local mode src dst
    DEPLOY_CHANGED=0
    while IFS=$'\t' read -r mode src dst; do
        case "$mode" in
            link) deploy_link "$src" "$dst" ;;
            seed) deploy_seed "$src" "$dst" ;;
            *) die "deploy.tsv: unknown mode '$mode'" ;;
        esac
    done < <(manifest_rows deploy.tsv)
    ok "deployed $(manifest_rows deploy.tsv | wc -l) entries ($DEPLOY_CHANGED changed)"
}

# timezone -> "place<TAB>lat<TAB>lon" from zone1970.tab (ISO 6709 coordinates)
tz_location() {
    local tz; tz=$(timedatectl show -p Timezone --value 2>/dev/null || true)
    [[ -z "$tz" ]] && tz=$(readlink /etc/localtime 2>/dev/null | sed 's|.*/zoneinfo/||' || true)
    [[ -z "$tz" ]] && return 1
    awk -F'\t' -v tz="$tz" '
        function dms(s, w,   sign, d, m, x) {
            sign = substr(s,1,1)=="-" ? -1 : 1; s = substr(s,2)
            d = substr(s,1,w); m = substr(s,w+1,2); x = substr(s,w+3,2)
            return sign * (d + m/60 + (x==""?0:x)/3600)
        }
        $3==tz { c=$2; i = match(substr(c,2), /[+-]/) + 1
                 la = substr(c,1,i-1); lo = substr(c,i)
                 n = split(tz, p, "/"); gsub(/_/, " ", p[n])
                 printf "%s (timezone default)\t%.2f\t%.2f\n", p[n], dms(la,2), dms(lo,3); exit }
    ' /usr/share/zoneinfo/zone1970.tab 2>/dev/null
}

write_local_files() {
    run mkdir -p "$RF_LOCAL"
    if [[ "$DRY_RUN" != 1 ]]; then
        cat > "$RF_LOCAL/machine.conf" <<EOF
# Written by ./setup on $(date -I). Re-run ./setup to change; safe to edit.
PROFILE="$PROFILE"
FEATURES="$FEATURES"
HYPR_EXTRAS="$HYPR_EXTRAS"
KB_LAYOUT="$KB_LAYOUT"
AUR_HELPER="${AUR_HELPER:-}"
EOF
    fi
    ok "machine settings: ~/.config/riceforge-local/machine.conf"

    # Hyprland machine layer: your lines are kept; only the marked block is managed
    local hl="$RF_LOCAL/hypr.lua" block e
    block="-- >>> riceforge (managed by ./setup; edit outside this block) >>>"$'\n'
    block+="hl.config({ input = { kb_layout = \"$KB_LAYOUT\" } })"$'\n'
    for e in $HYPR_EXTRAS; do
        [[ -f "$RF_SRC/config/hypr/extras/$e.lua" ]] || { warn "unknown Hyprland extra '$e'"; continue; }
        block+="dofile(HOME .. \"/.config/riceforge/config/hypr/extras/$e.lua\")"$'\n'
    done
    block+="-- <<< riceforge <<<"
    if [[ "$DRY_RUN" == 1 ]]; then note "would write the managed block of $hl"; else
        if [[ ! -f "$hl" ]]; then
            cat > "$hl" <<EOF
-- Machine-local Hyprland settings for this computer (not tracked by git).
-- Loaded after the base config and before the theme. Examples:
--   hl.monitor({ output = "DP-1", mode = "2560x1440@144", position = "0x0", scale = 1 })
--   hl.monitor({ output = "eDP-1", mode = "preferred", position = "auto", scale = 1.25 })
--   hl.config({ input = { kb_layout = "us,de", kb_options = "grp:alt_shift_toggle" } })
-- \`hyprctl monitors\` lists your outputs. Hyprland reloads this file when you save it.

$block
EOF
        else
            python3 -I - "$hl" "$block" <<'PY'
import re, sys
path, block = sys.argv[1], sys.argv[2]
s = open(path).read()
pat = re.compile(r"-- >>> riceforge.*?-- <<< riceforge <<<", re.S)
s = pat.sub(lambda m: block, s, count=1) if pat.search(s) else s.rstrip("\n") + "\n\n" + block + "\n"
open(path, "w").write(s)
PY
        fi
    fi
    ok "Hyprland machine layer: ~/.config/riceforge-local/hypr.lua (extras: ${HYPR_EXTRAS:-none})"

    # riceforge-shell location for sunrise/sunset: seeded once from the timezone
    if [[ ! -f "$RF_LOCAL/shell.toml" ]]; then
        local loc place lat lon
        loc=$(tz_location) || loc=""
        if [[ -n "$loc" ]]; then
            IFS=$'\t' read -r place lat lon <<< "$loc"
            if [[ "$DRY_RUN" != 1 ]]; then
                printf '# riceforge-shell settings for this machine (overrides shell/config.toml)\n[location]\nplace = "%s"\nlat = %s\nlon = %s\n' \
                    "$place" "$lat" "$lon" > "$RF_LOCAL/shell.toml"
            fi
            ok "astrolabe location: $place ($lat, $lon) — edit ~/.config/riceforge-local/shell.toml"
        else
            note "timezone unknown; astrolabe uses Greenwich until you set ~/.config/riceforge-local/shell.toml"
        fi
    fi
}

fix_permissions() {
    local f n=0
    while IFS= read -r -d '' f; do
        if [[ ! -x "$f" ]]; then run chmod +x "$f"; n=$((n+1)); fi
    done < <(find "$RF_SRC/bin" "$RF_SRC/install" "$RF_SRC/tests" "$RF_SRC/config" "$RF_SRC/shell" "$RF_SRC/themes" \
                 -type f \( -name '*.sh' -o -name 'riceforge' -o -name 'riceforge-shell' -o -name 'session' \
                            -o -path '*/hyprland/scripts/*.py' -o -path '*/waybar/scripts/*.py' \) -print0 2>/dev/null)
    [[ -x "$RF_SRC/setup" ]] || { run chmod +x "$RF_SRC/setup"; n=$((n+1)); }
    ok "script permissions ($n fixed)"
}

deploy_user_config() {
    say "user configuration"
    ensure_repo_location
    fix_permissions
    render_templates; ok "templates rendered"
    local t
    for t in "$RF_SRC"/themes/*/; do ensure_wallpaper "$(basename "$t")" || true; done
    # theme-layer links need a current theme before they can resolve
    if [[ ! -L "$RF_SRC/current" ]]; then run ln -sfn "themes/$THEME" "$RF_SRC/current"; fi
    deploy_all
    write_local_files
}
