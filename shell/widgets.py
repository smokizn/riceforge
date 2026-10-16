"""Desktop instruments on the BOTTOM layer: the astrolabe and the strip.

Surfaces are sized to their content (no fullscreen layer), so they never take
clicks meant for windows; windows simply cover them. Data comes from the
shared NetState/BtState plus UPower and MPRIS signals; CPU and memory are read
from /proc every few seconds in-process (no subprocesses).
"""
import math
import os
from datetime import datetime

import gi

gi.require_version("PangoCairo", "1.0")
from gi.repository import Gio, GLib, Gtk, Gtk4LayerShell as LS, Pango, PangoCairo  # noqa: E402

import astro  # noqa: E402
import netlogic as L  # noqa: E402
from common import CURRENT, TEST, Panel, icon, label, set_icon  # noqa: E402

PARCHMENT = (0.84, 0.80, 0.70)
BONE = (0.90, 0.87, 0.81)
STONE = (0.43, 0.42, 0.39)
SILVER = (0.73, 0.74, 0.76)
BRASS = (0.70, 0.60, 0.37)
INK = (0.04, 0.04, 0.04)


def draw_moon(cr, cx, cy, r, frac, waxing):
    """engraved moon: silver limb, lit part washed, dark part hatched."""
    c = math.cos(2 * math.pi * frac)
    cr.save()
    cr.arc(cx, cy, r, 0, 2 * math.pi)
    cr.clip()
    # dark side: fine diagonal hatch
    cr.set_source_rgba(*STONE, 0.55)
    cr.set_line_width(0.7)
    for k in range(-int(r * 2), int(r * 2), 3):
        cr.move_to(cx + k - r, cy - r); cr.line_to(cx + k + r, cy + r)
    cr.stroke()
    # lit side, sampled row by row
    cr.set_source_rgba(*PARCHMENT, 0.92)
    steps = max(24, int(r))
    left, right = [], []
    for i in range(steps + 1):
        y = -r + 2 * r * i / steps
        s = math.sqrt(max(r * r - y * y, 0))
        a, b = (c * s, s) if waxing else (-s, -c * s)
        left.append((cx + a, cy + y)); right.append((cx + b, cy + y))
    cr.move_to(*left[0])
    for p in left[1:]:
        cr.line_to(*p)
    for p in reversed(right):
        cr.line_to(*p)
    cr.close_path(); cr.fill()
    cr.restore()
    cr.set_source_rgba(*SILVER, 0.95); cr.set_line_width(1.2)
    cr.arc(cx, cy, r, 0, 2 * math.pi); cr.stroke()


def _text(cr, s, x, y, size, rgb, family="Cormorant SC, Noto Serif", center=True):
    layout = PangoCairo.create_layout(cr)
    layout.set_font_description(Pango.FontDescription.from_string(f"{family} {size}"))
    layout.set_text(s, -1)
    w, h = layout.get_pixel_size()
    cr.set_source_rgb(*rgb)
    cr.move_to(x - (w / 2 if center else 0), y - h / 2)
    PangoCairo.show_layout(cr, layout)


class Astrolabe(Gtk.DrawingArea):
    SIZE = 236

    def __init__(self, cfg, on_click):
        super().__init__()
        self.cfg = cfg
        self.set_content_width(self.SIZE); self.set_content_height(self.SIZE)
        self.set_draw_func(self._draw)
        click = Gtk.GestureClick(); click.connect("released", lambda *_: on_click())
        self.add_controller(click)
        self.set_cursor_from_name("pointer")

    @staticmethod
    def angle(minutes):
        return math.pi / 2 + 2 * math.pi * minutes / 1440.0

    def _draw(self, _a, cr, w, h):
        cx, cy = w / 2, h / 2
        R = min(w, h) / 2 - 6
        now = datetime.now().astimezone()
        lat, lon = self.cfg["lat"], self.cfg["lon"]
        sd = astro.sun_day(now.date(), lat, lon)
        moon = astro.moon_at()
        # face: a dark, slightly translucent disc so it reads over any plate
        cr.set_source_rgba(*INK, 0.55); cr.arc(cx, cy, R, 0, 2 * math.pi); cr.fill()
        cr.set_source_rgba(*SILVER, 0.75); cr.set_line_width(1.2)
        cr.arc(cx, cy, R, 0, 2 * math.pi); cr.stroke()
        cr.set_line_width(0.6); cr.arc(cx, cy, R - 5, 0, 2 * math.pi); cr.stroke()
        # 24 hours of ticks, 96 quarter ticks
        for i in range(96):
            a = self.angle(i * 15)
            r1 = R - 6
            r2 = r1 - (9 if i % 24 == 0 else 6 if i % 4 == 0 else 3)
            cr.set_source_rgba(*BONE, 0.85 if i % 4 == 0 else 0.45)
            cr.set_line_width(1.0 if i % 4 == 0 else 0.6)
            cr.move_to(cx + r1 * math.cos(a), cy + r1 * math.sin(a))
            cr.line_to(cx + r2 * math.cos(a), cy + r2 * math.sin(a)); cr.stroke()
        for mins, txt in ((0, "XXIV"), (360, "VI"), (720, "XII"), (1080, "XVIII")):
            a = self.angle(mins)
            _text(cr, txt, cx + (R - 26) * math.cos(a), cy + (R - 26) * math.sin(a), 9, BONE)
        # daylight band, hatched like an engraved arc
        rin, rout = R - 44, R - 34
        if sd.polar != "night":
            if sd.polar == "day":
                a0, a1 = 0, 2 * math.pi
            else:
                rise = sd.sunrise.astimezone(); sset = sd.sunset.astimezone()
                a0 = self.angle(rise.hour * 60 + rise.minute)
                a1 = self.angle(sset.hour * 60 + sset.minute)
                if a1 < a0:
                    a1 += 2 * math.pi
            cr.set_source_rgba(*PARCHMENT, 0.7); cr.set_line_width(0.8)
            n = int((a1 - a0) / (2 * math.pi) * 220)
            for i in range(n + 1):
                a = a0 + (a1 - a0) * i / max(n, 1)
                cr.move_to(cx + rin * math.cos(a), cy + rin * math.sin(a))
                cr.line_to(cx + rout * math.cos(a), cy + rout * math.sin(a))
            cr.stroke()
            cr.set_line_width(0.6)
            cr.arc(cx, cy, rout + 1.5, a0, a1); cr.stroke()
        # night band: a dotted ring
        cr.set_source_rgba(*SILVER, 0.45); cr.set_dash([0.8, 3.2]); cr.set_line_width(0.9)
        cr.arc(cx, cy, (rin + rout) / 2, 0, 2 * math.pi); cr.stroke(); cr.set_dash([])
        # the alidade: a hand to the present minute, sun or moon at its tip
        m = now.hour * 60 + now.minute
        a = self.angle(m)
        is_day = sd.polar == "day" or (sd.polar is None and sd.sunrise <= now <= sd.sunset)
        tip = (rin + rout) / 2
        cr.set_source_rgba(*(BRASS if is_day else SILVER), 0.9); cr.set_line_width(1.0)
        cr.move_to(cx + 44 * math.cos(a), cy + 44 * math.sin(a))
        cr.line_to(cx + (tip - 9) * math.cos(a), cy + (tip - 9) * math.sin(a)); cr.stroke()
        tx, ty = cx + tip * math.cos(a), cy + tip * math.sin(a)
        if is_day:
            cr.set_source_rgb(*BRASS)
            cr.arc(tx, ty, 5.5, 0, 2 * math.pi); cr.fill()
            cr.set_line_width(0.9)
            for i in range(12):
                b = i * math.pi / 6
                cr.move_to(tx + 7.5 * math.cos(b), ty + 7.5 * math.sin(b))
                cr.line_to(tx + 11 * math.cos(b), ty + 11 * math.sin(b))
            cr.stroke()
        else:
            cr.set_source_rgb(*SILVER)
            cr.arc(tx, ty, 6, 0, 2 * math.pi); cr.fill()
            cr.set_source_rgba(*INK, 1)
            cr.arc(tx + 3, ty - 2, 5.2, 0, 2 * math.pi); cr.fill()
        # the moon at the centre, its actual phase
        draw_moon(cr, cx, cy, 34, moon.fraction, moon.waxing)


class MoonPanel(Panel):
    def __init__(self, app, cfg):
        super().__init__(app, title="Luna", eyebrow="EPHEMERIS", icon_name="moon-4", width=380,
                         anchor=("bottom", "right"), margins=(0, 60, 380, 0))
        self.cfg = cfg
        self.area = Gtk.DrawingArea(content_width=150, content_height=150, halign=Gtk.Align.CENTER)
        self.area.set_draw_func(self._draw)
        self.body.append(self.area)
        self.grid = Gtk.Grid(column_spacing=18, row_spacing=6)
        self.grid.add_css_class("rf-ephemeris")
        self.body.append(self.grid)
        self.note = label("", "rf-row-sub", wrap=True)
        self.body.append(self.note)

    def _draw(self, _a, cr, w, h):
        m = astro.moon_at()
        draw_moon(cr, w / 2, h / 2, min(w, h) / 2 - 4, m.fraction, m.waxing)

    def on_show(self):
        m = astro.moon_at()
        now = datetime.now().astimezone()
        sd = astro.sun_day(now.date(), self.cfg["lat"], self.cfg["lon"])
        set_icon(self.head_icon, f"moon-{m.index}")
        self.subtitle.set_text(f"{m.name} · {m.illumination * 100:.0f}% lit")
        rows = [("Phase", m.name), ("Illumination", f"{m.illumination * 100:.1f}%"),
                ("Age", f"{m.age_days:.1f} days"),
                ("Next full moon", m.next_full.astimezone().strftime("%a %d %b, %H:%M")),
                ("Next new moon", m.next_new.astimezone().strftime("%a %d %b, %H:%M"))]
        if sd.polar is None:
            dl = sd.day_length
            rows += [("Sunrise", sd.sunrise.astimezone().strftime("%H:%M")),
                     ("Sunset", sd.sunset.astimezone().strftime("%H:%M")),
                     ("Day length", f"{dl.seconds // 3600} h {dl.seconds % 3600 // 60:02d} m")]
        else:
            rows.append(("Sun", "polar day" if sd.polar == "day" else "polar night"))
        child = self.grid.get_first_child()
        while child:
            nxt = child.get_next_sibling(); self.grid.remove(child); child = nxt
        for i, (k, v) in enumerate(rows):
            self.grid.attach(label(k, "rf-row-sub"), 0, i, 1, 1)
            self.grid.attach(label(v, "rf-row-title"), 1, i, 1, 1)
        self.note.set_text(f"Sun times for {self.cfg['place']} ({self.cfg['lat']:.2f}, {self.cfg['lon']:.2f}); "
                           "set your location in ~/.config/riceforge/shell/config.toml.")
        self.area.queue_draw()


class SysStat:
    def __init__(self):
        self.prev = None

    def cpu(self):
        with open("/proc/stat") as f:
            parts = [int(x) for x in f.readline().split()[1:]]
        idle, total = parts[3] + parts[4], sum(parts)
        if self.prev is None:
            self.prev = (idle, total); return 0
        di, dt = idle - self.prev[0], total - self.prev[1]
        self.prev = (idle, total)
        return 0 if dt <= 0 else round(100 * (1 - di / dt))

    @staticmethod
    def mem():
        info = {}
        with open("/proc/meminfo") as f:
            for line in f:
                k, v = line.split(":", 1)
                info[k] = int(v.split()[0])
                if len(info) > 8 and "MemAvailable" in info:
                    break
        return round(100 * (1 - info["MemAvailable"] / info["MemTotal"]))


class Power:
    def __init__(self, on_change):
        self.proxy = None
        try:
            self.proxy = Gio.DBusProxy.new_for_bus_sync(
                Gio.BusType.SYSTEM, Gio.DBusProxyFlags.NONE, None, "org.freedesktop.UPower",
                "/org/freedesktop/UPower/devices/DisplayDevice", "org.freedesktop.UPower.Device", None)
            self.proxy.connect("g-properties-changed", lambda *_: on_change())
        except GLib.Error:
            self.proxy = None

    def state(self):
        if not self.proxy:
            return None
        pct = self.proxy.get_cached_property("Percentage")
        st = self.proxy.get_cached_property("State")
        present = self.proxy.get_cached_property("IsPresent")
        if pct is None or (present is not None and not present.unpack()):
            return None
        return round(pct.unpack()), (st.unpack() if st else 0)


class Media:
    """the most relevant MPRIS player, followed by signals."""

    def __init__(self, on_change):
        self.on_change = on_change
        self.bus = Gio.bus_get_sync(Gio.BusType.SESSION)
        self.players = {}
        self.bus.signal_subscribe("org.freedesktop.DBus", "org.freedesktop.DBus", "NameOwnerChanged",
                                  "/org/freedesktop/DBus", None, Gio.DBusSignalFlags.NONE, self._owner)
        names = self.bus.call_sync("org.freedesktop.DBus", "/org/freedesktop/DBus", "org.freedesktop.DBus",
                                   "ListNames", None, None, Gio.DBusCallFlags.NONE, 2000, None).unpack()[0]
        for n in names:
            if n.startswith("org.mpris.MediaPlayer2."):
                self._add(n)

    def _owner(self, _c, _s, _p, _i, _sig, params):
        name, old, new = params.unpack()
        if not name.startswith("org.mpris.MediaPlayer2."):
            return
        if new:
            self._add(name)
        else:
            self.players.pop(name, None)
        self.on_change()

    def _add(self, name):
        def ready(_src, res):
            try:
                p = Gio.DBusProxy.new_for_bus_finish(res)
            except GLib.Error:
                return
            p.connect("g-properties-changed", lambda *_: self.on_change())
            self.players[name] = p
            self.on_change()
        Gio.DBusProxy.new_for_bus(Gio.BusType.SESSION, Gio.DBusProxyFlags.NONE, None, name,
                                  "/org/mpris/MediaPlayer2", "org.mpris.MediaPlayer2.Player", None, ready)

    def current(self):
        best = None
        for name, p in self.players.items():
            st = p.get_cached_property("PlaybackStatus")
            st = st.unpack() if st else "Stopped"
            md = p.get_cached_property("Metadata")
            md = md.unpack() if md else {}
            title = md.get("xesam:title") or ""
            artist = ", ".join(md.get("xesam:artist") or [])
            rank = {"Playing": 2, "Paused": 1}.get(st, 0)
            if title and (best is None or rank > best[0]):
                best = (rank, name, st, title, artist)
        return best

    def play_pause(self):
        b = self.current()
        if b:
            self.players[b[1]].call("PlayPause", None, Gio.DBusCallFlags.NONE, 2000, None, None)


def trunc(text, n=20):
    """deliberate truncation: ellipsizing labels collapse inside a content-sized layer surface."""
    text = text or ""
    return text if len(text) <= n else text[:n - 1].rstrip() + "…"


class Desk(Gtk.Window):
    """the astrolabe and the instrument strip, bottom-right on the desktop layer."""

    def __init__(self, app, cfg, net, bt, actions):
        super().__init__(application=app)
        self.add_css_class("rf-window")
        LS.init_for_window(self)
        LS.set_namespace(self, "riceforge-widget")
        # (test mode can lift the desk above windows to inspect it; never in real use)
        LS.set_layer(self, LS.Layer.OVERLAY if TEST and os.environ.get("RICEFORGE_DESK_OVERLAY") else LS.Layer.BOTTOM)
        LS.set_keyboard_mode(self, LS.KeyboardMode.NONE)
        LS.set_exclusive_zone(self, 0)
        LS.set_anchor(self, LS.Edge.BOTTOM, True); LS.set_anchor(self, LS.Edge.RIGHT, True)
        LS.set_margin(self, LS.Edge.BOTTOM, cfg["margin_bottom"]); LS.set_margin(self, LS.Edge.RIGHT, cfg["margin_right"])
        self.cfg, self.net, self.bt, self.actions = cfg, net, bt, actions
        root = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10, halign=Gtk.Align.END)
        root.add_css_class("rf-desk")
        self.set_child(root)

        if cfg["astrolabe"]:
            dial_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2, halign=Gtk.Align.CENTER)
            dial_box.add_css_class("rf-astrolabe")
            self.dial = Astrolabe(cfg, actions["moon"])
            dial_box.append(self.dial)
            self.time_l = label("", "rf-desk-time", xalign=0.5)
            self.date_l = label("", "rf-desk-date", xalign=0.5)
            self.sky_l = label("", "rf-desk-sky", xalign=0.5)
            for w in (self.time_l, self.date_l, self.sky_l):
                dial_box.append(w)
            root.append(dial_box)
        else:
            self.dial = None

        self.strip = Gtk.Box(spacing=6, halign=Gtk.Align.END)
        self.strip.add_css_class("rf-strip")
        if cfg["strip"]:
            root.append(self.strip)
        self.chips = {}
        for key, ic in (("wifi", "wifi-0"), ("bt", "bluetooth"), ("battery", "battery-2"),
                        ("media", "music"), ("sys", "cpu"), ("wall", "frame")):
            b = Gtk.Button(); b.add_css_class("rf-chip")
            box = Gtk.Box(spacing=6)
            im = icon(ic, "bone", 14)
            lb = label("", "rf-chip-text")
            box.append(im); box.append(lb)
            b.set_child(box)
            self.strip.append(b)
            self.chips[key] = (b, im, lb)
        self.chips["wifi"][0].connect("clicked", lambda *_: actions["wifi"]())
        self.chips["bt"][0].connect("clicked", lambda *_: actions["bluetooth"]())
        self.chips["wall"][0].connect("clicked", lambda *_: actions["wallpapers"]())
        self.chips["sys"][0].connect("clicked", lambda *_: None)
        self.media = Media(self.update)
        self.chips["media"][0].connect("clicked", lambda *_: self.media.play_pause())
        self.power = Power(self.update)
        self.stat = SysStat()
        net.subscribe(self.update)
        bt.subscribe(self.update)
        self._tick()
        GLib.timeout_add_seconds(3, self._tick)

    def _tick(self):
        now = datetime.now().astimezone()
        if self.dial:
            self.time_l.set_text(now.strftime("%H:%M"))
            self.date_l.set_text(now.strftime("%A · %-d %B"))
            m = astro.moon_at()
            sd = astro.sun_day(now.date(), self.cfg["lat"], self.cfg["lon"])
            sun = (f"☉ {sd.sunrise.astimezone():%H:%M} – {sd.sunset.astimezone():%H:%M}"
                   if sd.polar is None else "☉ " + sd.polar)
            self.sky_l.set_text(f"{sun}   ☾ {m.name.lower()} {m.illumination * 100:.0f}%")
            self.dial.queue_draw()
        b, im, lb = self.chips["sys"]
        lb.set_text(f"{self.stat.cpu()}% · {self.stat.mem()}%")
        b.set_tooltip_text("CPU · memory in use")
        return True

    def update(self):
        s = self.net.summary()
        b, im, lb = self.chips["wifi"]
        if s["state"] == "connected":
            set_icon(im, f"wifi-{L.signal_level(s['strength'])}"); lb.set_text(trunc(s["ssid"], 16))
        elif s["state"] == "connecting":
            set_icon(im, "wifi-0"); lb.set_text("connecting…")
        else:
            set_icon(im, "wifi-off"); lb.set_text({"off": "wifi off", "unavailable": "no wifi"}.get(s["state"], "offline"))
        b.set_tooltip_text("Wi-Fi: open the network panel")

        t = self.bt.summary()
        b, im, lb = self.chips["bt"]
        if t["state"] == "connected":
            set_icon(im, "bluetooth-connected")
            d = t["devices"][0]
            lb.set_text(trunc(d["name"], 16) + (f" · {d['battery']}%" if d["battery"] is not None else ""))
        else:
            set_icon(im, "bluetooth" if t["state"] == "on" else "bluetooth-off")
            lb.set_text({"on": "on", "off": "off"}.get(t["state"], "n/a"))
        b.set_tooltip_text("Bluetooth: open the device panel")

        b, im, lb = self.chips["battery"]
        p = self.power.state()
        b.set_visible(p is not None)
        if p:
            pct, st = p
            set_icon(im, "battery-charging" if st in (1, 5) else f"battery-{min(4, pct // 21)}",
                     )
            lb.set_text(f"{pct}%")
            b.remove_css_class("rf-chip-critical")
            if pct <= 15 and st not in (1, 4, 5):
                b.add_css_class("rf-chip-critical")

        b, im, lb = self.chips["media"]
        cur = self.media.current()
        b.set_visible(cur is not None)
        if cur:
            _rank, _name, st, title, artist = cur
            lb.set_text(trunc(title if not artist else f"{title} · {artist}", 26))
            b.set_tooltip_text(f"{st}: click to play/pause")

        b, im, lb = self.chips["wall"]
        try:
            lb.set_text(trunc((CURRENT / "wallpaper.png").resolve().stem.replace("-", " "), 18))
        except OSError:
            lb.set_text("wallpaper")
        b.set_tooltip_text("Open the plate archive")
