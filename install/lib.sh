# Riceforge installer library: sourced by ./setup, install/*.sh and bin/riceforge.
# Provides logging, a dry-run aware `run`, backups and the install-state manifest.
# shellcheck shell=bash

RF_SRC="${RF_SRC:-$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd -P)}"
RF="$HOME/.config/riceforge"                      # canonical path every config uses
RF_LOCAL="$HOME/.config/riceforge-local"          # machine-specific, never tracked
RF_STATE="${XDG_STATE_HOME:-$HOME/.local/state}/riceforge"
RF_STATE_FILE="$RF_STATE/installed.tsv"           # kind  target  backup  detail
RF_STAMP="${RF_STAMP:-$(date +%Y%m%d-%H%M%S)}"
RF_BACKUP="$RF_STATE/backups/$RF_STAMP"
RF_LOG="${RF_LOG:-}"
DRY_RUN="${DRY_RUN:-0}"
ASSUME_YES="${ASSUME_YES:-0}"

if [[ -t 1 ]]; then
    c_acc=$'\e[38;2;179;154;94m'; c_dim=$'\e[38;2;110;106;100m'; c_bad=$'\e[38;2;168;70;79m'
    c_ok=$'\e[38;2;185;188;194m'; c_off=$'\e[0m'
else
    c_acc=; c_dim=; c_bad=; c_ok=; c_off=
fi

_log() { [[ -n "$RF_LOG" ]] && printf '%s %s\n' "$(date +%H:%M:%S)" "$*" >> "$RF_LOG"; return 0; }
say()   { printf '%s☉%s %s\n' "$c_acc" "$c_off" "$*"; _log "== $*"; }
note()  { printf '  %s%s%s\n' "$c_dim" "$*" "$c_off"; _log "   $*"; }
ok()    { printf '  %s✓%s %s\n' "$c_ok" "$c_off" "$*"; _log "ok $*"; }
warn()  { printf '  %s!%s %s\n' "$c_bad" "$c_off" "$*" >&2; _log "!! $*"; }
die()   { printf '%s✗ error:%s %s\n' "$c_bad" "$c_off" "$*" >&2; _log "ERROR $*"
          [[ -n "$RF_LOG" ]] && printf '  log: %s\n' "$RF_LOG" >&2; exit 1; }

start_log() {  # $1 = name
    [[ "$DRY_RUN" == 1 ]] && return 0
    mkdir -p "$RF_STATE/logs"
    RF_LOG="$RF_STATE/logs/$1-$RF_STAMP.log"
    export RF_LOG
    _log "riceforge $1 started (src=$RF_SRC)"
}

# run <cmd...>: execute, or only print under --dry-run. Failures are logged.
run() {
    if [[ "$DRY_RUN" == 1 ]]; then
        printf '  %s[dry-run]%s %s\n' "$c_dim" "$c_off" "$(printf '%q ' "$@")"
        return 0
    fi
    _log "\$ $(printf '%q ' "$@")"
    "$@"
}

# run_root <cmd...>: as root via sudo (never used for files under $HOME)
run_root() {
    if [[ $EUID -eq 0 ]]; then run "$@"; else run sudo "$@"; fi
}

confirm() {  # confirm "question" [default y|n]
    local q="$1" def="${2:-y}" a
    [[ "$ASSUME_YES" == 1 ]] && return 0
    [[ "$DRY_RUN" == 1 ]] && { note "(dry-run) would ask: $q"; return 0; }
    [[ -t 0 ]] || { [[ "$def" == y ]]; return; }
    local hint="[Y/n]"; [[ "$def" == n ]] && hint="[y/N]"
    read -r -p "  $q $hint " a || a=""
    a="${a:-$def}"
    [[ "$a" =~ ^[Yy] ]]
}

# ask "question" default -> echoes the answer
ask() {
    local q="$1" def="$2" a
    if [[ "$ASSUME_YES" == 1 || "$DRY_RUN" == 1 || ! -t 0 ]]; then echo "$def"; return; fi
    read -r -p "  $q [$def] " a || a=""
    echo "${a:-$def}"
}

have() { command -v "$1" >/dev/null 2>&1; }

# manifest readers: strip comments/blank lines, keep TAB columns
manifest_rows() { grep -v -e '^\s*#' -e '^\s*$' "$RF_SRC/manifests/$1"; }

# ── install state ──────────────────────────────────────────────────────────────
# One line per thing Riceforge did, newest wins for a given kind+target.
state_get() {  # kind target -> prints "backup<TAB>detail" of the latest record
    [[ -f "$RF_STATE_FILE" ]] || return 1
    awk -F'\t' -v k="$1" -v t="$2" '$1==k && $2==t {line=$3"\t"$4} END {if (line!="") print line; else exit 1}' "$RF_STATE_FILE"
}
state_put() {  # kind target backup detail
    [[ "$DRY_RUN" == 1 ]] && return 0
    mkdir -p "$RF_STATE"
    local tmp="$RF_STATE_FILE.tmp"
    { [[ -f "$RF_STATE_FILE" ]] && awk -F'\t' -v k="$1" -v t="$2" '!($1==k && $2==t)' "$RF_STATE_FILE"
      printf '%s\t%s\t%s\t%s\n' "$1" "$2" "${3:--}" "${4:--}"; } > "$tmp"
    mv "$tmp" "$RF_STATE_FILE"
}
state_del() {  # kind target
    [[ "$DRY_RUN" == 1 || ! -f "$RF_STATE_FILE" ]] && return 0
    local tmp="$RF_STATE_FILE.tmp"
    awk -F'\t' -v k="$1" -v t="$2" '!($1==k && $2==t)' "$RF_STATE_FILE" > "$tmp"
    mv "$tmp" "$RF_STATE_FILE"
}
state_rows() {  # [kind] -> rows
    [[ -f "$RF_STATE_FILE" ]] || return 0
    if [[ -n "${1:-}" ]]; then awk -F'\t' -v k="$1" '$1==k' "$RF_STATE_FILE"; else cat "$RF_STATE_FILE"; fi
}

# backup_move <abs path>: move an existing file/dir/link into this run's backup,
# preserving its path below $HOME. Echoes the backup path.
backup_move() {
    local src="$1" rel dest
    rel="${src#"$HOME"/}"
    dest="$RF_BACKUP/$rel"
    if [[ "$DRY_RUN" == 1 ]]; then echo "$dest"; return 0; fi
    mkdir -p "$(dirname "$dest")"
    mv -- "$src" "$dest"
    _log "backup $src -> $dest"
    echo "$dest"
}

sha() { sha256sum "$1" 2>/dev/null | cut -d' ' -f1; }

# ── machine config ─────────────────────────────────────────────────────────────
load_machine() {
    PROFILE="" FEATURES="" HYPR_EXTRAS="" KB_LAYOUT="" AUR_HELPER=""
    # shellcheck disable=SC1091
    [[ -r "$RF_LOCAL/machine.conf" ]] && . "$RF_LOCAL/machine.conf"
    return 0
}
feature_on() { [[ " $FEATURES " == *" $1 "* ]]; }

# apply_feature_spec <spec> <base>: "+a,-b" edits base; "a,b" replaces it; core always stays
apply_feature_spec() {  # $1 spec, $2 base
    local spec="$1" out=" $2 " item
    if [[ "$spec" != *[+-]* ]]; then out=" ${spec//,/ } "
    else
        IFS=, read -ra items <<< "$spec"
        for item in "${items[@]}"; do
            case "$item" in
                +*) out+="${item#+} " ;;
                -*) out="${out// ${item#-} / }" ;;
            esac
        done
    fi
    [[ "$out" == *" core "* ]] || out=" core$out"
    echo "$out" | tr ' ' '\n' | awk 'NF && !s[$0]++' | tr '\n' ' ' | sed 's/ $//'
}


# ── theme runtime helpers (shared with bin/riceforge) ─────────────────────────
# render_templates: themes/**/X.in -> X with @RF@, @RF_CURRENT@, @HOME@ filled in
render_templates() {
    local t out
    while IFS= read -r -d '' t; do
        out="${t%.in}"
        if [[ "$DRY_RUN" == 1 ]]; then note "would render ${out#"$RF_SRC"/}"; continue; fi
        sed -e "s|@RF_CURRENT@|$RF/current|g" -e "s|@RF@|$RF|g" -e "s|@HOME@|$HOME|g" "$t" > "$out.tmp"
        mv "$out.tmp" "$out"
    done < <(find "$RF_SRC/themes" -name '*.in' -type f -print0)
}

# ensure_wallpaper <theme>: themes/<t>/wallpaper.png is per-machine state (the
# plate archive re-points it). Create or repair it from DEFAULT_WALLPAPER.
ensure_wallpaper() {
    local d="$RF_SRC/themes/$1" cand DEFAULT_WALLPAPER=""
    [[ -e "$d/wallpaper.png" ]] && return 0
    # shellcheck disable=SC1091
    DEFAULT_WALLPAPER=$(. "$d/theme.env" 2>/dev/null; echo "${DEFAULT_WALLPAPER:-}")
    for cand in $DEFAULT_WALLPAPER; do
        if [[ -f "$d/$cand" ]]; then
            run ln -sfn "$cand" "$d/wallpaper.png"
            return 0
        fi
    done
    warn "theme $1: no wallpaper available (DEFAULT_WALLPAPER=$DEFAULT_WALLPAPER)"
    return 1
}
