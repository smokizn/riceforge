-- ┌──────────────────────────────────────────────────────────────┐
-- │ ETCH · Hyprland layer                                        │
-- │ Loaded last by hyprland.lua (via hypr/riceforge.lua), so it  │
-- │ only overrides looks: no binds, no execs, no behaviour.      │
-- └──────────────────────────────────────────────────────────────┘
-- Graphite plates on a zinc bench. One mordant colour, lichen,
-- marks where the acid has bitten: the focused window, the active
-- folio, the selection. Flat colour only: no glow, no gradients.

local ink    = "0a0a0b"
local rule   = "2a2a2e"
local lichen = "c2d94c"
local steel  = "6b6b70"

hl.config({
    general = {
        -- plate margins: generous outside, tight gutters between columns
        gaps_in = 4,
        gaps_out = { top = 6, right = 12, bottom = 12, left = 12 },
        gaps_workspaces = 48,
        border_size = 2,
        col = {
            active_border   = "rgba(" .. lichen .. "e6)",
            inactive_border = "rgba(" .. rule .. "cc)",
        },
    },

    decoration = {
        -- a bevelled plate edge: softened, never pill-round
        rounding = 4,
        rounding_power = 2.0,

        active_opacity = 1.0,
        inactive_opacity = 1.0,

        -- unfocused plates recede slightly
        dim_inactive = true,
        dim_strength = 0.07,
        dim_special = 0.35,

        -- no glass. metal and paper are opaque.
        blur = { enabled = false },

        -- tiled windows already have no_shadow (rules.lua); this lifts floats off the bench
        shadow = {
            enabled = true,
            range = 24,
            render_power = 4,
            offset = { 0, 10 },
            color = "rgba(000000b8)",
            color_inactive = "rgba(00000066)",
        },
    },

    group = {
        col = {
            border_active   = "rgba(" .. lichen .. "e6)",
            border_inactive = "rgba(" .. rule .. "ff)",
        },
    },

    misc = {
        background_color = "rgba(" .. ink .. "ff)",
    },
})

-- a pinned window is marked in steel, not the accent
hl.window_rule({ match = { pin = 1 }, border_color = "rgba(" .. steel .. "ff)" })

-- ── Motion: the printing process ──────────────────────────────
-- bite : acid taking the line, fast then settling (expo-out). arrivals.
-- lift : the sheet leaving the plate (quad-in). exits, always quicker.
-- pull : the press roller, eased at both ends. workspaces.
hl.curve("bite", { type = "bezier", points = { { 0.16, 1.0 }, { 0.30, 1.0 } } })
hl.curve("lift", { type = "bezier", points = { { 0.55, 0.0 }, { 0.80, 0.15 } } })
hl.curve("pull", { type = "bezier", points = { { 0.65, 0.05 }, { 0.30, 1.0 } } })
hl.curve("even", { type = "bezier", points = { { 0.0, 0.0 }, { 1.0, 1.0 } } })

-- speed is in tenths of a second.
hl.animation({ leaf = "windows",     enabled = true, speed = 2.8, bezier = "bite", style = "popin 94%" })
hl.animation({ leaf = "windowsIn",   enabled = true, speed = 2.8, bezier = "bite", style = "popin 94%" })
hl.animation({ leaf = "windowsOut",  enabled = true, speed = 1.7, bezier = "lift", style = "popin 97%" })
hl.animation({ leaf = "windowsMove", enabled = true, speed = 3.0, bezier = "bite" })

hl.animation({ leaf = "fade",        enabled = true, speed = 2.4, bezier = "bite" })
hl.animation({ leaf = "fadeIn",      enabled = true, speed = 2.4, bezier = "bite" })
hl.animation({ leaf = "fadeOut",     enabled = true, speed = 1.6, bezier = "lift" })
hl.animation({ leaf = "fadeDim",     enabled = true, speed = 3.5, bezier = "even" })

-- focus is "bitten in": the lichen border arrives a beat after the window
hl.animation({ leaf = "border",      enabled = true, speed = 3.2, bezier = "bite" })
hl.animation({ leaf = "borderangle", enabled = false })

hl.animation({ leaf = "workspaces",       enabled = true, speed = 3.4, bezier = "pull", style = "slidefade 14%" })
-- scratchpads (discord, spotify) rise like a proof slid under the plate
hl.animation({ leaf = "specialWorkspace", enabled = true, speed = 3.0, bezier = "bite", style = "slidefadevert 18%" })

hl.animation({ leaf = "layers",    enabled = true, speed = 2.4, bezier = "bite", style = "slide" })
hl.animation({ leaf = "layersIn",  enabled = true, speed = 2.4, bezier = "bite", style = "slide" })
hl.animation({ leaf = "layersOut", enabled = true, speed = 1.6, bezier = "lift", style = "slide" })
