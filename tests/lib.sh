# Test helpers. Every test runs against a throwaway copy of the repo and a fake
# $HOME, with pacman/sudo/systemctl/gsettings/hyprctl replaced by recording mocks,
# and with the Hyprland/Wayland session variables removed, so nothing here can
# touch the live desktop, system services or packages.
# shellcheck shell=bash
set -uo pipefail
REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd -P)"
PASS=0; FAILED=0; CURRENT_TEST=""

t_begin() { CURRENT_TEST="$1"; printf '\n── %s\n' "$1"; }
pass() { PASS=$((PASS+1)); printf '  ok    %s\n' "$1"; }
flunk() { FAILED=$((FAILED+1)); printf '  FAIL  %s\n' "$1"; [[ -n "${2:-}" ]] && printf '        %s\n' "$2"; return 0; }
check() {  # check "name" cmd...
    local name="$1"; shift
    if "$@" >/dev/null 2>&1; then pass "$name"; else flunk "$name" "command: $*"; fi
}
t_end() {
    printf '\n%d passed, %d failed\n' "$PASS" "$FAILED"
    (( FAILED == 0 ))
}

# sandbox: SB/{repo,home,mock,bin}; exports HOME, RF_SRC, PATH with mocks first
make_sandbox() {
    SB=$(mktemp -d "${TMPDIR:-/tmp}/riceforge-test.XXXXXX")
    mkdir -p "$SB/home" "$SB/mock" "$SB/bin"
    # copy the working tree (including untracked local plates) without .git/current
    rsync -a --exclude .git --exclude current --exclude backups --exclude '__pycache__' \
        --exclude 'themes/*/wallpaper.png' --exclude tests/.sandbox "$REPO/" "$SB/repo/"
    unset HYPRLAND_INSTANCE_SIGNATURE WAYLAND_DISPLAY DISPLAY XDG_STATE_HOME RF_LOG RF_SRC RF_STAMP
    export HOME="$SB/home" MOCK="$SB/mock" XDG_CONFIG_HOME="$SB/home/.config"
    export PATH="$SB/bin:$PATH"
    : > "$MOCK/installed"; : > "$MOCK/repo"; : > "$MOCK/calls"; : > "$MOCK/enabled"
    write_mocks
}
drop_sandbox() { [[ -n "${SB:-}" && "$SB" == */riceforge-test.* ]] && rm -rf "$SB"; }

write_mocks() {
    cat > "$SB/bin/pacman" <<'EOF'
#!/usr/bin/env bash
echo "pacman $*" >> "$MOCK/calls"
case "$1" in
  -T) shift; for p in "$@"; do grep -qx "$p" "$MOCK/installed" || { echo "$p"; exit 127; }; done; exit 0 ;;
  -Si) grep -qx "$2" "$MOCK/repo" ;;
  -Qq) grep -qx "$2" "$MOCK/installed" ;;
  -S|-Syu) shift; for p in "$@"; do [[ "$p" == -* ]] || echo "$p" >> "$MOCK/installed"; done ;;
  -Rns) exit 0 ;;
  *) exit 0 ;;
esac
EOF
    cat > "$SB/bin/sudo" <<'EOF'
#!/usr/bin/env bash
[[ "$1" == -n ]] && { shift; [[ "$1" == true ]] && exit 0; }
echo "sudo $*" >> "$MOCK/calls"; exec "$@"
EOF
    cat > "$SB/bin/systemctl" <<'EOF'
#!/usr/bin/env bash
echo "systemctl $*" >> "$MOCK/calls"
args=("$@"); [[ "${args[0]}" == --user ]] && args=("${args[@]:1}")
case "${args[0]}" in
  is-enabled) grep -qx "${args[-1]}" "$MOCK/enabled" ;;
  is-active) grep -qx "${args[-1]}" "$MOCK/enabled" ;;
  enable) echo "${args[-1]}" >> "$MOCK/enabled" ;;
  show) echo "${MOCK_TZ:-Europe/London}" ;;
  *) exit 0 ;;
esac
EOF
    cat > "$SB/bin/timedatectl" <<'EOF'
#!/usr/bin/env bash
echo "${MOCK_TZ:-Europe/London}"
EOF
    cat > "$SB/bin/gsettings" <<'EOF'
#!/usr/bin/env bash
f="$MOCK/gsettings"; touch "$f"
case "$1" in
  get) v=$(awk -F= -v k="$3" '$1==k {v=$2} END {print v}' "$f"); echo "'${v:-default}'" ;;
  set) echo "$3=$4" >> "$f" ;;
esac
EOF
    for c in hyprctl swaync-client notify-send xdg-user-dirs-update localectl; do
        printf '#!/usr/bin/env bash\necho "%s $*" >> "$MOCK/calls"\n' "$c" > "$SB/bin/$c"
    done
    chmod +x "$SB"/bin/*
}

# all packages from the manifest are "installed" / "in repos"
mock_all_installed() { grep -v '^#' "$SB/repo/manifests/packages.tsv" | awk -F'\t' 'NF>1 {print $1}' > "$MOCK/installed"; cp "$MOCK/installed" "$MOCK/repo"; }

# snapshot of everything under $HOME: path, type, link target or checksum
home_snapshot() {
    (cd "$HOME" && find . -mindepth 1 -not -path './.local/state/riceforge/logs*' -printf '%p %y %l\n' | sort | while read -r p t l; do
        if [[ "$t" == f ]]; then echo "$p f $(sha256sum "$p" | cut -c1-16)"; else echo "$p $t $l"; fi
    done)
}
