-- Riceforge extra: the author's personal apps. Enabled by the "personal" feature
-- (a dofile line in ~/.config/riceforge-local/hypr.lua). Every command is guarded,
-- so a missing app does nothing instead of erroring.
hl.on("hyprland.start", function()
    hl.exec_cmd("command -v discord >/dev/null && discord")
    hl.exec_cmd("command -v easyeffects >/dev/null && easyeffects -w")
end)

-- Discord lives on its own special workspace
hl.window_rule({ match = { class = "^(discord)$" }, workspace = "special:discord" })
hl.bind("SUPER + D", hl.dsp.workspace.toggle_special("discord"), { description = "Workspace: Discord" })
hl.bind("SUPER + ALT + D", hl.dsp.window.move({ workspace = "special:discord", follow = false }),
    { description = "Window: Send to Discord workspace" })

-- FluxCap screen recorder (cargo install; not packaged)
hl.bind("SUPER + SHIFT + R", hl.dsp.exec_cmd(
    "f=$(command -v fluxcap || echo \"$HOME/.cargo/bin/fluxcap\"); [ -x \"$f\" ] && \"$f\" toggle --region"),
    { description = "Utilities: FluxCap region toggle" })
