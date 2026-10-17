#!/usr/bin/env bash
# Installer behaviour in a sandbox: dry run, first install, rerun idempotence,
# backups of pre-existing files, seeds, local layer, uninstall and restore.
. "$(dirname "$0")/lib.sh"
make_sandbox; trap drop_sandbox EXIT
mock_all_installed
S="$SB/repo/setup"
FLAGS=(--yes --no-packages --no-system --profile laptop)

# a user's pre-existing desktop: plain files that setup must back up, plus unrelated ones
mkdir -p "$HOME/.config/hypr/hyprlua" "$HOME/.config/kitty" "$HOME/.config/waybar" "$HOME/.config/unrelated"
echo "-- my old hyprland.lua" > "$HOME/.config/hypr/hyprland.lua"
echo "-- old module" > "$HOME/.config/hypr/hyprlua/keybinds.lua"
echo "font_size 99" > "$HOME/.config/kitty/kitty.conf"
echo '{"old": true}' > "$HOME/.config/waybar/config.jsonc"
echo "keep me" > "$HOME/.config/unrelated/file"
mkdir -p "$HOME/.config/hypr/custom"; echo "-- my binds" > "$HOME/.config/hypr/custom/keybinds.lua"

t_begin "dry run changes nothing"
before=$(home_snapshot)
"$S" --dry-run "${FLAGS[@]}" > "$SB/dry.out" 2>&1; rc=$?
check "dry run exits 0" test $rc -eq 0
check "dry run prints the plan" grep -q "files:" "$SB/dry.out"
check "dry run lists backups" grep -q "backup: ~/.config/hypr/hyprland.lua" "$SB/dry.out"
after=$(home_snapshot)
[[ "$before" == "$after" ]] && pass "home untouched by dry run" || flunk "home untouched by dry run" "$(diff <(echo "$before") <(echo "$after") | head -5)"
check "no repo link created in dry run" test ! -e "$HOME/.config/riceforge"

t_begin "first install"
"$S" "${FLAGS[@]}" > "$SB/run1.out" 2>&1; rc=$?
check "setup exits 0" test $rc -eq 0 || tail -20 "$SB/run1.out"
check "~/.config/riceforge links to the checkout" test "$(readlink -f "$HOME/.config/riceforge")" = "$SB/repo"
bad=0
while IFS=$'\t' read -r mode src dst; do
    [[ "$mode" == link ]] || continue
    [[ -L "$HOME/$dst" && -e "$HOME/$dst" && "$(readlink "$HOME/$dst")" == "$HOME/.config/riceforge/$src" ]] || { bad=1; echo "    bad: $dst"; }
done < <(grep -v -e '^\s*#' -e '^\s*$' "$SB/repo/manifests/deploy.tsv")
check "every link resolves to the repo" test $bad -eq 0
check "default theme is nacre" test "$(readlink "$SB/repo/current")" = themes/nacre
check "theme wallpaper created" test -e "$SB/repo/themes/nacre/wallpaper.png"
check "walker layout rendered without placeholders" bash -c "! grep -q '@RF' '$SB/repo/themes/nacre/walker/layout.xml'"
check "rendered layout uses this HOME" grep -q "$HOME/.config/riceforge/current/icons" "$SB/repo/themes/nacre/walker/layout.xml"
check "unrelated file kept" grep -qx "keep me" "$HOME/.config/unrelated/file"
check "user's custom keybinds kept (seed never overwrites)" grep -qx -- "-- my binds" "$HOME/.config/hypr/custom/keybinds.lua"
check "missing custom files seeded" test -f "$HOME/.config/hypr/custom/rules.lua"
bk=$(ls -d "$HOME/.local/state/riceforge/backups/"*/ | head -1)
check "old hyprland.lua backed up" grep -q "my old hyprland.lua" "$bk/.config/hypr/hyprland.lua"
check "old hyprlua dir backed up" grep -q "old module" "$bk/.config/hypr/hyprlua/keybinds.lua"
check "old kitty.conf backed up" grep -q "font_size 99" "$bk/.config/kitty/kitty.conf"
check "machine.conf written" grep -q 'PROFILE="laptop"' "$HOME/.config/riceforge-local/machine.conf"
check "local hypr.lua has managed block" grep -q ">>> riceforge" "$HOME/.config/riceforge-local/hypr.lua"
check "shell.toml location from timezone (London)" grep -q 'lat = 51.51' "$HOME/.config/riceforge-local/shell.toml"
check "gsettings dark preference set" grep -q "color-scheme=prefer-dark" "$MOCK/gsettings"
check "no pacman install attempted (--no-packages)" bash -c "! grep -q 'pacman -S' '$MOCK/calls'"
check "no system service touched (--no-system)" bash -c "! grep -q 'systemctl enable' '$MOCK/calls'"
check "riceforge on ~/.local/bin" test -x "$HOME/.local/bin/riceforge"

t_begin "rerun is idempotent"
state1=$(cat "$HOME/.local/state/riceforge/installed.tsv")
snap1=$(home_snapshot | grep -v '/backups/')
echo "-- my monitor" >> "$HOME/.config/riceforge-local/hypr.lua"
"$S" "${FLAGS[@]}" > "$SB/run2.out" 2>&1; rc=$?
check "second run exits 0" test $rc -eq 0
check "second run changes no entries" grep -q "(0 changed)" "$SB/run2.out"
state2=$(cat "$HOME/.local/state/riceforge/installed.tsv")
[[ "$(echo "$state1" | grep -v '^setup')" == "$(echo "$state2" | grep -v '^setup')" ]] && pass "install record unchanged" || flunk "install record unchanged" "$(diff <(echo "$state1") <(echo "$state2") | head)"
check "managed block appears once" test "$(grep -c '>>> riceforge' "$HOME/.config/riceforge-local/hypr.lua")" -eq 1
check "user line in local hypr.lua kept" grep -qx -- "-- my monitor" "$HOME/.config/riceforge-local/hypr.lua"
check "no new backup dir with content" test "$(find "$HOME/.local/state/riceforge/backups" -mindepth 1 -maxdepth 1 -type d | wc -l)" -eq 1
check "kitty theme include not duplicated" test "$(grep -c "globinclude riceforge" "$HOME/.config/kitty/kitty.conf")" -eq 1
"$S" "${FLAGS[@]}" --profile acer-nitro > "$SB/run3.out" 2>&1
check "profile change rewrites only the block" test "$(grep -c '>>> riceforge' "$HOME/.config/riceforge-local/hypr.lua")" -eq 1
check "acer extra now loaded" grep -q 'extras/acer-nitro.lua' "$HOME/.config/riceforge-local/hypr.lua"
check "user line survives profile change" grep -qx -- "-- my monitor" "$HOME/.config/riceforge-local/hypr.lua"

t_begin "hyprland accepts the deployed config"
if command -v Hyprland >/dev/null; then
    out=$(Hyprland --verify-config -c "$HOME/.config/hypr/hyprland.lua" 2>&1 | sed -n '/Config parsing result/,$p' | tail -n +3)
    [[ "$out" == "config ok" ]] && pass "full config verifies in the sandbox HOME" || flunk "full config verifies" "$out"
else
    pass "(Hyprland not installed; skipped)"
fi

t_begin "uninstall"
echo "edited" >> "$HOME/.config/hypr/custom/rules.lua"
"$SB/repo/install/uninstall.sh" --dry-run > "$SB/un-dry.out" 2>&1
check "uninstall dry run keeps links" test -L "$HOME/.config/hypr/hyprland.lua"
"$SB/repo/install/uninstall.sh" --yes --purge-seeds > "$SB/un.out" 2>&1; rc=$?
check "uninstall exits 0" test $rc -eq 0 || tail "$SB/un.out"
check "hyprland.lua restored" grep -q "my old hyprland.lua" "$HOME/.config/hypr/hyprland.lua"
check "hyprlua dir restored" grep -q "old module" "$HOME/.config/hypr/hyprlua/keybinds.lua"
check "kitty.conf restored" grep -q "font_size 99" "$HOME/.config/kitty/kitty.conf"
check "waybar config restored" grep -q '"old": true' "$HOME/.config/waybar/config.jsonc"
check "links without a backup removed" test ! -e "$HOME/.config/hypr/hypridle.conf"
check "unrelated file still there" grep -qx "keep me" "$HOME/.config/unrelated/file"
check "edited seed kept" grep -q edited "$HOME/.config/hypr/custom/rules.lua"
check "unedited seed purged" test ! -e "$HOME/.config/hypr/custom/env.lua"
check "user's own custom file kept" grep -qx -- "-- my binds" "$HOME/.config/hypr/custom/keybinds.lua"
check "machine layer kept" test -f "$HOME/.config/riceforge-local/machine.conf"
check "repo link removed" test ! -e "$HOME/.config/riceforge"
check "gsettings restored" bash -c "tail -1 '$MOCK/gsettings' | grep -q default"
left=$(find "$HOME" -type l -lname "*riceforge*" | grep -v riceforge-local)
[[ -z "$left" ]] && pass "no Riceforge links left" || flunk "no Riceforge links left" "$left"

t_begin "reinstall after uninstall, then restore command"
"$S" "${FLAGS[@]}" > "$SB/run4.out" 2>&1
check "reinstall exits 0" test $? -eq 0
check "reinstall backed up the restored files again" test "$(find "$HOME/.local/state/riceforge/backups" -mindepth 1 -maxdepth 1 -type d | wc -l)" -ge 2

t_end
