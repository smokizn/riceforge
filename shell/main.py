#!/usr/bin/env python3
"""riceforge-shell: panels and desk instruments for the active riceforge theme.

    riceforge-shell                 start (or keep) the resident instance
    riceforge-shell wifi|bluetooth|wallpapers|moon    toggle a panel
    riceforge-shell reload-style    re-read current/shell/style.css
    riceforge-shell status          print Wi-Fi/Bluetooth/wallpaper state (JSON)
    riceforge-shell quit

Single instance on the session bus (dev.riceforge.Shell); later invocations
forward their arguments to the running one. Nothing listens on the network.
"""
import json
import signal
import sys
import tomllib
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

from common import CURRENT, TEST, set_process_name  # noqa: E402

set_process_name("riceforge-test" if TEST else "riceforge-shell")

import gi  # noqa: E402

gi.require_version("Gtk", "4.0")
gi.require_version("Gdk", "4.0")
from gi.repository import Gdk, Gio, GLib, Gtk  # noqa: E402

DEFAULTS = {"lat": 51.48, "lon": 0.0, "place": "Greenwich (default)",
            "astrolabe": True, "strip": True, "margin_bottom": 76, "margin_right": 64}
# tracked defaults, then the machine's own file (written by ./setup, never tracked)
CONFIG_FILES = (HERE / "config.toml", Path.home() / ".config/riceforge-local/shell.toml")


def merge_config(cfg, data):
    loc, wid = data.get("location", {}), data.get("widgets", {})
    if isinstance(loc.get("lat"), (int, float)) and -90 <= loc["lat"] <= 90:
        cfg["lat"] = float(loc["lat"])
    if isinstance(loc.get("lon"), (int, float)) and -180 <= loc["lon"] <= 180:
        cfg["lon"] = float(loc["lon"])
    if isinstance(loc.get("place"), str):
        cfg["place"] = loc["place"][:60]
    for k in ("astrolabe", "strip"):
        if isinstance(wid.get(k), bool):
            cfg[k] = wid[k]
    for k in ("margin_bottom", "margin_right"):
        if isinstance(wid.get(k), int) and 0 <= wid[k] <= 2000:
            cfg[k] = wid[k]


def load_config(files=CONFIG_FILES):
    cfg = dict(DEFAULTS)
    for p in files:
        if not p.exists():
            continue
        try:
            merge_config(cfg, tomllib.loads(p.read_text()))
        except (OSError, tomllib.TOMLDecodeError) as e:
            print(f"config: ignoring {p} ({e})", file=sys.stderr)
    return cfg


class Shell(Gtk.Application):
    def __init__(self):
        super().__init__(application_id="dev.riceforge.ShellTest" if TEST else "dev.riceforge.Shell",
                         flags=Gio.ApplicationFlags.HANDLES_COMMAND_LINE)
        self.started = False
        self.panels = {}
        self.css = None

    # ── startup ──
    def do_startup(self):
        Gtk.Application.do_startup(self)
        self.hold()                      # stay resident without windows
        self.cfg = load_config()
        self.reload_style()
        from wifi import NetState
        from bluetooth import Agent, BtState
        from gallery import WallpaperBackend, ensure_valid_wallpaper
        self.net = NetState()
        self.bt = BtState()
        self.agent = Agent(self, self.bt)
        self.backend = WallpaperBackend()
        ensure_valid_wallpaper(self.backend)
        if self.cfg["astrolabe"] or self.cfg["strip"]:
            from widgets import Desk
            self.desk = Desk(self, self.cfg, self.net, self.bt, {
                "wifi": lambda: self.toggle("wifi"), "bluetooth": lambda: self.toggle("bluetooth"),
                "wallpapers": lambda: self.toggle("wallpapers"), "moon": lambda: self.toggle("moon")})
            self.desk.present()
        try:
            from gi.repository import GLibUnix
            add_signal = GLibUnix.signal_add
        except ImportError:
            add_signal = GLib.unix_signal_add
        for sig in (signal.SIGTERM, signal.SIGINT):
            add_signal(GLib.PRIORITY_DEFAULT, sig, self._on_signal)
        self.started = True

    def do_shutdown(self):
        try:
            self.agent.unregister()
        except Exception:
            pass
        Gtk.Application.do_shutdown(self)

    def _on_signal(self):
        self.quit()
        return False

    def reload_style(self):
        display = Gdk.Display.get_default()
        if self.css:
            Gtk.StyleContext.remove_provider_for_display(display, self.css)
        self.css = Gtk.CssProvider()
        path = CURRENT / "shell" / "style.css"
        if path.exists():
            self.css.load_from_path(str(path))
        Gtk.StyleContext.add_provider_for_display(display, self.css, Gtk.STYLE_PROVIDER_PRIORITY_USER)

    # ── panels ──
    def panel(self, name):
        if name not in self.panels:
            if name == "wifi":
                from wifi import WifiPanel
                self.panels[name] = WifiPanel(self, self.net)
            elif name == "bluetooth":
                from bluetooth import BtPanel
                self.panels[name] = BtPanel(self, self.bt)
            elif name == "wallpapers":
                from gallery import GalleryPanel
                self.panels[name] = GalleryPanel(self, self.backend)
            elif name == "moon":
                from widgets import MoonPanel
                self.panels[name] = MoonPanel(self, self.cfg)
        return self.panels[name]

    def toggle(self, name):
        for other, p in self.panels.items():
            if other != name and p.get_visible():
                p.hide()
        self.panel(name).toggle()

    # ── command line (local or forwarded) ──
    def do_command_line(self, cmdline):
        args = cmdline.get_arguments()[1:]
        cmd = args[0] if args else ""
        if cmd in ("wifi", "bluetooth", "wallpapers", "moon"):
            self.toggle(cmd)
        elif cmd == "reload-style":
            self.reload_style()
        elif cmd == "status":
            cmdline.print_literal(json.dumps(self.status(), default=str) + "\n")
        elif cmd == "quit":
            self.quit()
        elif cmd not in ("", "start"):
            cmdline.printerr_literal(f"unknown command: {cmd}\n")
            return 2
        return 0

    def status(self):
        w = dict(self.net.summary()); w.pop("ac", None)
        b = self.bt.summary()
        if "devices" in b:
            b = {**b, "devices": [{k: d[k] for k in ("name", "kind", "battery", "trusted")} for d in b["devices"]]}
        try:
            wall = str((CURRENT / "wallpaper.png").resolve(strict=True))
        except OSError:
            wall = None
        return {"wifi": w, "bluetooth": b, "wallpaper": wall, "backend": self.backend.describe(),
                "panels_open": [n for n, p in self.panels.items() if p.get_visible()],
                "agent": self.agent.state}


def main():
    return Shell().run(sys.argv)


if __name__ == "__main__":
    sys.exit(main())
