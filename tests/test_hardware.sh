#!/usr/bin/env bash
# Hardware profiles, feature selection, location, GPU handling, unsupported
# architectures and missing optional dependencies, on simulated machines.
. "$(dirname "$0")/lib.sh"
make_sandbox; trap drop_sandbox EXIT
export RF_SRC="$SB/repo" RF_ASSUME_ONLINE=1
. "$SB/repo/install/lib.sh"; . "$SB/repo/install/preflight.sh"
. "$SB/repo/install/dependencies.sh"; . "$SB/repo/install/user-config.sh"

fake_sys() {  # fake_sys <dir> vendor product gpu-ids... [--battery] [--bt]
    local d="$1" vendor="$2" product="$3"; shift 3
    mkdir -p "$d/class/dmi/id" "$d/class/power_supply" "$d/class/bluetooth"
    echo "$vendor" > "$d/class/dmi/id/sys_vendor"; echo "$product" > "$d/class/dmi/id/product_name"
    local i=0 a
    for a in "$@"; do
        case "$a" in
            --battery) mkdir -p "$d/class/power_supply/BAT0" ;;
            --bt) mkdir -p "$d/class/bluetooth/hci0" ;;
            *) mkdir -p "$d/class/drm/card$i/device"; echo "$a" > "$d/class/drm/card$i/device/vendor"; i=$((i+1)) ;;
        esac
    done
}

t_begin "hardware detection"
fake_sys "$SB/sys-acer" Acer "Nitro ANV15-41" 0x10de 0x1002 --battery --bt
fake_sys "$SB/sys-tower" "Micro-Star" "MS-7D25" 0x10de
fake_sys "$SB/sys-thinkpad" LENOVO "21CB" 0x8086 --battery
SYSFS="$SB/sys-acer"; PF_LAPTOP=1
check "acer hybrid gpus detected" test "$(detect_gpus)" = "nvidia amd"
check "acer nitro -> acer-nitro profile" test "$(detect_profile)" = acer-nitro
SYSFS="$SB/sys-thinkpad"; PF_LAPTOP=1
check "intel laptop -> laptop profile" test "$(detect_profile)" = laptop
check "intel gpu detected" test "$(detect_gpus)" = intel
SYSFS="$SB/sys-tower"; PF_LAPTOP=0
check "nvidia tower -> desktop profile" test "$(detect_profile)" = desktop
check "nvidia-only detected" test "$(detect_gpus)" = nvidia

t_begin "feature selection"
base="core launcher shell launcher-extras apps aesthetic"
check "+personal adds" test "$(apply_feature_spec +personal "$base")" = "core launcher shell launcher-extras apps aesthetic personal"
check "-aesthetic removes" test "$(apply_feature_spec -aesthetic "$base")" = "core launcher shell launcher-extras apps"
check "explicit list replaces, core kept" test "$(apply_feature_spec launcher,shell "$base")" = "core launcher shell"
check "core cannot be removed" test "$(apply_feature_spec -core "$base")" = "core launcher shell launcher-extras apps aesthetic"
check "duplicates collapse" test "$(apply_feature_spec +apps,+apps "$base")" = "$base"

t_begin "location from timezone"
for z in "Europe/London:51.51:-0.13" "America/New_York:40.71:-74.01" "Australia/Sydney:-33.87:151.22" "Asia/Kolkata:22.53:88.37"; do
    IFS=: read -r tz la lo <<< "$z"
    out=$(MOCK_TZ="$tz" tz_location)
    IFS=$'\t' read -r place lat lon <<< "$out"
    check "$tz -> $lat,$lon" test "$lat,$lon" = "$la,$lo"
done

t_begin "profiles end to end"
mock_all_installed
RF_SYSFS="$SB/sys-acer" "$SB/repo/setup" --yes --no-packages --no-system > "$SB/acer.out" 2>&1
check "auto profile on Acer is acer-nitro" grep -q 'PROFILE="acer-nitro"' "$HOME/.config/riceforge-local/machine.conf"
check "acer extra in local hypr.lua" grep -q 'extras/acer-nitro.lua' "$HOME/.config/riceforge-local/hypr.lua"
check "hybrid nvidia does not get nvidia env" bash -c "! grep -q extras/nvidia.lua '$HOME/.config/riceforge-local/hypr.lua'"
RF_SYSFS="$SB/sys-tower" "$SB/repo/setup" --yes --no-packages --no-system --profile desktop > "$SB/tower.out" 2>&1
check "nvidia-only machine gets nvidia env" grep -q 'extras/nvidia.lua' "$HOME/.config/riceforge-local/hypr.lua"
check "profile switch dropped acer extra" bash -c "! grep -q extras/acer-nitro.lua '$HOME/.config/riceforge-local/hypr.lua'"
"$SB/repo/setup" --yes --no-packages --no-system --profile desktop --features +personal --kb-layout de > "$SB/de.out" 2>&1
check "keyboard layout written" grep -q 'kb_layout = "de"' "$HOME/.config/riceforge-local/hypr.lua"
check "personal feature adds personal extra" grep -q 'extras/personal.lua' "$HOME/.config/riceforge-local/hypr.lua"
if command -v Hyprland >/dev/null; then
    out=$(Hyprland --verify-config -c "$HOME/.config/hypr/hyprland.lua" 2>&1 | sed -n '/Config parsing result/,$p' | tail -n +3)
    [[ "$out" == "config ok" ]] && pass "config with nvidia+personal extras and de layout verifies" || flunk "extras verify" "$out"
fi
check "fan widgets gated on the Acer driver in every theme" bash -c \
    "for f in '$SB'/repo/themes/*/waybar/config.jsonc; do [ \$(grep -c 'exec-if.*linuwu_sense\|exec-if.*fan-toggle' \$f) -eq 2 ] || exit 1; done"

t_begin "dependency handling with mocks"
FEATURES="core launcher shell launcher-extras apps aesthetic"
mock_all_installed
grep -v -x -e awww -e otf-cormorant "$MOCK/installed" > "$MOCK/i2"; mv "$MOCK/i2" "$MOCK/installed"
verify_dependencies quiet > "$SB/v1.out" 2>&1; v1=$?; cat "$SB/v1.out" | sed "s/^/    /"
check "missing optional packages warn but do not fail" test $v1 -eq 0
check "missing optional packages are named" grep -q "missing aesthetic package: awww" "$SB/v1.out"
grep -v -x walker-bin "$MOCK/installed" > "$MOCK/i2"; mv "$MOCK/i2" "$MOCK/installed"
verify_dependencies quiet > "$SB/v2.out" 2>&1
check "missing required package fails" test $? -ne 0
check "missing required package is named" grep -q "missing required package: walker-bin" "$SB/v2.out"

: > "$MOCK/calls"; mock_all_installed
"$SB/repo/setup" --yes --no-system --profile desktop > "$SB/p1.out" 2>&1
check "nothing reinstalled when everything is present" bash -c "! grep -qE 'pacman -S|pacman -Syu' '$MOCK/calls'"
grep -v -x -e awww -e otf-cormorant -e walker-bin "$MOCK/installed" > "$MOCK/i2"; mv "$MOCK/i2" "$MOCK/installed"
: > "$MOCK/calls"
"$SB/repo/setup" --yes --no-system --profile desktop --aur-helper none > "$SB/p2.out" 2>&1
check "pacman installs only the missing official packages" grep -qE '^pacman -Syu --needed --noconfirm (awww otf-cormorant|otf-cormorant awww)$' "$MOCK/calls"
check "AUR skipped without a helper (warned, not failed)" grep -q "AUR packages not installed: walker-bin" "$SB/p2.out"
check "no AUR helper was assumed" bash -c "! grep -qE '^(yay|paru) ' '$MOCK/calls'"
grep -q "^pkg	awww" "$HOME/.local/state/riceforge/installed.tsv" && pass "installed packages recorded for uninstall" || flunk "installed packages recorded"
sed -i '/^otf-cormorant$/d' "$MOCK/repo"; sed -i '/^otf-cormorant$/d' "$MOCK/installed"
"$SB/repo/setup" --yes --no-system --profile desktop --aur-helper none > "$SB/p3.out" 2>&1
check "renamed/unavailable package skipped with a warning" grep -q "not in your repositories (skipped): otf-cormorant" "$SB/p3.out"
RF_ARCH=aarch64 "$SB/repo/setup" --yes --no-system --profile desktop --aur-helper none > "$SB/p4.out" 2>&1
check "aarch64: -bin AUR packages are skipped" bash -c "grep -q 'x86_64 only' '$SB/p4.out' && ! grep -q 'AUR packages not installed: .*walker-bin' '$SB/p4.out'"

t_end
