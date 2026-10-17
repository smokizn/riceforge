-- Riceforge extra: NVIDIA as the primary (display) GPU. Selected by the nvidia
-- profile. Not needed on hybrid laptops where the iGPU drives the panel.
-- Riceforge never installs or replaces GPU drivers; install nvidia-open or
-- nvidia yourself (https://wiki.archlinux.org/title/NVIDIA).
hl.env("LIBVA_DRIVER_NAME", "nvidia")
hl.env("__GLX_VENDOR_LIBRARY_NAME", "nvidia")
