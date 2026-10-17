#!/bin/bash

sources=$(pactl list short sources | awk '$2 ~ /^alsa_input/ {print $1}')

any_unmuted=false

for source in $sources; do
    if pactl get-source-mute "$source" | grep -q "Mute: no"; then
        any_unmuted=true
        break
    fi
done

if [ "$any_unmuted" = true ]; then
    # Mute ALL internal microphones
    for source in $sources; do
        pactl set-source-mute "$source" 1
    done
else
    # Unmute ALL internal microphones
    for source in $sources; do
        pactl set-source-mute "$source" 0
    done
fi

# Immediately refresh Waybar
pkill -RTMIN+12 waybar