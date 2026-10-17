-- Riceforge base Hyprland config (deployed as a symlink by ./setup).
-- Load order: base (hyprlua/) → your custom/ layer → monitors/workspaces →
-- machine-local overrides (~/.config/riceforge-local/hypr.lua) → theme look.
-- Machine-specific things (monitors, keyboard layout, GPU env) belong in the
-- local file, never in this tracked tree.

-- This file is a symlink into the Riceforge repo; Hyprland resolves it, so make
-- require() look in ~/.config/hypr first (custom/, monitors, riceforge theme layer).
do
    local hypr = os.getenv("HOME") .. "/.config/hypr/"
    package.path = hypr .. "?.lua;" .. hypr .. "?/init.lua;" .. package.path
end

-- Internal stuff --
require("hyprlua.lib")
require("hyprlua.services")
-- Environment variables --
require("hyprlua.env")
if is_file_exists(HOME .. "/.config/hypr/custom/env.lua") then
    require("custom.env")
end
-- default configs--
require("hyprlua.execs")
require("hyprlua.general")
require("hyprlua.rules")
require("hyprlua.colors")
require("hyprlua.keybinds")

-- custom configs--
if is_file_exists(HOME .. "/.config/hypr/custom/execs.lua") then
    require("custom.execs")
end

if is_file_exists(HOME .. "/.config/hypr/custom/general.lua") then
    require("custom.general")
end

if is_file_exists(HOME .. "/.config/hypr/custom/rules.lua") then
    require("custom.rules")
end

if is_file_exists(HOME .. "/.config/hypr/custom/keybinds.lua") then
    require("custom.keybinds")
end

-- Animations
if is_file_exists(HOME .. "/.config/hypr/hyprlua/animations.lua") then
    require("hyprlua.animations")
end

-- Workspaces / monitors
if is_file_exists(HOME .. "/.config/hypr/workspaces.lua") then
    require("workspaces")
end

if is_file_exists(HOME .. "/.config/hypr/monitors.lua") then
    require("monitors")
end

-- >>> riceforge machine layer >>>
if is_file_exists(HOME .. "/.config/riceforge-local/hypr.lua") then
    dofile(HOME .. "/.config/riceforge-local/hypr.lua")
end
-- <<< riceforge machine layer <<<

-- >>> riceforge theme layer >>>
if is_file_exists(HOME .. "/.config/hypr/riceforge.lua") then
    require("riceforge")
end
-- <<< riceforge theme layer <<<

-- Shell overrides
require("hyprlua.shellOverrides.main")
