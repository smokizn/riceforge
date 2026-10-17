--##! Apps
hl.bind("SUPER + T", hl.dsp.exec_cmd("kitty"), { description = "App: Terminal" })
hl.bind("SUPER + W", hl.dsp.exec_cmd("~/.config/hypr/hyprland/scripts/launch_first_available.sh zen-browser firefox chromium brave librewolf"), { description = "App: Browser" })
hl.bind("SUPER + E", hl.dsp.exec_cmd("~/.config/hypr/hyprland/scripts/launch_first_available.sh dolphin nautilus nemo thunar"), { description = "App: File manager" })

--##! Launcher
hl.bind("SUPER + SUPER_L",
    hl.dsp.exec_cmd("walker"),
    { description = "Launcher" }
)
--##! Utilities

--# Screenshot - Area (save to file)
hl.bind("SUPER + SHIFT + S", hl.dsp.exec_cmd(
    "mkdir -p ~/Pictures/Screenshots && grim -g \"$(slurp)\" - | tee ~/Pictures/Screenshots/$(date +'%Y%m%d_%H%M%S').png | wl-copy"),
    { description = "Utilities: Screen snip >> clipboard & file" })

--# Clipboard manager
hl.bind("SUPER + V", hl.dsp.exec_cmd(
    "walker -m clipboard"),
    { description = "Utilities: Clipboard history >> clipboard" })

--# Color picker
hl.bind("SUPER + SHIFT + C", hl.dsp.exec_cmd("hyprpicker -a"),
    { description = "Utilities: Pick color #RRGGBB >> clipboard" })

--# Emoji picker
hl.bind("SUPER + Period", hl.dsp.exec_cmd("hypremoji"),
    { description = "Utilities: Emoji >> clipboard" })

--# Task manager
hl.bind("CTRL + SHIFT + Escape", hl.dsp.exec_cmd("kitty -e btop"),
    { description = "App: Task manager" })

--# Audio mixer
hl.bind("CTRL + SUPER + V", hl.dsp.exec_cmd("pavucontrol"),
    { description = "App: Volume mixer" })

--# Screenshots
--# Fullscreen screenshot >> clipboard
hl.bind("Print", hl.dsp.exec_cmd("grim - | wl-copy"),
    { locked = true, description = "Utilities: Screenshot >> clipboard" })

--# Area screenshot >> clipboard
hl.bind("SUPER + SHIFT + X", hl.dsp.exec_cmd("grim -g \"$(slurp)\" - | wl-copy"),
    { description = "Utilities: Screen snip >> clipboard" })

--# Save fullscreen screenshot to file
hl.bind("CTRL + Print", hl.dsp.exec_cmd(
    "mkdir -p ~/Pictures/Screenshots && grim ~/Pictures/Screenshots/Screenshot_$(date +'%Y-%m-%d_%H-%M-%S').png"),
    { locked = true, description = "Utilities: Screenshot >> file" })

--##! Media

--# Volume
hl.bind("XF86AudioRaiseVolume", hl.dsp.exec_cmd("wpctl set-volume @DEFAULT_AUDIO_SINK@ 2%+ -l 1.5"),
    { locked = true, repeating = true })
hl.bind("XF86AudioLowerVolume", hl.dsp.exec_cmd("wpctl set-volume @DEFAULT_AUDIO_SINK@ 2%-"),
    { locked = true, repeating = true })
hl.bind("XF86AudioMute", hl.dsp.exec_cmd("wpctl set-mute @DEFAULT_AUDIO_SINK@ toggle"),
    { locked = true })

--# Mic
hl.bind("XF86AudioMicMute", hl.dsp.exec_cmd("wpctl set-mute @DEFAULT_SOURCE@ toggle"),
    { locked = true })

--# Brightness
hl.bind("XF86MonBrightnessUp", hl.dsp.exec_cmd("brightnessctl s 2%+"),
    { locked = true, repeating = true })
hl.bind("XF86MonBrightnessDown", hl.dsp.exec_cmd("brightnessctl s 2%-"),
    { locked = true, repeating = true })

--# Media playback
hl.bind("XF86AudioPlay", hl.dsp.exec_cmd("playerctl play-pause"), { locked = true })
hl.bind("XF86AudioPause", hl.dsp.exec_cmd("playerctl play-pause"), { locked = true })
hl.bind("XF86AudioNext", hl.dsp.exec_cmd("playerctl next"), { locked = true })
hl.bind("XF86AudioPrev", hl.dsp.exec_cmd("playerctl previous"), { locked = true })

--##! Session
hl.bind("SUPER + L", hl.dsp.exec_cmd("hyprlock"), { description = "Session: Lock" })
hl.bind("SUPER + SHIFT + L", hl.dsp.exec_cmd("systemctl suspend"),
    { locked = true, description = "Session: Sleep" })
hl.bind("CTRL + ALT + Delete", hl.dsp.exec_cmd("pkill -x wlogout || wlogout"), { description = "Shell: Toggle session menu" })

--##! Window

--# Mouse binds
hl.bind("SUPER + mouse:272", hl.dsp.window.drag(), { mouse = true, description = "Window: Move" })
hl.bind("SUPER + mouse:274", hl.dsp.window.drag(), { mouse = true })
hl.bind("SUPER + mouse:273", hl.dsp.window.resize(), { mouse = true, description = "Window: Resize" })


--#/# bind = SUPER, ←/↑/→/↓,, -- Focus in direction
for i = 1, 4 do
    local arrowkey = { "Left", "Right", "Up", "Down" }
    local focusdir = { "l", "r", "u", "d" }
    hl.bind("SUPER + " .. arrowkey[i], hl.dsp.focus({ direction = focusdir[i] }),
        { description = "Window: Focus " .. arrowkey[i] })
end
for i = 1, 2 do
    local bracketkey = { "BracketLeft", "BracketRight" }
    local focusdir = { "l", "r" }
    hl.bind("SUPER + " .. bracketkey[i], hl.dsp.focus({ direction = focusdir[i] }))
end

--#/# bind = SUPER+SHIFT, ←/↑/→/↓,, -- Move in direction
for i = 1, 4 do
    local arrowkey = { "Left", "Right", "Up", "Down" }
    local movedir = { "l", "r", "u", "d" }
    hl.bind("SUPER + SHIFT + " .. arrowkey[i], hl.dsp.window.move({ direction = movedir[i] }),
        { description = "Window: Move " .. arrowkey[i] })
end

hl.bind("ALT + F4", hl.dsp.window.close()) -- [hidden] Close (Windows)
hl.bind("SUPER + Q", hl.dsp.window.close(), { description = "Window: Close" })
hl.bind("SUPER + SHIFT + ALT + Q", hl.dsp.exec_cmd("hyprctl kill"),
    { description = "Window: Forcefully zap a window" })

--# Positioning mode
hl.bind("SUPER + ALT + Space", hl.dsp.window.float({ action = "toggle" }), { description = "Window: Float/Tile" })

hl.bind("SUPER + F", hl.dsp.window.fullscreen({ mode = "fullscreen", action = "toggle" }),
    { description = "Window: Fullscreen" })
hl.bind("SUPER + ALT + F", hl.dsp.window.fullscreen_state({ internal = 0, client = 3, action = "toggle" }),
    { description = "Window: Fullscreen spoof" })
hl.bind("SUPER + P", hl.dsp.window.pin(), { description = "Window: Pin" })

--#/# bind = SUPER+ALT, Hash,, -- Send to workspace -- (1, 2, 3,...)
-- Using raw keycodes because some keyboard layouts register number keys as different chars. Verify with `wev`
for i = 1, 10 do
    local numberkey = { 10, 11, 12, 13, 14, 15, 16, 17, 18, 19 }
    hl.bind("SUPER + ALT + code:" .. numberkey[i], function()
        hl.dispatch(hl.dsp.window.move({ workspace = i, follow = false }))
    end)
end
-- keypad numbers
for i = 1, 10 do
    local numpadkey = { 87, 88, 89, 83, 84, 85, 79, 80, 81, 90 }
    hl.bind("SUPER + ALT + code:" .. numpadkey[i], function()
        hl.dispatch(hl.dsp.window.move({ workspace = i, follow = false }))
    end)
end

--#/# bind = SUPER+SHIFT, Scroll ↑/↓,, -- Send to workspace left/right
hl.bind("SUPER + SHIFT + mouse_down", hl.dsp.window.move({ workspace = "r-1" }))
hl.bind("SUPER + SHIFT + mouse_up", hl.dsp.window.move({ workspace = "r+1" }))
hl.bind("SUPER + ALT + mouse_down", hl.dsp.window.move({ workspace = "-1" }))
hl.bind("SUPER + ALT + mouse_up", hl.dsp.window.move({ workspace = "+1" }))

--#/# bind = SUPER+SHIFT, Page_↑/↓,, -- Send to workspace left/right
hl.bind("SUPER + ALT + Page_Down", hl.dsp.window.move({ workspace = "+1" }))
hl.bind("SUPER + ALT + Page_Up", hl.dsp.window.move({ workspace = "-1" }))
hl.bind("SUPER + SHIFT + Page_Down", hl.dsp.window.move({ workspace = "r+1" }))
hl.bind("SUPER + SHIFT + Page_Up", hl.dsp.window.move({ workspace = "r-1" }))
hl.bind("CTRL + SUPER + SHIFT + Right", hl.dsp.window.move({ workspace = "r+1" }))
hl.bind("CTRL + SUPER + SHIFT + Left", hl.dsp.window.move({ workspace = "r-1" }))

hl.bind("SUPER + ALT + S",
    hl.dsp.window.move({ workspace = "special:spotify", follow = false }), { description = "Window: Send to scratchpad" })


--##! Workspace

--# Switching
--#/# bind = SUPER, Hash,, -- Focus workspace -- (1, 2, 3,...)
-- Using raw keycodes because some keyboard layouts register number keys as different chars. Verify with `wev`
for i = 1, 10 do
    local numberkey = { 10, 11, 12, 13, 14, 15, 16, 17, 18, 19 }
    hl.bind("SUPER + code:" .. numberkey[i], function()
        hl.dispatch(hl.dsp.focus({ workspace = i }))
    end, { description = "Workspace: Focus " .. i })
end
-- keypad numbers
for i = 1, 10 do
    local numpadkey = { 87, 88, 89, 83, 84, 85, 79, 80, 81, 90 }
    hl.bind("SUPER + code:" .. numpadkey[i], function()
        hl.dispatch(hl.dsp.focus({ workspace = i }))
    end)
end

--#/# bind = CTRL+SUPER, ←/→,, -- Focus left/right
hl.bind("CTRL + SUPER + Right", hl.dsp.focus({ workspace = "r+1" }), { description = "Workspace: Focus right" })
hl.bind("CTRL + SUPER + Left", hl.dsp.focus({ workspace = "r-1" }), { description = "Workspace: Focus left" })
hl.bind("CTRL + SUPER + ALT + Right", hl.dsp.focus({ workspace = "m+1" }))
hl.bind("CTRL + SUPER + ALT + Left", hl.dsp.focus({ workspace = "m-1" }))

--#/# bind = SUPER, Page_↑/↓,, -- Focus left/right
hl.bind("SUPER + Page_Down", hl.dsp.focus({ workspace = "+1" }))
hl.bind("SUPER + Page_Up", hl.dsp.focus({ workspace = "-1" }))
hl.bind("CTRL + SUPER + Page_Down", hl.dsp.focus({ workspace = "r+1" }))
hl.bind("CTRL + SUPER + Page_Up", hl.dsp.focus({ workspace = "r-1" }))

--#/# bind = SUPER, Scroll ↑/↓,, -- Focus left/right
-- hl.bind("SUPER + mouse_up", hl.dsp.focus({ workspace = "+1" }))
-- hl.bind("SUPER + mouse_down", hl.dsp.focus({ workspace = "-1" }))
hl.bind("CTRL + SUPER + mouse_up", hl.dsp.focus({ workspace = "r+1" }))
hl.bind("CTRL + SUPER + mouse_down", hl.dsp.focus({ workspace = "r-1" }))

--# Special
hl.bind("SUPER + S", hl.dsp.workspace.toggle_special("spotify"), { description = "Workspace: Toggle scratchpad" })
hl.bind("SUPER + mouse:275", hl.dsp.workspace.toggle_special("special"))
hl.bind("CTRL + SUPER + BracketLeft", hl.dsp.focus({ workspace = "-1" }))
hl.bind("CTRL + SUPER + BracketRight", hl.dsp.focus({ workspace = "+1" }))
hl.bind("CTRL + SUPER + Up", hl.dsp.focus({ workspace = "r-5" }))
hl.bind("CTRL + SUPER + Down", hl.dsp.focus({ workspace = "r+5" }))

--##! Screen

--# Zoom
local function zoomfunction(value)
    local zoomvalue = hl.get_config("cursor:zoom_factor")
    if (zoomvalue + value) > 3.0 then
        hl.config({ cursor = { zoom_factor = 3.0 } })
    elseif (zoomvalue + value) < 1.0 then
        hl.config({ cursor = { zoom_factor = 1.0 } })
    else
        hl.config({ cursor = { zoom_factor = zoomvalue + value } })
    end
end
hl.bind("SUPER + Minus", function() zoomfunction(-0.1) end, { repeating = true, description = "Screen: Zoom out" })
hl.bind("SUPER + Equal", function() zoomfunction(0.1) end, { repeating = true, description = "Screen: Zoom in" })

--##! Riceforge shell (acts only while a theme runs riceforge-shell, i.e. nacre)
local rfs = "pgrep -x riceforge-shell >/dev/null && ~/.config/riceforge/shell/riceforge-shell "
hl.bind("SUPER + ALT + W", hl.dsp.exec_cmd(rfs .. "wallpapers"), { description = "Shell: Plate archive (wallpapers)" })
hl.bind("SUPER + ALT + N", hl.dsp.exec_cmd(rfs .. "wifi"),       { description = "Shell: Wi-Fi panel" })
hl.bind("SUPER + ALT + B", hl.dsp.exec_cmd(rfs .. "bluetooth"),  { description = "Shell: Bluetooth panel" })
hl.bind("SUPER + ALT + M", hl.dsp.exec_cmd(rfs .. "moon"),       { description = "Shell: Lunar ephemeris" })
