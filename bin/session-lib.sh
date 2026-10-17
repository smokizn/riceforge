# riceforge session helpers, sourced by themes/<t>/session.
# Every helper is idempotent: starting something already running is a no-op,
# so repeated theme switches never stack duplicate processes.

RF="$HOME/.config/riceforge"
CURRENT="$RF/current"

# start_once <process-name> <command...>
start_once() {
    local name="$1"; shift
    pgrep -x "$name" >/dev/null && return 0
    command -v "$1" >/dev/null 2>&1 || [[ -x "$1" ]] || return 0
    setsid -f "$@" >/dev/null 2>&1
}

# stop_all <process-name...>: TERM, then wait briefly so a following start is clean
stop_all() {
    local n
    for n in "$@"; do pkill -x "$n" 2>/dev/null || true; done
    for _ in $(seq 30); do
        local alive=0
        for n in "$@"; do pgrep -x "$n" >/dev/null && alive=1; done
        (( alive )) || return 0
        sleep 0.1
    done
}

# the classic wallpaper path: one swaybg showing current/wallpaper.png
wallpaper_swaybg() {
    stop_all swaybg
    setsid -f swaybg -m fill -i "$CURRENT/wallpaper.png" >/dev/null 2>&1
}

# applets the original setup ran from autostart
applets_start() {
    start_once nm-applet nm-applet
    start_once blueman-applet blueman-applet
}
applets_stop() {
    stop_all nm-applet blueman-applet blueman-tray
}
