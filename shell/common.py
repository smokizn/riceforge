"""Shared pieces for riceforge-shell: icons, the etched Panel, small widgets."""
import ctypes
import os
from pathlib import Path

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Gdk", "4.0")
gi.require_version("Gtk4LayerShell", "1.0")
from gi.repository import GLib, Gtk, Gtk4LayerShell as LS  # noqa: E402

RF = Path.home() / ".config/riceforge"
# test mode: separate instance, no keyboard grabs, no pairing-agent takeover
TEST = os.environ.get("RICEFORGE_SHELL_TEST") == "1"
CURRENT = RF / "current"


def set_process_name(name):
    """comm (as seen by pgrep -x / ps) instead of python3; max 15 bytes."""
    try:
        libc = ctypes.CDLL("libc.so.6")
        libc.prctl(15, ctypes.c_char_p(name.encode()[:15]), 0, 0, 0)  # PR_SET_NAME
    except OSError:
        pass


def icon_path(name, colour="bone"):
    p = CURRENT / "icons" / colour / f"{name}.svg"
    if p.exists():
        return str(p)
    p = CURRENT / "icons" / "bone" / f"{name}.svg"
    return str(p) if p.exists() else None


def icon(name, colour="bone", size=18):
    path = icon_path(name, colour)
    img = Gtk.Image.new_from_file(path) if path else Gtk.Image.new_from_icon_name("image-missing")
    img.set_pixel_size(size)
    img.add_css_class("rf-icon")
    return img


def set_icon(img, name, colour="bone"):
    path = icon_path(name, colour)
    if path:
        img.set_from_file(path)


def label(text="", *classes, xalign=0.0, wrap=False, ellipsize=False):
    lb = Gtk.Label(label=text, xalign=xalign)
    for c in classes:
        lb.add_css_class(c)
    if wrap:
        lb.set_wrap(True)
        lb.set_natural_wrap_mode(Gtk.NaturalWrapMode.WORD)
    if ellipsize:
        from gi.repository import Pango
        lb.set_ellipsize(Pango.EllipsizeMode.END)
    return lb


def button(text=None, icon_name=None, *classes, tooltip=None, on_click=None):
    b = Gtk.Button()
    box = Gtk.Box(spacing=6)
    if icon_name:
        box.append(icon(icon_name, "bone", 16))
    if text:
        box.append(Gtk.Label(label=text))
    b.set_child(box)
    for c in classes:
        b.add_css_class(c)
    if tooltip:
        b.set_tooltip_text(tooltip)
    if on_click:
        b.connect("clicked", lambda *_: on_click())
    return b


def clear(box):
    child = box.get_first_child()
    while child is not None:
        nxt = child.get_next_sibling()
        box.remove(child)
        child = nxt


def section(title):
    box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
    head = Gtk.Box(spacing=8)
    head.add_css_class("rf-section-head")
    head.append(label(title.upper(), "rf-section"))
    rule = Gtk.Box(); rule.set_hexpand(True); rule.add_css_class("rf-hairline"); rule.set_valign(Gtk.Align.CENTER)
    head.append(rule)
    box.append(head)
    return box


class Panel(Gtk.Window):
    """An etched plate floating on the overlay layer.

    Closes on Escape and when it loses focus (after having had it), so it
    behaves like a popover without a fullscreen click-catcher.
    """

    def __init__(self, app, *, title, eyebrow, icon_name, width=400,
                 anchor=("top", "right"), margins=(6, 10, 0, 0), keyboard=True):
        super().__init__(application=app)
        self.add_css_class("rf-window")
        self.set_decorated(False)
        self.set_default_size(width, -1)
        self.set_resizable(False)
        LS.init_for_window(self)
        LS.set_namespace(self, "riceforge-panel")
        LS.set_layer(self, LS.Layer.OVERLAY)
        LS.set_keyboard_mode(self, LS.KeyboardMode.ON_DEMAND if keyboard and not TEST
                             else LS.KeyboardMode.NONE)
        edges = {"top": LS.Edge.TOP, "right": LS.Edge.RIGHT, "bottom": LS.Edge.BOTTOM, "left": LS.Edge.LEFT}
        for name in anchor:
            LS.set_anchor(self, edges[name], True)
        for edge, m in zip((LS.Edge.TOP, LS.Edge.RIGHT, LS.Edge.BOTTOM, LS.Edge.LEFT), margins):
            LS.set_margin(self, edge, m)

        plate = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        plate.add_css_class("rf-plate")
        self.set_child(plate)

        head = Gtk.Box(spacing=12)
        head.add_css_class("rf-head")
        self.head_icon = icon(icon_name, "bone", 22)
        self.head_icon.add_css_class("rf-head-icon")
        head.append(self.head_icon)
        titles = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        titles.append(label(eyebrow, "rf-eyebrow"))
        self.title_label = label(title, "rf-title")
        titles.append(self.title_label)
        self.subtitle = label("", "rf-subtitle", ellipsize=True)
        titles.append(self.subtitle)
        titles.set_hexpand(True)
        head.append(titles)
        self.head_extra = Gtk.Box(spacing=6, valign=Gtk.Align.CENTER)
        head.append(self.head_extra)
        close = button(None, "close", "rf-ghost", tooltip="Close (Esc)", on_click=self.hide)
        close.set_valign(Gtk.Align.START)
        head.append(close)
        plate.append(head)

        rule = Gtk.Box(); rule.add_css_class("rf-double-rule")
        plate.append(rule)

        self.scroller = Gtk.ScrolledWindow()
        self.scroller.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        self.scroller.set_propagate_natural_height(True)
        self.scroller.set_max_content_height(560)
        self.body = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=14)
        self.body.add_css_class("rf-body")
        self.scroller.set_child(self.body)
        plate.append(self.scroller)

        foot = Gtk.Box(spacing=8)
        foot.add_css_class("rf-foot")
        self.spinner = Gtk.Spinner()
        foot.append(self.spinner)
        self.status = label("", "rf-status", wrap=True)
        self.status.set_hexpand(True)
        foot.append(self.status)
        plate.append(foot)

        keys = Gtk.EventControllerKey()
        keys.connect("key-pressed", self._on_key)
        self.add_controller(keys)
        self._had_focus = False
        self.connect("notify::is-active", self._on_active)
        self.connect("close-request", lambda *_: (self.hide(), True)[1])

    def _on_key(self, _ctl, keyval, _code, _state):
        from gi.repository import Gdk
        if keyval == Gdk.KEY_Escape:
            self.hide()
            return True
        return self.on_key(keyval)

    def on_key(self, keyval):
        return False

    def _on_active(self, *_):
        if self.is_active():
            self._had_focus = True
        elif self._had_focus and self.get_visible():
            GLib.timeout_add(180, self._hide_if_inactive)

    def _hide_if_inactive(self):
        if not self.is_active() and not getattr(self, "keep_open", False):
            self.hide()
        return False

    def hide(self):
        self.set_visible(False)

    def toggle(self):
        if self.get_visible():
            self.hide()
        else:
            self._had_focus = False
            self.on_show()
            self.present()

    def on_show(self):
        pass

    def set_status(self, text, kind="info", busy=False):
        self.status.set_text(text or "")
        for k in ("info", "error", "ok", "busy"):
            self.status.remove_css_class(f"rf-status-{k}")
        self.status.add_css_class(f"rf-status-{'busy' if busy else kind}")
        self.spinner.set_visible(busy)
        self.spinner.set_spinning(busy)


def debounce(fn, ms=200):
    """call fn at most once per `ms`, trailing."""
    state = {"id": 0}

    def fire():
        state["id"] = 0
        fn()
        return False

    def call(*_):
        if state["id"]:
            GLib.source_remove(state["id"])
        state["id"] = GLib.timeout_add(ms, fire)
    return call


def boottime_ms():
    import time
    return int(time.clock_gettime(time.CLOCK_BOOTTIME) * 1000)
