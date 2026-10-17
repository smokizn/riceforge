#!/bin/bash

# the sound is optional: drop any gunshot.mp3 into ~/.config/waybar/ (not shipped)
snd="$HOME/.config/waybar/gunshot.mp3"
[ -r "$snd" ] && command -v mpv >/dev/null && mpv --no-terminal "$snd" &

GUN_STATE="/tmp/waybar_gun_state.json"
BULLET_STATE="/tmp/waybar_bullet_state.json"

echo '{"text":"🔫","class":"shooting"}' > "$GUN_STATE"
echo '{"text":"💨","class":"bullet"}' > "$BULLET_STATE"
pkill -RTMIN+8 waybar
pkill -RTMIN+9 waybar

sleep 0.05


echo '{"text":"☄️","class":"bullet"}' > "$BULLET_STATE"
pkill -RTMIN+9 waybar

sleep 0.05


echo '{"text":"💥","class":"impact"}' > "$BULLET_STATE"
pkill -RTMIN+9 waybar

sleep 0.12


echo '{"text":"🔫","class":"idle"}' > "$GUN_STATE"
echo '{"text":"","class":"hidden"}' > "$BULLET_STATE"
pkill -RTMIN+8 waybar
pkill -RTMIN+9 waybar