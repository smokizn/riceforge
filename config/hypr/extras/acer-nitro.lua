-- Riceforge extra: Acer Nitro / Predator laptops (tested on a Nitro ANV15-41).
-- Fn+F4 (XF86Launch6) toggles every internal mic; the "P" key (XF86Presentation)
-- flips DAMX fan mode. Fan control needs the out-of-tree linuwu_sense driver and
-- DAMX daemon, which Riceforge does not install (see docs/HARDWARE.md).
hl.bind("XF86Launch6", hl.dsp.exec_cmd("bash ~/.config/waybar/scripts/mic_toggle_click.sh"),
    { description = "Utilities: Mic toggle" })
hl.bind("XF86Presentation", hl.dsp.exec_cmd("~/.config/hypr/hyprland/scripts/damx_toggle.py"),
    { description = "Utilities: DamX toggle" })
