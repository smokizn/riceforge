
-- Smooth

-- hl.animation({ leaf = "windows",     enabled = false })
-- hl.animation({ leaf = "windowsMove", enabled = false })


-- hl.animation({ leaf = "fadeIn",      enabled = false })
-- hl.animation({ leaf = "fadeOut",     enabled = false })

-- hl.animation({ leaf = "layersIn",    enabled = false })
-- hl.animation({ leaf = "layersOut",   enabled = false })
-- hl.animation({ leaf = "fadeLayersIn",  enabled = false })
-- hl.animation({ leaf = "fadeLayersOut", enabled = false })

-- hl.animation({ leaf = "border",      enabled = false })
-- hl.animation({ leaf = "borderangle", enabled = false })

-- hl.animation({ leaf = "zoomFactor",  enabled = false })

-- hl.animation({ leaf = "workspaces",         enabled = true,  speed = 4,     bezier = "menu_decel",      style = "slide"     })
-- -- specialWorkspace
-- hl.animation({ leaf = "specialWorkspaceIn", enabled = true,  speed = 1.1,   bezier = "emphasizedDecel", style = "slidevert" })
-- hl.animation({ leaf = "specialWorkspaceOut",enabled = true,  speed = 1.1,   bezier = "emphasizedAccel", style = "slidevert" })
hl.curve("smooth", {
    type = "bezier",
    points = {
        {0.25, 0.1},
        {0.25, 1.0}
    }
})

hl.animation({
    leaf = "windows",
    enabled = true,
    speed = 4,
    bezier = "smooth"
})

hl.animation({
    leaf = "fade",
    enabled = true,
    speed = 4,
    bezier = "smooth"
})

hl.animation({
    leaf = "workspaces",
    enabled = true,
    speed = 4,
    bezier = "smooth"
})

-- Bounce
hl.curve("bounce", {
    type = "bezier",
    points = {
        {0.34, 1.56},
        {0.64, 1}
    }
})

hl.animation({
    leaf = "windowsIn",
    enabled = true,
    speed = 6,
    bezier = "bounce",
    style = "popin 70%"
})

hl.animation({
    leaf = "workspaces",
    enabled = true,
    speed = 6,
    bezier = "bounce",
    style = "slide"
})

-- Fade
hl.curve("fade", {
    type = "bezier",
    points = {
        {0.25, 0.1},
        {0.25, 1.0}
    }
})

hl.animation({
    leaf = "fade",
    enabled = true,
    speed = 4,
    bezier = "fade"
})

-- Slide
hl.curve("slide", {
    type = "bezier",
    points = {
        {0.25, 0.1},
        {0.25, 1.0}
    }
})

hl.animation({
    leaf = "windows",
    enabled = true,
    speed = 4,
    bezier = "slide",
    style = "slide"
})


hl.animation({
    leaf = "workspaces",
    enabled = true,
    speed = 4,
    bezier = "slide",
    style = "slide"
})

