# Preflight: what system is this, and is it safe to continue? Sets PF_* variables.
# shellcheck shell=bash
# RF_SYSFS / RF_ARCH / RF_ASSUME_ONLINE exist so tests can simulate other machines.
SYSFS="${RF_SYSFS:-/sys}"

detect_gpus() {  # -> space list of vendors from /sys (works without pciutils)
    local v out=""
    for v in "$SYSFS"/class/drm/card[0-9]*/device/vendor; do
        [[ -r "$v" ]] || continue
        case "$(cat "$v")" in
            0x10de) out+=" nvidia" ;; 0x1002) out+=" amd" ;; 0x8086) out+=" intel" ;;
            *) out+=" other" ;;
        esac
    done
    # unique, keep order
    echo "$out" | tr ' ' '\n' | awk 'NF && !seen[$0]++' | tr '\n' ' ' | sed 's/ $//'
}

detect_dm() {  # enabled display manager unit, or empty
    local l
    l=$(readlink -f /etc/systemd/system/display-manager.service 2>/dev/null) || true
    if [[ -n "$l" && -e "$l" ]]; then basename "$l" .service; fi
}

detect_profile() {
    local vendor product
    vendor=$(cat "$SYSFS"/class/dmi/id/sys_vendor 2>/dev/null || true)
    product=$(cat "$SYSFS"/class/dmi/id/product_name 2>/dev/null || true)
    if [[ "$vendor" == Acer* && "$product" =~ (Nitro|Predator) ]]; then echo acer-nitro
    elif [[ "$PF_LAPTOP" == 1 ]]; then echo laptop
    else echo desktop
    fi
}

net_conflicts() {  # network stacks that would fight NetworkManager
    local s out=""
    for s in systemd-networkd connman netctl dhcpcd wicd; do
        systemctl is-active --quiet "$s.service" 2>/dev/null && out+=" $s"
    done
    # iwd alone (not as NM's backend) also conflicts with NM's wpa_supplicant
    if systemctl is-active --quiet iwd.service 2>/dev/null \
        && ! grep -rqs 'wifi.backend=iwd' /etc/NetworkManager/; then out+=" iwd"; fi
    echo "${out# }"
}

preflight() {
    say "preflight"
    local id="" like="" pretty=""
    if [[ -r /etc/os-release ]]; then
        # shellcheck disable=SC1091
        id=$(. /etc/os-release; echo "${ID:-}"); like=$(. /etc/os-release; echo "${ID_LIKE:-}")
        pretty=$(. /etc/os-release; echo "${PRETTY_NAME:-$id}")
    fi
    PF_DISTRO="$id"
    if [[ "$id" == arch ]]; then ok "distribution: $pretty"
    elif [[ " $like " == *" arch "* ]]; then
        warn "distribution: $pretty (Arch-based; untested — repositories may differ)"
        confirm "continue on an Arch derivative?" n || die "stopped at your request"
    else
        die "Riceforge needs Arch Linux (found: ${pretty:-unknown}). It does not install Arch itself; see README 'Before you start'."
    fi

    [[ $EUID -eq 0 ]] && die "run ./setup as your normal user (it uses sudo only for system steps), not as root"
    [[ -d /run/archiso || "$(cat /etc/hostname 2>/dev/null)" == archiso ]] \
        && die "this looks like the Arch live ISO; install Arch to disk first, reboot, then run ./setup as your user"
    have pacman || die "pacman not found"

    PF_ARCH=${RF_ARCH:-$(uname -m)}
    if [[ "$PF_ARCH" == x86_64 ]]; then ok "architecture: x86_64"
    else warn "architecture: $PF_ARCH — AUR *-bin packages (walker-bin) are x86_64 only; the launcher will be skipped"; fi

    PF_GRAPHICAL=0
    if [[ -n "${HYPRLAND_INSTANCE_SIGNATURE:-}" ]]; then PF_GRAPHICAL=hyprland; ok "session: inside Hyprland (changes reload live)"
    elif [[ -n "${WAYLAND_DISPLAY:-}${DISPLAY:-}" ]]; then PF_GRAPHICAL=other
        ok "session: graphical (${XDG_CURRENT_DESKTOP:-unknown}); Riceforge takes effect when you log into Hyprland"
    else ok "session: text console (log into Hyprland afterwards)"; fi

    if have sudo; then
        if sudo -n true 2>/dev/null; then ok "sudo: available"
        else ok "sudo: available (will ask for your password once)"; fi
    else
        PF_NO_SUDO=1; warn "sudo not installed: package and system steps will be skipped (pacman -S sudo, add yourself to wheel)"
    fi

    local free_home free_root
    free_home=$(df -Pm "$HOME" | awk 'NR==2{print $4}' || echo 0)
    free_root=$(df -Pm / | awk 'NR==2{print $4}' || echo 0)
    if (( free_root < 3000 )); then warn "only ${free_root} MiB free on / (the full stack needs ~2.5 GiB)"; else ok "disk: ${free_root} MiB free on /, ${free_home} MiB in \$HOME"; fi

    PF_ONLINE=0
    if [[ "${RF_ASSUME_ONLINE:-0}" == 1 ]]; then PF_ONLINE=1; ok "network: assumed online"
    elif getent hosts archlinux.org >/dev/null 2>&1 && \
       { have curl && curl -fsI --max-time 6 https://archlinux.org >/dev/null 2>&1 || ! have curl; }; then
        PF_ONLINE=1; ok "network: online"
    else warn "network: offline — packages cannot be installed (configs can still be deployed)"; fi

    PF_GPUS=$(detect_gpus); ok "gpu: ${PF_GPUS:-unknown}"
    PF_LAPTOP=0; compgen -G "$SYSFS/class/power_supply/BAT*" >/dev/null && PF_LAPTOP=1
    ok "form factor: $([[ $PF_LAPTOP == 1 ]] && echo laptop || echo desktop)"
    PF_BT=0; compgen -G "$SYSFS/class/bluetooth/hci*" >/dev/null && PF_BT=1
    ok "bluetooth adapter: $([[ $PF_BT == 1 ]] && echo present || echo none found)"
    PF_DM=$(detect_dm); ok "display manager: ${PF_DM:-none enabled}"
    PF_NET_CONFLICT=$(net_conflicts)
    [[ -n "$PF_NET_CONFLICT" ]] && warn "active network stack(s): $PF_NET_CONFLICT — Riceforge will NOT enable NetworkManager over them"

    local others=()
    for s in /usr/share/wayland-sessions/*.desktop /usr/share/xsessions/*.desktop; do
        [[ -e "$s" ]] || continue
        case "$(basename "$s")" in hyprland*.desktop) ;; *) others+=("$(basename "$s" .desktop)") ;; esac
    done
    (( ${#others[@]} )) && note "other sessions installed (left alone): ${others[*]}"

    PF_EXISTING=0
    if [[ -f "$RF_STATE_FILE" ]]; then PF_EXISTING=1; ok "existing Riceforge install found (re-running is safe; nothing is duplicated)"; fi
    if [[ -e "$RF" && "$(cd "$RF" 2>/dev/null && pwd -P)" != "$RF_SRC" ]]; then
        die "$RF exists and is not this checkout ($RF_SRC). Move it aside or run ./setup from $RF."
    fi
    return 0
}
