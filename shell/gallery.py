"""The plate archive: a keyboard-driven wallpaper gallery.

Backends: awww (real crossfade) when awww-daemon is running, otherwise
swaybg swapped without a black flash (start the new one, retire the old one
once it has mapped). The chosen plate is persisted by re-pointing the
theme's wallpaper.png symlink, which hyprlock and the session also read.
"""
import json
import os
import shutil
import subprocess
from pathlib import Path

import gi

gi.require_version("GdkPixbuf", "2.0")
from gi.repository import GdkPixbuf, GLib, Gtk  # noqa: E402

from common import CURRENT, Panel, button, clear, icon, label  # noqa: E402

USER_WALLS = Path.home() / "Pictures/Wallpapers"
CACHE = Path.home() / ".cache/riceforge/thumbs"
IMAGE_EXT = {".png", ".jpg", ".jpeg", ".webp"}


class WallpaperBackend:
    def describe(self):
        return "awww (crossfade)" if self._awww() else "swaybg (instant)"

    def _awww(self):
        return shutil.which("awww") and subprocess.run(["pgrep", "-x", "awww-daemon"],
                                                       capture_output=True).returncode == 0

    @staticmethod
    def loadable(path):
        try:
            fmt, w, h = GdkPixbuf.Pixbuf.get_file_info(str(path))
            return fmt is not None and w > 0 and h > 0
        except GLib.Error:
            return False

    def show(self, path, done=None):
        """display path now (preview or apply). done(error_or_None)."""
        path = str(path)
        if not self.loadable(path):
            if done:
                done("This image cannot be decoded.")
            return
        if self._awww():
            try:
                subprocess.Popen(["awww", "img", path, "--transition-type", "fade",
                                  "--transition-duration", "0.8", "--transition-fps", "120"],
                                 stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                if done:
                    done(None)
            except OSError as e:
                if done:
                    done(str(e))
            return
        old = subprocess.run(["pgrep", "-x", "swaybg"], capture_output=True, text=True).stdout.split()
        try:
            subprocess.Popen(["swaybg", "-m", "fill", "-i", path], stdout=subprocess.DEVNULL,
                             stderr=subprocess.DEVNULL, start_new_session=True)
        except OSError as e:
            if done:
                done(str(e))
            return

        def retire():
            for pid in old:
                try:
                    os.kill(int(pid), 15)
                except (ProcessLookupError, ValueError):
                    pass
            return False
        GLib.timeout_add(450, retire)
        if done:
            done(None)


def thumb_for(path):
    """cached 384x216 thumbnail for an arbitrary image."""
    CACHE.mkdir(parents=True, exist_ok=True)
    st = path.stat()
    t = CACHE / f"{path.stem}-{int(st.st_mtime)}-{st.st_size}.png"
    if not t.exists():
        pb = GdkPixbuf.Pixbuf.new_from_file_at_scale(str(path), 384, 216, True)
        pb.savev(str(t), "png", [], [])
    return t


class GalleryPanel(Panel):
    def __init__(self, app, backend):
        super().__init__(app, title="The Plate Archive", eyebrow="TABULAE", icon_name="frame",
                         width=1240, anchor=(), margins=(0, 0, 0, 0))
        self.add_css_class("rf-gallery")
        self.backend = backend
        self.plates = []
        self.active_target = None
        self.previewing = None
        self._preview_id = 0
        self.scroller.set_max_content_height(640)

        self.flow = Gtk.FlowBox(selection_mode=Gtk.SelectionMode.SINGLE, homogeneous=True,
                                max_children_per_line=4, min_children_per_line=4,
                                row_spacing=14, column_spacing=14, activate_on_single_click=False)
        self.flow.add_css_class("rf-flow")
        self.flow.connect("selected-children-changed", self._on_select)
        self.flow.connect("child-activated", lambda *_: self.apply_selected())
        self.body.append(self.flow)

        self.detail = Gtk.Box(spacing=16)
        self.detail.add_css_class("rf-card")
        self.d_title = label("", "rf-row-title")
        self.d_meta = label("", "rf-row-sub", wrap=True)
        self.d_attr = label("", "rf-attrib", wrap=True)
        col = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2); col.set_hexpand(True)
        for w in (self.d_title, self.d_meta, self.d_attr):
            col.append(w)
        self.detail.append(col)
        self.apply_btn = button("Set as wallpaper", None, "rf-primary", on_click=self.apply_selected)
        self.apply_btn.set_valign(Gtk.Align.CENTER)
        self.detail.append(self.apply_btn)
        self.body.append(self.detail)
        self.body.append(label("←→↑↓ browse · Space preview on the desktop · Enter set · Esc close", "rf-hint",
                               xalign=0.5))

    # ── data ──
    def _load(self):
        plates = []
        idx = CURRENT / "wallpapers" / "plates.json"
        try:
            for p in json.loads(idx.read_text()):
                f = CURRENT / "wallpapers" / p["file"]
                if p.get("local") and not f.exists():
                    continue          # machine-local plate (not distributed); absent here
                t = CURRENT / "wallpapers" / "thumbs" / (Path(p["file"]).stem + ".jpg")
                plates.append({**p, "path": f, "thumb": t, "ok": f.exists() and self.backend.loadable(f),
                               "group": "Plates"})
        except (OSError, ValueError) as e:
            self.set_status(f"Could not read the plate index: {e}", "error")
        if USER_WALLS.is_dir():
            for f in sorted(USER_WALLS.iterdir()):
                if f.suffix.lower() in IMAGE_EXT and f.is_file():
                    ok = self.backend.loadable(f)
                    plates.append({"id": f"user:{f.name}", "title": f.stem, "path": f, "ok": ok,
                                   "thumb": None, "category": "your collection", "palette": "original",
                                   "origin": "~/Pictures/Wallpapers", "attribution": None,
                                   "group": "Your wallpapers"})
        self.plates = plates

    def _active_path(self):
        link = CURRENT / "wallpaper.png"
        try:
            return link.resolve(strict=True)
        except OSError:
            return None

    # ── lifecycle ──
    def on_show(self):
        self._load()
        self.active_target = self._active_path()
        self.previewing = None
        clear(self.flow)
        select = None
        for p in self.plates:
            child = Gtk.FlowBoxChild()
            child.plate = p
            child.add_css_class("rf-tile")
            box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
            frame = Gtk.Overlay()
            pic = Gtk.Picture()
            pic.set_content_fit(Gtk.ContentFit.COVER)
            pic.set_size_request(280, 158)
            pic.add_css_class("rf-thumb")
            try:
                t = p["thumb"] if p["thumb"] and p["thumb"].exists() else (thumb_for(p["path"]) if p["ok"] else None)
                if t:
                    pic.set_filename(str(t))
            except GLib.Error:
                p["ok"] = False
            frame.set_child(pic)
            if not p["ok"]:
                miss = label("missing or unreadable", "rf-missing", xalign=0.5)
                miss.set_valign(Gtk.Align.CENTER)
                frame.add_overlay(miss)
                child.set_sensitive(False)
            is_active = self.active_target is not None and Path(p["path"]).resolve() == self.active_target
            if is_active:
                badge = Gtk.Box(spacing=4, halign=Gtk.Align.END, valign=Gtk.Align.START)
                badge.add_css_class("rf-badge")
                badge.append(icon("star-filled", "brass", 12))
                badge.append(label("active", "rf-badge-text"))
                frame.add_overlay(badge)
                child.add_css_class("rf-tile-active")
                select = child
            box.append(frame)
            box.append(label(p["title"], "rf-tile-title", ellipsize=True))
            box.append(label(p.get("category", ""), "rf-tile-sub", ellipsize=True))
            child.set_child(box)
            self.flow.append(child)
        first = select or self.flow.get_child_at_index(0)
        if first:
            self.flow.select_child(first)
            GLib.idle_add(first.grab_focus)
        self.set_status(f"Backend: {self.backend.describe()}", "info")

    def hide(self):
        # leaving without Enter puts the active wallpaper back
        if self.previewing is not None and self.active_target is not None and \
                self.previewing != self.active_target:
            self.backend.show(self.active_target)
        self.previewing = None
        super().hide()

    def on_key(self, keyval):
        from gi.repository import Gdk
        if keyval == Gdk.KEY_space:
            p = self._selected()
            if p and p["ok"]:
                self._preview(p)
            return True
        return False

    # ── selection ──
    def _selected(self):
        sel = self.flow.get_selected_children()
        return sel[0].plate if sel else None

    def _on_select(self, *_):
        p = self._selected()
        if not p:
            return
        self.d_title.set_text(p["title"])
        meta = [p.get("category", ""), p.get("palette", ""), p.get("aspect", ""), p.get("origin", "")]
        self.d_meta.set_text(" · ".join(m for m in meta if m))
        a = p.get("attribution")
        self.d_attr.set_text(f"Source: {a['artist'] or 'unknown'}, “{a['title']}”, {a['licence']}. {a['page']}"
                             if a else ("Procedural engraving, drawn for this theme." if p.get("origin") == "procedural"
                                        else ""))
        self.apply_btn.set_sensitive(p["ok"])

    def _preview(self, p):
        target = Path(p["path"]).resolve()
        if target == self.previewing:
            return
        self.previewing = target
        self.backend.show(target, lambda err: self.set_status(f"Preview failed: {err}", "error") if err
                          else self.set_status(f"Previewing “{p['title']}”. Enter to keep, Esc to revert.", "info"))

    def apply_selected(self):
        p = self._selected()
        if not p or not p["ok"]:
            return
        target = Path(p["path"]).resolve()

        def shown(err):
            if err:
                self.set_status(f"Could not set wallpaper: {err}", "error"); return
            try:
                persist(target)
            except OSError as e:
                self.set_status(f"Shown, but could not remember the choice: {e}", "error"); return
            self.active_target = target
            self.previewing = target
            self.set_status(f"“{p['title']}” is now the wallpaper.", "ok")
            self.on_show()
        self.backend.show(target, shown)


def persist(target):
    """atomically re-point <theme>/wallpaper.png at target (relative when inside the theme)."""
    theme = (CURRENT).resolve()
    link = theme / "wallpaper.png"
    try:
        rel = os.path.relpath(target, theme)
        dest = rel if not rel.startswith("..") else str(target)
    except ValueError:
        dest = str(target)
    tmp = theme / ".wallpaper.png.tmp"
    if tmp.is_symlink() or tmp.exists():
        tmp.unlink()
    os.symlink(dest, tmp)
    os.replace(tmp, link)


def ensure_valid_wallpaper(backend):
    """at session start: if the remembered plate is gone, fall back to the first good plate."""
    link = CURRENT / "wallpaper.png"
    if link.exists() and backend.loadable(link):
        return str(link)
    try:
        for p in json.loads((CURRENT / "wallpapers" / "plates.json").read_text()):
            f = CURRENT / "wallpapers" / p["file"]
            if f.exists() and backend.loadable(f):
                persist(f.resolve())
                return str(f)
    except (OSError, ValueError):
        pass
    return None
