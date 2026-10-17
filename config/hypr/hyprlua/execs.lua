--  Hyprland autostart (Riceforge base). Personal apps go in custom/execs.lua.
hl.on("hyprland.start", function()
    -- polkit authentication dialogs (hyprpolkitagent ships a user unit)
    hl.exec_cmd("systemctl --user start hyprpolkitagent.service")

    -- the active theme's session: wallpaper, riceforge-shell or tray applets
    hl.exec_cmd("~/.config/riceforge/bin/riceforge session-start")

    -- bar and notifications
    hl.exec_cmd("waybar")
    hl.exec_cmd("swaync")

    -- launcher: elephant (data provider) first, then walker's resident service.
    -- Clipboard history comes from elephant's clipboard provider (SUPER+V).
    hl.exec_cmd("elephant")
    hl.exec_cmd("walker --gapplication-service")

    -- idle: lock after 5 min, screen off after 10 (hypr/hypridle.conf)
    hl.exec_cmd("hypridle")
end)

-- Former exec (not exec-once)
hl.exec_cmd("hyprctl dispatch submap global")
