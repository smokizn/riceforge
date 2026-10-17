#!/bin/bash

sources=$(pactl list short sources | awk '$2 ~ /^alsa_input/ {print $1}')

any_unmuted=false
volume=""

for source in $sources; do
    if pactl get-source-mute "$source" | grep -q "Mute: no"; then
        any_unmuted=true
    fi

    # Get volume from the first internal mic
    if [ -z "$volume" ]; then
        volume=$(pactl get-source-volume "$source" | grep -oE '[0-9]+%' | head -n1 | tr -d '%')
    fi
done

if [ "$any_unmuted" = true ]; then
    echo "{\"text\":\"󰍬\",\"tooltip\":\"Mic: ${volume}% • Click to mute\"}"
else
    echo '{"text":"󰍭","tooltip":"Mic: Muted • Click to unmute"}'
fi