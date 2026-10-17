# System configuration: only what Riceforge needs, and never bootloader, kernel,
# GPU drivers, disks or network credentials. Every change is recorded.
# shellcheck shell=bash

enable_service() {  # unit [now]
    local unit="$1" now="${2:-}"
    if systemctl is-enabled --quiet "$unit" 2>/dev/null; then
        ok "$unit already enabled"
        if [[ -n "$now" ]] && ! systemctl is-active --quiet "$unit"; then
            run_root systemctl start "$unit" && ok "$unit started"
        fi
        return 0
    fi
    if confirm "enable ${unit}${now:+ and start it now}?"; then
        run_root systemctl enable ${now:+--now} "$unit" || { warn "could not enable $unit"; return 1; }
        state_put service "$unit" - enabled-by-riceforge
        ok "$unit enabled"
    fi
}

configure_system() {
    say "system"
    [[ "${PF_NO_SUDO:-0}" == 1 ]] && { warn "no sudo: skipping system services"; return 0; }

    # Network: NetworkManager backs the Wi-Fi panel and bar. Never take over from
    # another active network stack — that would drop your connection.
    if [[ -n "${PF_NET_CONFLICT:-}" ]]; then
        if systemctl is-enabled --quiet NetworkManager.service 2>/dev/null; then
            ok "NetworkManager enabled (alongside: $PF_NET_CONFLICT)"
        else
            warn "not enabling NetworkManager while $PF_NET_CONFLICT is active; the Wi-Fi panel needs NM"
            note "switch yourself when convenient: https://wiki.archlinux.org/title/NetworkManager"
        fi
    elif pacman -T networkmanager >/dev/null 2>&1; then
        enable_service NetworkManager.service now
    fi

    # Bluetooth: the panel is a BlueZ client. Start it now only if an adapter exists.
    if pacman -T bluez >/dev/null 2>&1; then
        if [[ "${PF_BT:-0}" == 1 ]]; then enable_service bluetooth.service now
        else note "no Bluetooth adapter detected; bluetooth.service left as is"; fi
    fi

    # Login: keep any display manager you already use. Otherwise offer SDDM.
    if [[ -n "${PF_DM:-}" ]]; then
        ok "display manager: keeping $PF_DM (pick 'Hyprland (uwsm-managed)' or 'Hyprland' at login)"
    elif feature_on display-manager; then
        if pacman -T sddm >/dev/null 2>&1; then
            # enable only: starting it from a console would replace that console
            enable_service sddm.service && note "SDDM starts at next boot"
        fi
    else
        note "no display manager: log in on a console and run  uwsm start hyprland.desktop  (or start-hyprland)"
    fi
}

configure_user_session() {
    say "user session"
    have xdg-user-dirs-update && run xdg-user-dirs-update
    run mkdir -p "$HOME/Pictures/Screenshots" "$HOME/Pictures/Wallpapers"

    # GTK apps follow the dark ink palette; remember previous values for uninstall
    if have gsettings; then
        local key prev want
        for key in "color-scheme:prefer-dark" "gtk-theme:Adwaita-dark"; do
            want="${key#*:}"; key="${key%%:*}"
            prev=$(gsettings get org.gnome.desktop.interface "$key" 2>/dev/null | tr -d "'") || continue
            [[ "$prev" == "$want" ]] && continue
            state_get gsetting "$key" >/dev/null || state_put gsetting "$key" - "$prev"
            run gsettings set org.gnome.desktop.interface "$key" "$want" && ok "gsettings $key = $want (was $prev)"
        done
    fi
}
