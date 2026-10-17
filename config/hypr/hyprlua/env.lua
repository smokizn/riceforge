local home_dir = os.getenv("HOME")

-- Wayland
hl.env("ELECTRON_OZONE_PLATFORM_HINT", "auto")

-- Applications
hl.env(
    "XDG_DATA_DIRS",
    home_dir ..
    "/.local/share/flatpak/exports/share:/var/lib/flatpak/exports/share:/usr/local/share:/usr/share"
)

-- Themes
hl.env("QT_QPA_PLATFORM", "wayland;xcb")
hl.env("QT_QPA_PLATFORMTHEME", "qt6ct")
-- dolphin finds its "Open with" menus through the plasma menu prefix
hl.env("XDG_MENU_PREFIX", "plasma-")

-- Terminal
hl.env("TERMINAL", "kitty -1")

-- GPU-specific variables (NVIDIA etc.) live in ~/.config/riceforge-local/hypr.lua
