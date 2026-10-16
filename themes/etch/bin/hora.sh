#!/usr/bin/env bash
# The canonical hour for the current local time.
#   hora.sh           -> waybar JSON
#   hora.sh --plain   -> bare word (hyprlock)
h=$((10#$(date +%H)))
case $h in
    0|1|2)    name="vigils";   gloss="the night watch" ;;
    3|4|5)    name="lauds";    gloss="praise, before first light" ;;
    6|7|8)    name="prime";    gloss="the first hour, daybreak" ;;
    9|10|11)  name="terce";    gloss="the third hour, mid-morning" ;;
    12|13|14) name="sext";     gloss="the sixth hour, midday" ;;
    15|16|17) name="nones";    gloss="the ninth hour, afternoon" ;;
    18|19|20) name="vespers";  gloss="evening, the lamps are lit" ;;
    *)        name="compline"; gloss="completion, before sleep" ;;
esac

if [[ $1 == --plain ]]; then
    printf '%s\n' "${name^^}"
else
    printf '{"text":"%s","tooltip":"%s · %s","class":"%s"}\n' "$name" "${name^}" "$gloss" "$name"
fi
