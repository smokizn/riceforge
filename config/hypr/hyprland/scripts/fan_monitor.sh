#!/bin/bash

FAN1="/sys/module/linuwu_sense/drivers/platform:acer-wmi/acer-wmi/hwmon/hwmon5/fan1_input"
FAN2="/sys/module/linuwu_sense/drivers/platform:acer-wmi/acer-wmi/hwmon/hwmon5/fan2_input"

fan1=$(cat "$FAN1" 2>/dev/null)
fan2=$(cat "$FAN2" 2>/dev/null)

fan1=${fan1:-0}
fan2=${fan2:-0}

avg=$(( (fan1 + fan2) / 2 ))


if [ "$avg" -lt 2000 ]; then
    icon="󰈐"
    class="low"
elif [ "$avg" -lt 4000 ]; then
    icon="󰾆"
    class="medium"
else
    icon="󰓅"
    class="high"
fi

echo "{\"text\":\"$icon ${fan1}/${fan2} RPM\",\"class\":\"$class\",\"tooltip\":\"CPU Fan: ${fan1} RPM\nGPU Fan: ${fan2} RPM\"}"