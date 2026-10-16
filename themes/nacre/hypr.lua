-- ┌──────────────────────────────────────────────────────────────┐
-- │ NACRE · Visionary · Hyprland layer                           │
-- │ Loaded last by hyprland.lua (via hypr/riceforge.lua): looks  │
-- │ and motion only. No binds, no execs.                         │
-- └──────────────────────────────────────────────────────────────┘
-- An antique celestial instrument: ink-glass panes over engraved plates.
-- Focus is an engraved silver line that catches tarnished brass, the way
-- light runs along the edge of a burnished plate. Motion is real spring
-- physics, calm and slightly elastic.
-- (the previous liquid-glass version: git tag `nacre-glass`)

local MOTION_BLUR = false   -- experimental in 0.56; flip to true to try it

local silver = "b9bcc2"
local brass  = "b39a5e"
local ink    = "0b0a0a"

hl.config({
    general = {
        gaps_in = 3,
        gaps_out = { top = 4, right = 8, bottom = 8, left = 8 },
        gaps_workspaces = 60,
        border_size = 2,
        col = {
            -- silver with a brass glint at the middle of the run, like burnished metal
            active_border   = { colors = { "rgba(" .. silver .. "cc)", "rgba(" .. brass .. "bb)",
                                           "rgba(" .. silver .. "aa)" }, angle = 45 },
            -- unfocused panes keep a faint engraved edge
            inactive_border = "rgba(e6dfcf14)",
        },
    },

    decoration = {
        -- a plate's bevel: rounded, but not a pill
        rounding = 14,
        rounding_power = 2.6,

        active_opacity = 1.0,
        inactive_opacity = 0.94,
        fullscreen_opacity = 1.0,
        dim_inactive = false,

        blur = {
            enabled = true,
            size = 7,
            passes = 3,
            noise = 0.024,        -- grain, like paper under the glass
            contrast = 0.94,
            brightness = 0.74,    -- smoked: text over glass stays legible
            vibrancy = 0.08,      -- monochrome world; colour stays in the art
            vibrancy_darkness = 0.1,
            popups = true,
            xray = false,
            new_optimizations = true,
        },

        shadow = {
            enabled = true,
            range = 30,
            render_power = 3,
            offset = { 0, 12 },
            color = "rgba(" .. ink .. "b3)",
            color_inactive = "rgba(" .. ink .. "66)",
        },

        motion_blur = { enabled = MOTION_BLUR, samples = 5 },
    },

    group = {
        col = {
            border_active   = { colors = { "rgba(" .. silver .. "cc)", "rgba(" .. brass .. "bb)" }, angle = 45 },
            border_inactive = "rgba(e6dfcf14)",
        },
    },

    misc = {
        background_color = "rgba(" .. ink .. "ff)",
    },
})

-- ── Overrides of base rules (rules.lua) that fight glass ─────────
-- rules.lua disables blur for every window and shadows for tiled ones.
-- Later rules win (verified with hyprctl getprop), so this turns both back on.
hl.window_rule({ match = { class = ".*" }, no_blur = false })
hl.window_rule({ match = { float = 0 },   no_shadow = false })
-- things that must stay solid: games, video, screen sharing
hl.window_rule({ match = { class = "^(steam_app).*" },       opaque = true })
hl.window_rule({ match = { class = "^(mpv|vlc|imv)$" },      opaque = true })
hl.window_rule({ match = { title = ".*\\.exe" },             opaque = true })
-- a pinned window is gilded
hl.window_rule({ match = { pin = 1 }, border_color = "rgba(" .. brass .. "dd)" })

-- ── Layer surfaces ───────────────────────────────────────────────
-- ignore_alpha: blur only behind pixels more opaque than this, so floating
-- islands and plates get glass and the gaps between them stay clear.
hl.layer_rule({ match = { namespace = "waybar" },                     blur = true, ignore_alpha = 0.28 })
hl.layer_rule({ match = { namespace = "swaync-notification-window" }, blur = true, ignore_alpha = 0.28 })
hl.layer_rule({ match = { namespace = "swaync-control-center" },      blur = true, ignore_alpha = 0.28 })
hl.layer_rule({ match = { namespace = "riceforge-panel" },            blur = true, ignore_alpha = 0.30 })
hl.layer_rule({ match = { namespace = "riceforge-prompt" },           blur = true, ignore_alpha = 0.30 })
hl.layer_rule({ match = { namespace = "riceforge-widget" },           blur = true, ignore_alpha = 0.45 })
-- motion per surface
hl.layer_rule({ match = { namespace = "walker" },                     no_anim = false })
hl.layer_rule({ match = { namespace = "walker" },                     animation = "popin 92%" })
hl.layer_rule({ match = { namespace = "riceforge-panel" },            animation = "popin 94%" })
hl.layer_rule({ match = { namespace = "riceforge-prompt" },           animation = "popin 90%" })
hl.layer_rule({ match = { namespace = "riceforge-widget" },           animation = "fade" })
hl.layer_rule({ match = { namespace = "swaync-notification-window" }, animation = "slide right" })
hl.layer_rule({ match = { namespace = "swaync-control-center" },      animation = "slide right" })

-- ── Motion ───────────────────────────────────────────────────────
-- springs: zeta = c / (2*sqrt(k*m)). speed (tenths of a second) is the
-- time budget; each is set at or just above the spring's settle time.
--
--   unveil  ζ .62  overshoot  8%  ~510ms   windows arriving: a slow, slightly elastic reveal
--   drop    ζ .60  overshoot  9%  ~550ms   scratchpads falling into place
--   pop     ζ .65  overshoot  7%  ~310ms   panels, launcher, notifications
--   wobble  ζ .68  overshoot  5%  ~440ms   tiling reflow, floats moving
--   glide   ζ .74  overshoot  3%  ~500ms   workspaces: like turning an astrolabe's rete
hl.curve("unveil", { type = "spring", mass = 1, stiffness = 160, dampening = 15.7 })
hl.curve("drop",   { type = "spring", mass = 1, stiffness = 143, dampening = 14.5 })
hl.curve("pop",    { type = "spring", mass = 1, stiffness = 400, dampening = 26.0 })
hl.curve("wobble", { type = "spring", mass = 1, stiffness = 182, dampening = 18.3 })
hl.curve("glide",  { type = "spring", mass = 1, stiffness = 116, dampening = 15.9 })

-- melt : leaving windows swell for an instant (y < 0), then dissolve
-- silk : colour and opacity, fast start, long soft landing
-- sink : fades out, accelerating away
hl.curve("melt", { type = "bezier", points = { { 0.55, -0.32 }, { 0.70, 0.30 } } })
hl.curve("silk", { type = "bezier", points = { { 0.22, 1.0 },   { 0.36, 1.0 } } })
hl.curve("sink", { type = "bezier", points = { { 0.40, 0.0 },   { 1.0, 1.0 } } })

hl.animation({ leaf = "windows",     enabled = true, speed = 6.0, spring = "unveil", style = "popin 88%" })
hl.animation({ leaf = "windowsIn",   enabled = true, speed = 6.0, spring = "unveil", style = "popin 88%" })
hl.animation({ leaf = "windowsOut",  enabled = true, speed = 2.8, bezier = "melt",   style = "popin 90%" })
hl.animation({ leaf = "windowsMove", enabled = true, speed = 4.9, spring = "wobble" })

hl.animation({ leaf = "fade",        enabled = true, speed = 3.2, bezier = "silk" })
hl.animation({ leaf = "fadeIn",      enabled = true, speed = 3.2, bezier = "silk" })
hl.animation({ leaf = "fadeOut",     enabled = true, speed = 2.4, bezier = "sink" })
hl.animation({ leaf = "fadeSwitch",  enabled = true, speed = 3.8, bezier = "silk" })
hl.animation({ leaf = "fadeShadow",  enabled = true, speed = 3.2, bezier = "silk" })
hl.animation({ leaf = "fadeDim",     enabled = true, speed = 3.2, bezier = "silk" })

-- focus: the engraved line flows over to the new window
hl.animation({ leaf = "border",      enabled = true, speed = 4.2, bezier = "silk" })
hl.animation({ leaf = "borderangle", enabled = false })

hl.animation({ leaf = "workspaces",       enabled = true, speed = 5.4, spring = "glide", style = "slide" })
hl.animation({ leaf = "specialWorkspace", enabled = true, speed = 5.9, spring = "drop",  style = "slidevert" })

hl.animation({ leaf = "layers",        enabled = true, speed = 3.4, spring = "pop",  style = "popin 90%" })
hl.animation({ leaf = "layersIn",      enabled = true, speed = 3.4, spring = "pop",  style = "popin 90%" })
hl.animation({ leaf = "layersOut",     enabled = true, speed = 1.8, bezier = "sink", style = "popin 94%" })
hl.animation({ leaf = "fadeLayersIn",  enabled = true, speed = 2.2, bezier = "silk" })
hl.animation({ leaf = "fadeLayersOut", enabled = true, speed = 1.6, bezier = "sink" })
