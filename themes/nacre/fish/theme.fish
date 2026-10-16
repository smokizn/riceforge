# NACRE · fish layer
# Sourced by ~/.config/fish/conf.d/riceforge.fish only while nacre is the
# active riceforge theme. Everything here is session-scoped (set -g,
# function definitions): nothing is written to universal variables, so
# other themes get stock fish back.
#
# Prompt anatomy
#
#     ╭ chips: [ dir ] [  branch +2 ~1 ⇡1 ]          right:  3.2s  [ ✕ 1 ]
#     ╰ ❯
#
# Past prompts collapse (fish_transient_prompt) to   "dirname ❯ command"
# so scrollback stays quiet. One `git status` per prompt, nothing else forks.

# ── palette ─────────────────────────────────────────────────────────
set -g __nacre_text     d4d4dc
set -g __nacre_bright   e2e2e8
set -g __nacre_silver   aeb0bc
set -g __nacre_mist     777a88
set -g __nacre_dim      4d505c
set -g __nacre_lavender a39cc4
set -g __nacre_lavlight b0a9cc
set -g __nacre_steel    8ea6bf
set -g __nacre_celadon  8db5a2
set -g __nacre_wheat    cdbf98
set -g __nacre_rose     c4919d
set -g __nacre_roselight d4a5af
# chip surfaces: opaque, a shade above the glass so they read as inlaid tiles
set -g __nacre_chip_dir  24252c
set -g __nacre_chip_git  2a2837
set -g __nacre_chip_env  222a33
set -g __nacre_chip_err  36262c
set -g __nacre_chip_ssh  2b2a27

# glyphs (Nerd Font private-use codepoints)
set -g __nacre_cap_l   
set -g __nacre_cap_r   
set -g __nacre_i_home  
set -g __nacre_i_dir   
set -g __nacre_i_lock  
set -g __nacre_i_git   
set -g __nacre_i_py    
set -g __nacre_i_time  
set -g __nacre_i_jobs  
set -g __nacre_i_ssh   

# ── syntax colours ──────────────────────────────────────────────────
set -g fish_color_normal          $__nacre_text
set -g fish_color_command         $__nacre_lavlight
set -g fish_color_keyword         $__nacre_steel
set -g fish_color_param           $__nacre_silver
set -g fish_color_option          $__nacre_silver
set -g fish_color_quote           $__nacre_celadon
set -g fish_color_redirection     $__nacre_steel
set -g fish_color_end             $__nacre_mist
set -g fish_color_operator        $__nacre_steel
set -g fish_color_escape          $__nacre_wheat
set -g fish_color_comment         5f6270 --italics
set -g fish_color_error           $__nacre_rose
set -g fish_color_autosuggestion  $__nacre_dim
set -g fish_color_valid_path      --underline
set -g fish_color_cancel          $__nacre_rose
set -g fish_color_search_match    --background=2f2c3d
set -g fish_color_selection       $__nacre_bright --background=3b3850
set -g fish_color_history_current --bold
set -g fish_pager_color_prefix              $__nacre_lavender --bold
set -g fish_pager_color_completion          $__nacre_silver
set -g fish_pager_color_description         $__nacre_mist --italics
set -g fish_pager_color_progress            $__nacre_mist
set -g fish_pager_color_selected_background --background=2a2b33
set -g fish_pager_color_selected_prefix     $__nacre_bright --bold
set -g fish_pager_color_selected_completion $__nacre_bright

set -g fish_transient_prompt 1
set -g __nacre_first_prompt 1

# ── pieces ──────────────────────────────────────────────────────────
function __nacre_chip --argument-names bg fg text
    set_color $bg
    printf '%s' $__nacre_cap_l
    set_color -b $bg $fg
    printf ' %s ' "$text"
    set_color normal
    set_color $bg
    printf '%s' $__nacre_cap_r
    set_color normal
end

# directory: parents shortened and faded, the current folder in full and bright
function __nacre_dir
    set -l pwd (prompt_pwd --dir-length 1 --full-length-dirs 1)
    set -l icon $__nacre_i_dir
    string match -q -- '~*' $pwd; and set icon $__nacre_i_home
    test -w . ; or set icon $__nacre_i_lock

    set -l parts (string split -r -m1 / -- $pwd)
    set_color $__nacre_chip_dir
    printf '%s' $__nacre_cap_l
    set_color -b $__nacre_chip_dir $__nacre_lavender
    printf ' %s ' $icon
    if test (count $parts) -eq 2
        set_color -b $__nacre_chip_dir $__nacre_mist
        printf '%s/' $parts[1]
    end
    set_color -b $__nacre_chip_dir $__nacre_bright --bold
    printf '%s ' $parts[-1]
    set_color normal
    set_color $__nacre_chip_dir
    printf '%s' $__nacre_cap_r
    set_color normal
end

# git: a single porcelain call gives branch, upstream delta and file states
function __nacre_git
    set -l lines (command git --no-optional-locks status --porcelain=v2 --branch 2>/dev/null)
    or return

    set -l branch ''
    set -l oid ''
    set -l ahead 0
    set -l behind 0
    set -l staged 0
    set -l dirty 0
    set -l untracked 0
    set -l conflict 0
    for l in $lines
        switch $l
            case '# branch.head *'
                set branch (string sub -s 15 -- $l)
            case '# branch.oid *'
                set oid (string sub -s 14 -l 7 -- $l)
            case '# branch.ab *'
                set -l ab (string split ' ' -- $l)
                set ahead (string trim -c + -- $ab[3])
                set behind (string trim -c - -- $ab[4])
            case '1 *' '2 *'
                set -l xy (string sub -s 3 -l 2 -- $l)
                string match -qr '^[^.]' -- $xy; and set staged (math $staged + 1)
                string match -qr '^.[^.]' -- $xy; and set dirty (math $dirty + 1)
            case 'u *'
                set conflict (math $conflict + 1)
            case '? *'
                set untracked (math $untracked + 1)
        end
    end
    test "$branch" = '(detached)'; and set branch "@$oid"

    set_color $__nacre_chip_git
    printf '%s' $__nacre_cap_l
    set_color -b $__nacre_chip_git $__nacre_lavlight
    printf ' %s %s' $__nacre_i_git $branch
    test $conflict -gt 0;  and set_color -b $__nacre_chip_git $__nacre_rose;    and printf ' !%s' $conflict
    test $staged -gt 0;    and set_color -b $__nacre_chip_git $__nacre_celadon; and printf ' +%s' $staged
    test $dirty -gt 0;     and set_color -b $__nacre_chip_git $__nacre_wheat;   and printf ' ~%s' $dirty
    test $untracked -gt 0; and set_color -b $__nacre_chip_git $__nacre_mist;    and printf ' ?%s' $untracked
    test "$ahead" -gt 0 2>/dev/null;  and set_color -b $__nacre_chip_git $__nacre_steel; and printf ' ⇡%s' $ahead
    test "$behind" -gt 0 2>/dev/null; and set_color -b $__nacre_chip_git $__nacre_steel; and printf ' ⇣%s' $behind
    printf ' '
    set_color normal
    set_color $__nacre_chip_git
    printf '%s' $__nacre_cap_r
    set_color normal
end

function __nacre_duration --argument-names ms
    test -n "$ms"; and test $ms -ge 1500; or return
    set -l text
    if test $ms -lt 60000
        set text (math --scale=1 $ms / 1000)s
    else if test $ms -lt 3600000
        set text (math --scale=0 "floor($ms / 60000)")m(math --scale=0 "floor($ms % 60000 / 1000)")s
    else
        set text (math --scale=0 "floor($ms / 3600000)")h(math --scale=0 "floor($ms % 3600000 / 60000)")m
    end
    set_color $__nacre_mist
    printf '%s %s' $__nacre_i_time $text
    set_color normal
end

# ── prompts ─────────────────────────────────────────────────────────
function fish_prompt
    set -l last $status
    set -l arrow '❯'
    fish_is_root_user; and set arrow '#'
    set -l arrow_colour $__nacre_lavender
    test $last -ne 0; and set arrow_colour $__nacre_rose

    # what stays in scrollback: just where you were and the arrow
    if contains -- --final-rendering $argv
        set_color $__nacre_dim
        printf '%s ' (path basename -- (prompt_pwd --dir-length 0))
        set_color $arrow_colour
        printf '%s ' $arrow
        set_color normal
        return
    end

    # a breath of space between commands (not above the first prompt)
    if set -q __nacre_first_prompt
        set -e __nacre_first_prompt
    else
        echo
    end

    if set -q SSH_TTY
        __nacre_chip $__nacre_chip_ssh $__nacre_wheat "$__nacre_i_ssh $USER@"(prompt_hostname)
        printf ' '
    end
    __nacre_dir
    if set -l g (__nacre_git)
        printf ' %s' "$g"
    end
    echo
    set_color $arrow_colour --bold
    printf '%s ' $arrow
    set_color normal
end

function fish_right_prompt
    set -l last_pipe $pipestatus
    set -l last $status
    contains -- --final-rendering $argv; and return

    set -l out

    if set -q VIRTUAL_ENV
        set -a out (__nacre_chip $__nacre_chip_env $__nacre_steel "$__nacre_i_py "(path basename -- $VIRTUAL_ENV))
    end

    set -l njobs (count (jobs -p 2>/dev/null))
    if test $njobs -gt 0
        set -a out (set_color $__nacre_steel; printf '%s %s' $__nacre_i_jobs $njobs; set_color normal)
    end

    set -l d (__nacre_duration $CMD_DURATION)
    test -n "$d"; and set -a out $d

    if test $last -ne 0
        set -l code $last
        test (count $last_pipe) -gt 1; and set code (string join '|' $last_pipe)
        set -l sig (fish_status_to_signal $last)
        test "$sig" != "$last"; and set code $sig
        set -a out (__nacre_chip $__nacre_chip_err $__nacre_roselight "✕ $code")
    end

    string join ' ' -- $out
end

function fish_mode_prompt
end

# a single quiet line instead of a banner
function fish_greeting
    set -l up (string split . < /proc/uptime)[1]
    set -l h (math --scale=0 "floor($up / 3600)")
    set -l m (math --scale=0 "floor($up % 3600 / 60)")
    set_color $__nacre_lavender
    printf '  ◦ '
    set_color $__nacre_silver
    printf '%s' (date '+%A %-d %B')
    set_color $__nacre_mist
    printf '  ·  up %sh %sm  ·  fish %s\n' $h $m $version
    set_color normal
end
