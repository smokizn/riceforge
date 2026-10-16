-- ┌──────────────────────────────────────────────────────────────┐
-- │ NACRE · Hyprland layer                                       │
-- │ Loaded last by hyprland.lua (via hypr/riceforge.lua): looks  │
-- │ and motion only. No binds, no execs.                         │
-- └──────────────────────────────────────────────────────────────┘
-- Mother-of-pearl glass over smoke. Surfaces are frosted and lit
-- from above; focus is a pearl rim that catches lavender and ice.
-- Motion is real spring physics (hyprutils springs), tuned per role.

local MOTION_BLUR = false   -- experimental in 0.56; flip to true to try it

hl.config({
    general = {
        -- glass needs air around it
        gaps_in = 3,
        gaps_out = { top = 4, right = 8, bottom = 8, left = 8 },
        gaps_workspaces = 60,
        border_size = 2,
        col = {
            -- the pearl rim: one soft sheen, brightest at the top-left like a light source
            active_border   = { colors = { "rgba(e2e2e8bb)", "rgba(a39cc499)", "rgba(8ea6bf99)" }, angle = 45 },
            -- unfocused glass still has an edge, just frosted
            inactive_border = "rgba(ffffff16)",
        },
    },

    decoration = {
        -- continuous, squircle-like corners (power > 2 flattens the curve's start)
        rounding = 18,
        rounding_power = 3.2,

        -- the focused pane is solid; others become glass you can see through
        active_opacity = 1.0,
        inactive_opacity = 0.93,
        fullscreen_opacity = 1.0,
        dim_inactive = false,

        blur = {
            enabled = true,
            size = 7,
            passes = 3,
            noise = 0.018,        -- a little grain keeps frosted glass from banding
            contrast = 0.92,
            brightness = 0.80,
            vibrancy = 0.18,      -- a hint of the wallpaper's colour, kept muted
            vibrancy_darkness = 0.15,
            popups = true,
            xray = false,         -- glass over glass: floats blur the windows beneath
            new_optimizations = true,
        },

        -- two depths: tight contact shadow is impossible with one shadow, so
        -- favour a wide, soft one that makes panes float off the wallpaper
        shadow = {
            enabled = true,
            range = 34,
            render_power = 3,
            offset = { 0, 14 },
            color = "rgba(0a0a1499)",
            color_inactive = "rgba(0a0a1455)",
        },

        motion_blur = { enabled = MOTION_BLUR, samples = 5 },
    },

    group = {
        col = {
            border_active   = { colors = { "rgba(e2e2e8bb)", "rgba(a39cc499)" }, angle = 45 },
            border_inactive = "rgba(ffffff16)",
        },
    },

    misc = {
        background_color = "rgba(0b0b12ff)",
    },
})

-- ── Overrides of base rules (rules.lua) that fight glass ─────────
-- rules.lua disables blur for every window and shadows for tiled ones.
-- Later rules win, so this layer turns both back on.
hl.window_rule({ match = { class = ".*" }, no_blur = false })
hl.window_rule({ match = { float = 0 },   no_shadow = false })
-- things that must stay solid: games, video, screen sharing
hl.window_rule({ match = { class = "^(steam_app).*" },       opaque = true })
hl.window_rule({ match = { class = "^(mpv|vlc|imv)$" },      opaque = true })
hl.window_rule({ match = { title = ".*\\.exe" },             opaque = true })
-- a pinned window keeps the full rim even when unfocused
hl.window_rule({ match = { pin = 1 }, border_color = "rgba(a39cc4cc)" })

-- ── Layer surfaces: per-surface glass ────────────────────────────
-- ignore_alpha: blur only behind pixels more opaque than this, so the
-- bar's floating islands get glass and the gaps between them stay clear.
hl.layer_rule({ match = { namespace = "waybar" },                     blur = true, ignore_alpha = 0.28 })
hl.layer_rule({ match = { namespace = "swaync-notification-window" }, blur = true, ignore_alpha = 0.28 })
hl.layer_rule({ match = { namespace = "swaync-control-center" },      blur = true, ignore_alpha = 0.28 })
-- walker asks for its own blur region (ext-background-effect); give it motion
hl.layer_rule({ match = { namespace = "walker" },                     no_anim = false })
hl.layer_rule({ match = { namespace = "walker" },                     animation = "popin 90%" })
hl.layer_rule({ match = { namespace = "swaync-notification-window" }, animation = "slide right" })
hl.layer_rule({ match = { namespace = "swaync-control-center" },      animation = "slide right" })

-- ── Motion ───────────────────────────────────────────────────────
-- springs: zeta = c / (2*sqrt(k*m)). speed (tenths of a second) is the
-- time budget; each is set at or just above the spring's settle time.
--
--   jelly   ζ .56  overshoot 12%  ~570ms   windows arriving: a soft wobble
--   drop    ζ .60  overshoot  9%  ~550ms   scratchpads falling into place
--   pop     ζ .65  overshoot  7%  ~310ms   panels, launcher, notifications
--   wobble  ζ .68  overshoot  5%  ~440ms   tiling reflow, floats moving
--   glide   ζ .74  overshoot  3%  ~500ms   workspaces: elastic, never seasick
hl.curve("jelly",  { type = "spring", mass = 1, stiffness = 160, dampening = 14.1 })
hl.curve("drop",   { type = "spring", mass = 1, stiffness = 143, dampening = 14.5 })
hl.curve("pop",    { type = "spring", mass = 1, stiffness = 400, dampening = 26.0 })
hl.curve("wobble", { type = "spring", mass = 1, stiffness = 182, dampening = 18.3 })
hl.curve("glide",  { type = "spring", mass = 1, stiffness = 116, dampening = 15.9 })

-- beziers where a spring is the wrong tool
-- melt : leaving windows swell for an instant (y < 0), then dissolve
-- silk : colour and opacity, fast start, long soft landing
-- sink : fades out, accelerating away
hl.curve("melt", { type = "bezier", points = { { 0.55, -0.32 }, { 0.70, 0.30 } } })
hl.curve("silk", { type = "bezier", points = { { 0.22, 1.0 },   { 0.36, 1.0 } } })
hl.curve("sink", { type = "bezier", points = { { 0.40, 0.0 },   { 1.0, 1.0 } } })

hl.animation({ leaf = "windows",     enabled = true, speed = 6.2, spring = "jelly",  style = "popin 82%" })
hl.animation({ leaf = "windowsIn",   enabled = true, speed = 6.2, spring = "jelly",  style = "popin 82%" })
hl.animation({ leaf = "windowsOut",  enabled = true, speed = 2.8, bezier = "melt",   style = "popin 86%" })
hl.animation({ leaf = "windowsMove", enabled = true, speed = 4.9, spring = "wobble" })

hl.animation({ leaf = "fade",        enabled = true, speed = 3.2, bezier = "silk" })
hl.animation({ leaf = "fadeIn",      enabled = true, speed = 3.2, bezier = "silk" })
hl.animation({ leaf = "fadeOut",     enabled = true, speed = 2.4, bezier = "sink" })
hl.animation({ leaf = "fadeSwitch",  enabled = true, speed = 3.8, bezier = "silk" })   -- active/inactive opacity
hl.animation({ leaf = "fadeShadow",  enabled = true, speed = 3.2, bezier = "silk" })
hl.animation({ leaf = "fadeDim",     enabled = true, speed = 3.2, bezier = "silk" })

-- focus: the pearl rim flows over to the new window
hl.animation({ leaf = "border",      enabled = true, speed = 4.2, bezier = "silk" })
hl.animation({ leaf = "borderangle", enabled = false })

hl.animation({ leaf = "workspaces",       enabled = true, speed = 5.4, spring = "glide", style = "slide" })
hl.animation({ leaf = "specialWorkspace", enabled = true, speed = 5.9, spring = "drop",  style = "slidevert" })

hl.animation({ leaf = "layers",        enabled = true, speed = 3.4, spring = "pop",  style = "popin 90%" })
hl.animation({ leaf = "layersIn",      enabled = true, speed = 3.4, spring = "pop",  style = "popin 90%" })
hl.animation({ leaf = "layersOut",     enabled = true, speed = 1.8, bezier = "sink", style = "popin 94%" })
hl.animation({ leaf = "fadeLayersIn",  enabled = true, speed = 2.2, bezier = "silk" })
hl.animation({ leaf = "fadeLayersOut", enabled = true, speed = 1.6, bezier = "sink" })
