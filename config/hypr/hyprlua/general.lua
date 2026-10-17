
hl.monitor({
    output = "",
    mode = "preferred",
    position = "auto",
    scale = 1
})

hl.gesture({
    fingers = 3,
    direction = "swipe",
    action = "move"
})

hl.gesture({
    fingers = 3,
    direction = "pinch",
    action = "float"
})

hl.gesture({
    fingers = 4,
    direction = "horizontal",
    action = "workspace"
})

hl.config({
    gestures = {
        workspace_swipe_distance = 700,
        workspace_swipe_cancel_ratio = 0.2,
        workspace_swipe_min_speed_to_force = 5,
        workspace_swipe_direction_lock = true,
        workspace_swipe_direction_lock_threshold = 10,
        workspace_swipe_create_new = true
    },

    general = {
        gaps_in = 2,
        gaps_out = 2,
        gaps_workspaces = 5,

        border_size = 2,

        col = {
            active_border = "rgba(0DB7D455)",
            inactive_border = "rgba(31313600)"
        },

        resize_on_border = true,
        no_focus_fallback = true,

        snap = {
            enabled = true,
            window_gap = 4,
            monitor_gap = 5,
            respect_gaps = true
        }
    },

    dwindle = {
        preserve_split = true
    },

    decoration = {
        rounding = 20,
        rounding_power = 2.4,
        
        shadow = {
            enabled = true,
            range = 4,
            offset = {0, 4},
            render_power = 3,
            color = "rgba(1a1a1aee)"
        }
    },

    input = {
        kb_layout = "us",
        numlock_by_default = true,
        repeat_delay = 250,
        repeat_rate = 35,

        follow_mouse = 1,
        off_window_axis_events = 2,

        touchpad = {
            natural_scroll = true,
            disable_while_typing = true,
            clickfinger_behavior = true,
            scroll_factor = 0.7
        }
    },

    misc = {
        disable_hyprland_logo = true,
        disable_splash_rendering = true,

        mouse_move_enables_dpms = true,
        key_press_enables_dpms = true,

        animate_manual_resizes = false,
        animate_mouse_windowdragging = false,

        enable_swallow = false,

        on_focus_under_fullscreen = 2,
        allow_session_lock_restore = true,
        session_lock_xray = true,
        initial_workspace_tracking = false,
        focus_on_activate = true
    },

    binds = {
        scroll_event_delay = 0,
        hide_special_on_workspace_change = true
    },

    cursor = {
        zoom_factor = 1,
        zoom_rigid = false,
        zoom_disable_aa = true,
        hotspot_padding = 1
    }
})

