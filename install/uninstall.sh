#!/usr/bin/env bash
# riceforge uninstall: undo what ~/.local/state/riceforge/installed.tsv says
# Riceforge did. Removes only links that still point into Riceforge, restores the
# files they replaced, keeps everything you edited or own.
#   --dry-run          show what would happen
#   --yes              don't ask
#   --purge-seeds      also delete seeded custom/ files you never changed
#   --remove-packages  also remove packages Riceforge installed (asks; pacman -Rns)
# Never touches: wallpapers, ~/.config/riceforge-local, the repo, network/bluetooth
# services (disabling them could drop your connection) or your display manager.
set -uo pipefail
RF_SRC="${RF_SRC:-$(cd "$(dirname "$(readlink -f "${BASH_SOURCE[0]}")")/.." && pwd -P)}"
export RF_SRC
# shellcheck source=lib.sh
. "$RF_SRC/install/lib.sh"

PURGE_SEEDS=0; REMOVE_PKGS=0
for a in "$@"; do
    case "$a" in
        --dry-run) DRY_RUN=1 ;; --yes|-y) ASSUME_YES=1 ;;
        --purge-seeds) PURGE_SEEDS=1 ;; --remove-packages) REMOVE_PKGS=1 ;;
        -h|--help) sed -n '2,12p' "$0" | sed 's/^# \{0,1\}//'; exit 0 ;;
        *) die "unknown option $a" ;;
    esac
done

[[ -f "$RF_STATE_FILE" ]] || die "no install record at $RF_STATE_FILE; nothing to undo"
start_log uninstall
say "uninstalling Riceforge$([[ "$DRY_RUN" == 1 ]] && echo " (dry run)")"
[[ "$DRY_RUN" == 1 ]] || confirm "remove Riceforge's links and restore your previous files?" || die "cancelled"

# stop the active theme's helpers first (pairing agent, wallpaper daemon)
if [[ -n "${HYPRLAND_INSTANCE_SIGNATURE:-}" && -L "$RF_SRC/current" ]]; then
    t=$(basename "$(readlink "$RF_SRC/current")")
    [[ -x "$RF_SRC/themes/$t/session" ]] && run "$RF_SRC/themes/$t/session" stop
fi

removed=0 restored=0 kept=0
while IFS=$'\t' read -r kind target backup detail; do
    case "$kind" in
        link)
            dst="$HOME/$target"
            if [[ -L "$dst" && "$(readlink "$dst")" == "$RF/"* ]]; then
                run rm -f -- "$dst"; removed=$((removed+1))
            elif [[ -e "$dst" || -L "$dst" ]]; then
                warn "~/$target was changed after install; left alone"; kept=$((kept+1)); continue
            fi
            if [[ "$backup" != - && ( -e "$backup" || -L "$backup" ) ]]; then
                run mkdir -p "$(dirname "$dst")"
                run cp -a -- "$backup" "$dst"; restored=$((restored+1)); note "restored ~/$target"
            fi
            state_del link "$target" ;;
        seed)
            dst="$HOME/$target"
            if [[ "$PURGE_SEEDS" == 1 && "$detail" != preexisting && -f "$dst" && "$(sha "$dst")" == "$detail" ]]; then
                run rm -f -- "$dst"; note "removed unchanged ~/$target"
            else kept=$((kept+1)); fi
            state_del seed "$target" ;;
        gsetting)
            if [[ "$detail" != - ]] && have gsettings; then
                run gsettings set org.gnome.desktop.interface "$target" "$detail" && note "gsettings $target restored to $detail"
            fi
            state_del gsetting "$target" ;;
        repo-link)
            if [[ -L "$target" ]]; then run rm -f -- "$target"; note "removed $target (checkout stays at $detail)"; fi
            state_del repo-link "$target" ;;
        service)
            note "left enabled: $target (disable yourself if unwanted: sudo systemctl disable $target)" ;;
        pkg) ;;
    esac
done < <(state_rows)

pkgs=$(state_rows pkg | cut -f2 | tr '\n' ' ')
if [[ -n "${pkgs// /}" ]]; then
    if [[ "$REMOVE_PKGS" == 1 ]]; then
        note "packages Riceforge installed: $pkgs"
        warn "removing them can break other software that started using them"
        if confirm "remove them with pacman -Rns?" n; then
            # shellcheck disable=SC2086
            run_root pacman -Rns $pkgs && for p in $pkgs; do state_del pkg "$p"; done
        fi
    else
        note "packages Riceforge installed were kept: $pkgs"
        note "remove later with: riceforge uninstall --remove-packages"
    fi
fi

say "done: $removed links removed, $restored files restored, $kept kept"
note "kept: ~/.config/riceforge (the repo), ~/.config/riceforge-local, wallpapers, backups in $RF_STATE/backups"
note "log out and back in for the previous configuration to take effect"
