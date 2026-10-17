#!/usr/bin/env bash
# Theme switching, wallpaper repair, and session helpers (no duplicated
# background processes). Session tests run inside a private PID namespace with
# dummy helpers, so they can neither see nor stop the live desktop's processes.
. "$(dirname "$0")/lib.sh"
make_sandbox; trap drop_sandbox EXIT
mock_all_installed
"$SB/repo/setup" --yes --no-packages --no-system --profile desktop > "$SB/setup.out" 2>&1 \
    || { tail -20 "$SB/setup.out"; exit 1; }
RFB="$HOME/.config/riceforge/bin/riceforge"

t_begin "switch themes (no live session)"
for t in etch original nacre etch nacre; do
    RICEFORGE_NO_LIVE=1 "$RFB" apply "$t" > "$SB/apply-$t.out" 2>&1
    check "apply $t exits 0" test $? -eq 0 || tail -5 "$SB/apply-$t.out"
    check "current -> $t" test "$(readlink "$SB/repo/current")" = "themes/$t"
    bad=0
    for l in hypr/riceforge.lua hypr/hyprlock.conf waybar/config.jsonc waybar/style.css kitty/riceforge-theme.conf swaync/style.css walker/themes/riceforge; do
        [[ -e "$HOME/.config/$l" ]] || { bad=1; echo "    dangling under $t: $l"; }
    done
    check "theme links resolve under $t" test $bad -eq 0
    check "$t has a wallpaper" test -e "$HOME/.config/riceforge/current/wallpaper.png"
done
check "apply never reloaded a live session" bash -c "! grep -q 'hyprctl reload' '$MOCK/calls'"
check "apply refuses unknown theme" bash -c "! RICEFORGE_NO_LIVE=1 '$RFB' apply nosuch"
check "status reports no broken links" bash -c "! '$RFB' status | grep -q BROKEN"

t_begin "wallpaper state repair"
rm -f "$SB/repo/themes/nacre/wallpaper.png"
RICEFORGE_NO_LIVE=1 "$RFB" verify nacre > /dev/null 2>&1
check "missing wallpaper recreated from DEFAULT_WALLPAPER" test "$(readlink "$SB/repo/themes/nacre/wallpaper.png")" = wallpapers/machina-mundi.png
ln -sfn wallpapers/does-not-exist.png "$SB/repo/themes/nacre/wallpaper.png"
RICEFORGE_NO_LIVE=1 "$RFB" verify nacre > /dev/null 2>&1
check "dangling wallpaper repaired" test -e "$SB/repo/themes/nacre/wallpaper.png"
rm -f "$SB/repo/themes/etch/wallpapers/plate-iii.png" "$SB/repo/themes/etch/wallpaper.png"
RICEFORGE_NO_LIVE=1 "$RFB" verify etch > /dev/null 2>&1
check "etch without local plates falls back to a public plate" test "$(readlink "$SB/repo/themes/etch/wallpaper.png")" = ../nacre/wallpapers/selenographia.png
check "fallback plate exists in a clean checkout" test -e "$SB/repo/themes/etch/wallpaper.png"

t_begin "session helpers never duplicate processes (private PID namespace)"
# dummy long-running helpers named like the real ones
for n in nm-applet blueman-applet swaybg awww-daemon; do
    printf '#!/bin/bash\nwhile sleep 1; do :; done\n' > "$SB/bin/$n"; chmod +x "$SB/bin/$n"
done
printf '#!/bin/bash\n[[ "$1" == quit ]] && exit 0\nwhile sleep 1; do :; done\n' > "$SB/repo/shell/riceforge-shell"
chmod +x "$SB/repo/shell/riceforge-shell"
printf '#!/usr/bin/env bash\nexit 1\n' > "$SB/bin/awww"; chmod +x "$SB/bin/awww"   # no daemon reachable -> swaybg fallback
unshare -Urpf --mount-proc env -u DBUS_SESSION_BUS_ADDRESS XDG_RUNTIME_DIR="$SB" HOME="$HOME" PATH="$PATH" \
    bash -c '
    count() { pgrep -cx "$1" || true; }
    T="$HOME/.config/riceforge/themes"
    "$T/etch/session" start; "$T/etch/session" start; "$T/etch/session" start; sleep 0.3
    echo "etch nm=$(count nm-applet) bt=$(count blueman-applet) bg=$(count swaybg) rfs=$(count riceforge-shell)"
    "$T/etch/session" stop; "$T/nacre/session" start; "$T/nacre/session" start; sleep 0.3
    echo "nacre nm=$(count nm-applet) bt=$(count blueman-applet) bg=$(count swaybg) rfs=$(count riceforge-shell)"
    echo "awww-daemon=$(count awww-daemon)"
    for i in 1 2 3; do "$T/nacre/session" stop; "$T/etch/session" start; "$T/etch/session" stop; "$T/nacre/session" start; done; sleep 0.3
    echo "cycled nm=$(count nm-applet) bt=$(count blueman-applet) bg=$(count swaybg) rfs=$(count riceforge-shell)"
    "$T/nacre/session" stop; sleep 0.3
    echo "stopped nm=$(count nm-applet) bt=$(count blueman-applet) bg=$(count swaybg) rfs=$(count riceforge-shell)"
    ' > "$SB/sessions.out" 2>&1
cat "$SB/sessions.out" | sed 's/^/    /'
check "etch: one applet each + one swaybg after 3 starts" grep -qx "etch nm=1 bt=1 bg=1 rfs=0" "$SB/sessions.out"
check "nacre: applets stopped, one shell, one wallpaper" grep -qx "nacre nm=0 bt=0 bg=1 rfs=1" "$SB/sessions.out"
check "unreachable awww-daemon is not left running beside swaybg" grep -qx "awww-daemon=0" "$SB/sessions.out"
check "3 theme cycles leave exactly one of each" grep -qx "cycled nm=0 bt=0 bg=1 rfs=1" "$SB/sessions.out"
check "stop leaves no shell behind" grep -q "stopped nm=0 bt=0 bg=. rfs=0" "$SB/sessions.out"

t_end
