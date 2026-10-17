# Dependencies: install the packages manifests/packages.tsv lists for the selected
# features. Repo packages go through pacman; AUR packages only through a helper you
# have (or explicitly agree to bootstrap). Nothing already satisfied is reinstalled.
# shellcheck shell=bash

# packages_for <source> -> package names for selected FEATURES
packages_for() {
    local src="$1" pkg s feat _
    while IFS=$'\t' read -r pkg s feat _; do
        [[ "$s" == "$src" ]] || continue
        feature_on "$feat" || continue
        echo "$pkg"
    done < <(manifest_rows packages.tsv)
}

# satisfied <pkg>: installed, or provided by something installed (blueman-git -> blueman)
satisfied() { pacman -T "$1" >/dev/null 2>&1; }

detect_aur_helper() {
    if [[ -n "${AUR_HELPER:-}" ]]; then
        [[ "$AUR_HELPER" == none ]] && { echo none; return; }
        have "$AUR_HELPER" && { echo "$AUR_HELPER"; return; }
        warn "configured AUR helper '$AUR_HELPER' is not installed"
    fi
    local h
    for h in paru yay pikaur aura trizen; do have "$h" && { echo "$h"; return; }; done
    echo ""
}

# bootstrap_helper <paru|yay>: build <name>-bin from the AUR with makepkg (asks first)
bootstrap_helper() {
    local name="$1" dir
    confirm "build and install $name-bin from the AUR now (needs base-devel and git)?" n || return 1
    run_root pacman -S --needed --noconfirm base-devel git || return 1
    dir=$(mktemp -d)
    run git clone --depth 1 "https://aur.archlinux.org/$name-bin.git" "$dir/$name-bin" || return 1
    ( cd "$dir/$name-bin" && run makepkg -si --noconfirm ) || return 1
    rm -rf "$dir"
    have "$name"
}

choose_aur_helper() {
    local h; h=$(detect_aur_helper)
    if [[ -n "$h" ]]; then AUR_HELPER="$h"; return 0; fi
    warn "no AUR helper found. AUR packages: $(packages_for aur | tr '\n' ' ')"
    note "Without them the desktop works, but Walker (SUPER launcher) and its providers are missing."
    if [[ "$ASSUME_YES" == 1 || ! -t 0 ]]; then
        note "non-interactive: skipping AUR (re-run with --aur-helper paru|yay to bootstrap one)"
        AUR_HELPER=none; return 0
    fi
    local a; a=$(ask "bootstrap an AUR helper? (paru / yay / none)" none)
    case "$a" in
        paru|yay) if bootstrap_helper "$a"; then AUR_HELPER="$a"; else warn "bootstrap failed; skipping AUR"; AUR_HELPER=none; fi ;;
        *) AUR_HELPER=none ;;
    esac
}

install_dependencies() {
    say "dependencies"
    [[ "${PF_NO_SUDO:-0}" == 1 ]] && { warn "no sudo: skipping package installation"; return 0; }

    local repo=() missing=() unavailable=() p
    mapfile -t repo < <(packages_for repo)
    for p in "${repo[@]}"; do satisfied "$p" || missing+=("$p"); done
    if (( ${#missing[@]} )); then
        [[ "${PF_ONLINE:-1}" == 1 ]] || die "offline, and these packages are missing: ${missing[*]}"
        # skip names the sync databases don't know (renamed, dropped, other arch)
        local avail=()
        for p in "${missing[@]}"; do
            if pacman -Si "$p" >/dev/null 2>&1; then avail+=("$p"); else unavailable+=("$p"); fi
        done
        (( ${#unavailable[@]} )) && warn "not in your repositories (skipped): ${unavailable[*]} — see manifests/packages.tsv alternatives"
        if (( ${#avail[@]} )); then
            note "official packages to install (${#avail[@]}): ${avail[*]}"
            note "pacman -Syu also brings the system up to date (Arch does not support partial upgrades)"
            if confirm "install them with pacman?"; then
                local flags=(-Syu --needed); [[ "$ASSUME_YES" == 1 ]] && flags+=(--noconfirm)
                run_root pacman "${flags[@]}" "${avail[@]}" || die "pacman failed; nothing after this step was changed"
                for p in "${avail[@]}"; do state_put pkg "$p" - repo; done
            else
                warn "skipped official packages; the desktop will be incomplete"
            fi
        fi
    else
        ok "all ${#repo[@]} official packages already satisfied"
    fi

    local aur=() amiss=()
    mapfile -t aur < <(packages_for aur)
    for p in "${aur[@]}"; do satisfied "$p" || amiss+=("$p"); done
    if [[ "$PF_ARCH" != x86_64 ]]; then
        local keep=(); for p in "${amiss[@]}"; do [[ "$p" == *-bin ]] && unavailable+=("$p") || keep+=("$p"); done
        amiss=("${keep[@]}")
    fi
    if (( ${#amiss[@]} )); then
        choose_aur_helper
        if [[ "$AUR_HELPER" == none ]]; then
            warn "AUR packages not installed: ${amiss[*]}"
        else
            note "AUR packages via $AUR_HELPER (${#amiss[@]}): ${amiss[*]}"
            note "AUR packages are user-submitted; review PKGBUILDs when $AUR_HELPER shows them"
            if confirm "install them with $AUR_HELPER?"; then
                local aflags=(-S --needed); [[ "$ASSUME_YES" == 1 ]] && aflags+=(--noconfirm)
                if run "$AUR_HELPER" "${aflags[@]}" "${amiss[@]}"; then
                    for p in "${amiss[@]}"; do state_put pkg "$p" - aur; done
                else
                    warn "$AUR_HELPER reported a failure; run 'riceforge doctor' to see what is missing"
                fi
            fi
        fi
    else
        ok "all ${#aur[@]} AUR packages already satisfied"
    fi
    [[ "$DRY_RUN" == 1 ]] && return 0
    # report, don't stop: the configs are still worth deploying; doctor repeats this
    verify_dependencies || warn "some required packages are missing; the desktop will be incomplete until they are installed"
    return 0
}

# verify_dependencies [quiet]: every selected package satisfied, every command present
verify_dependencies() {
    local pkg s feat tier cmds _ bad=0 c
    while IFS=$'\t' read -r pkg s feat tier cmds _; do
        feature_on "$feat" || continue
        if ! satisfied "$pkg"; then
            if [[ "$tier" == 1 ]]; then warn "missing required package: $pkg ($s)"; bad=1
            else warn "missing $feat package: $pkg ($s)"; fi
            continue
        fi
        [[ "$cmds" == - ]] && continue
        IFS=, read -ra cl <<< "$cmds"
        for c in "${cl[@]}"; do
            have "$c" && continue
            warn "$pkg installed but '$c' not on PATH"; [[ "$tier" == 1 ]] && bad=1
        done
    done < <(manifest_rows packages.tsv)
    (( bad )) && return 1
    [[ "${1:-}" == quiet ]] || ok "selected packages and their commands are present"
    return 0
}
