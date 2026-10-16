"""Bluetooth: a BlueZ model fed by BlueZ's own D-Bus signals, a pairing agent,
and the panel.

The model is GetManagedObjects once, then InterfacesAdded/Removed and
PropertiesChanged; bluetoothd restarts are followed through a name watch.
No polling, no bluetoothctl. Every call has a bounded timeout and errors are
reported as BlueZ states them. Pairing and connecting are kept distinct.
"""
import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Gtk4LayerShell", "1.0")
from gi.repository import Gio, GLib, Gtk, Gtk4LayerShell as LS  # noqa: E402

import netlogic as L  # noqa: E402
from common import TEST, Panel, button, clear, debounce, icon, label, section, set_icon  # noqa: E402

BLUEZ = "org.bluez"
ADAPTER = "org.bluez.Adapter1"
DEVICE = "org.bluez.Device1"
BATTERY = "org.bluez.Battery1"
AGENT_PATH = "/dev/riceforge/agent"
DISCOVERY_S = 30
TIMEOUT_MS = {"Pair": 45_000, "Connect": 25_000, "Disconnect": 10_000, "default": 10_000}

AGENT_XML = """
<node><interface name="org.bluez.Agent1">
  <method name="Release"/>
  <method name="RequestPinCode"><arg type="o" direction="in"/><arg type="s" direction="out"/></method>
  <method name="DisplayPinCode"><arg type="o" direction="in"/><arg type="s" direction="in"/></method>
  <method name="RequestPasskey"><arg type="o" direction="in"/><arg type="u" direction="out"/></method>
  <method name="DisplayPasskey"><arg type="o" direction="in"/><arg type="u" direction="in"/><arg type="q" direction="in"/></method>
  <method name="RequestConfirmation"><arg type="o" direction="in"/><arg type="u" direction="in"/></method>
  <method name="RequestAuthorization"><arg type="o" direction="in"/></method>
  <method name="AuthorizeService"><arg type="o" direction="in"/><arg type="s" direction="in"/></method>
  <method name="Cancel"/>
</interface></node>
"""

# a few service UUIDs worth naming in an authorization prompt
SERVICES = {
    "0000110b": "audio playback", "0000110a": "audio source", "0000111e": "hands-free calls",
    "00001108": "headset", "00001124": "keyboard/mouse input", "0000110e": "media controls",
    "0000110c": "media controls", "00001105": "file transfer",
}


class BtState:
    def __init__(self):
        self.bus = Gio.bus_get_sync(Gio.BusType.SYSTEM)
        self.objects = {}          # path -> {iface: {prop: value}}
        self.owner = None          # unique name of org.bluez, when present
        self.listeners = []
        self.busy = {}             # device path -> operation name
        self.errors = {}           # device path -> last error text
        self.discovery_timer = 0
        self._notify = debounce(self._emit, 80)
        self.agent = None
        for member, cb in (("InterfacesAdded", self._on_added), ("InterfacesRemoved", self._on_removed)):
            self.bus.signal_subscribe(BLUEZ, "org.freedesktop.DBus.ObjectManager", member, None, None,
                                      Gio.DBusSignalFlags.NONE, cb)
        self.bus.signal_subscribe(BLUEZ, "org.freedesktop.DBus.Properties", "PropertiesChanged", None, None,
                                  Gio.DBusSignalFlags.NONE, self._on_props)
        Gio.bus_watch_name_on_connection(self.bus, BLUEZ, Gio.BusNameWatcherFlags.NONE,
                                         self._appeared, self._vanished)

    # ── plumbing ──
    def subscribe(self, fn):
        self.listeners.append(fn); fn()

    def _emit(self):
        for fn in list(self.listeners):
            fn()

    def _appeared(self, _conn, _name, owner):
        self.owner = owner

        def got(conn, res):
            try:
                objs = conn.call_finish(res).unpack()[0]
            except GLib.Error as e:
                self.errors["*"] = e.message; self._notify(); return
            self.objects = {p: {i: dict(props) for i, props in ifs.items()} for p, ifs in objs.items()}
            self._notify()
            if self.agent:
                self.agent.register()
        self.bus.call(BLUEZ, "/", "org.freedesktop.DBus.ObjectManager", "GetManagedObjects",
                      None, None, Gio.DBusCallFlags.NONE, 5000, None, got)

    def _vanished(self, *_):
        self.owner = None
        self.objects = {}
        self._notify()

    def _on_added(self, _c, _s, _p, _i, _sig, params):
        path, ifaces = params.unpack()
        self.objects.setdefault(path, {}).update({i: dict(p) for i, p in ifaces.items()})
        self._notify()

    def _on_removed(self, _c, _s, _p, _i, _sig, params):
        path, ifaces = params.unpack()
        obj = self.objects.get(path, {})
        for i in ifaces:
            obj.pop(i, None)
        if not obj:
            self.objects.pop(path, None)
            self.busy.pop(path, None); self.errors.pop(path, None)
        self._notify()

    def _on_props(self, _c, _s, path, _i, _sig, params):
        iface, changed, invalidated = params.unpack()
        if path not in self.objects or iface not in (ADAPTER, DEVICE, BATTERY):
            return
        props = self.objects[path].setdefault(iface, {})
        props.update(changed)
        for k in invalidated:
            props.pop(k, None)
        self._notify()

    # ── queries ──
    def adapter_path(self):
        for p, ifs in sorted(self.objects.items()):
            if ADAPTER in ifs:
                return p
        return None

    def adapter(self):
        p = self.adapter_path()
        return self.objects[p][ADAPTER] if p else None

    def devices(self):
        out = []
        for p, ifs in self.objects.items():
            d = ifs.get(DEVICE)
            if not d:
                continue
            out.append({
                "path": p, "address": d.get("Address", ""),
                "name": d.get("Alias") or d.get("Name") or d.get("Address", ""),
                "unnamed": L.looks_unnamed(d.get("Alias"), d.get("Address")) and not d.get("Name"),
                "kind": L.bt_kind(d.get("Icon", ""), d.get("Alias") or d.get("Name") or ""),
                "paired": bool(d.get("Paired")), "trusted": bool(d.get("Trusted")),
                "connected": bool(d.get("Connected")), "rssi": d.get("RSSI"),
                "battery": ifs.get(BATTERY, {}).get("Percentage"),
                "blocked": bool(d.get("Blocked")),
            })
        return out

    def summary(self):
        if not self.owner:
            return {"state": "unavailable", "detail": "bluetoothd is not running"}
        a = self.adapter()
        if not a:
            return {"state": "unavailable", "detail": "No Bluetooth adapter"}
        if not a.get("Powered"):
            return {"state": "off"}
        conn = [d for d in self.devices() if d["connected"]]
        return {"state": "connected" if conn else "on", "devices": conn,
                "discovering": bool(a.get("Discovering"))}

    # ── calls ──
    def call(self, path, iface, method, params=None, done=None, timeout=None):
        to = timeout or TIMEOUT_MS.get(method, TIMEOUT_MS["default"])

        def finished(conn, res):
            try:
                conn.call_finish(res)
                err = None
            except GLib.Error as e:
                name = Gio.DBusError.get_remote_error(e) or ""
                Gio.DBusError.strip_remote_error(e)
                err = (name, e.message)
            if done:
                done(err)
        self.bus.call(BLUEZ, path, iface, method, params, None, Gio.DBusCallFlags.NONE, to, None, finished)

    def set_prop(self, path, iface, prop, variant, done=None):
        self.bus.call(BLUEZ, path, "org.freedesktop.DBus.Properties", "Set",
                      GLib.Variant("(ssv)", (iface, prop, variant)), None, Gio.DBusCallFlags.NONE,
                      TIMEOUT_MS["default"], None, lambda c, r: self._set_done(c, r, done))

    def _set_done(self, conn, res, done):
        try:
            conn.call_finish(res); err = None
        except GLib.Error as e:
            name = Gio.DBusError.get_remote_error(e) or ""
            Gio.DBusError.strip_remote_error(e)
            err = (name, e.message)
        if done:
            done(err)

    def set_powered(self, on, done=None):
        p = self.adapter_path()
        if p:
            self.set_prop(p, ADAPTER, "Powered", GLib.Variant("b", on), done)

    def start_discovery(self, done=None):
        p = self.adapter_path()
        if not p or (self.adapter() or {}).get("Discovering"):
            return
        self.call(p, ADAPTER, "StartDiscovery", None, done)
        if self.discovery_timer:
            GLib.source_remove(self.discovery_timer)
        self.discovery_timer = GLib.timeout_add_seconds(DISCOVERY_S, self._auto_stop)

    def _auto_stop(self):
        self.discovery_timer = 0
        self.stop_discovery()
        return False

    def stop_discovery(self, done=None):
        p = self.adapter_path()
        if p and (self.adapter() or {}).get("Discovering"):
            self.call(p, ADAPTER, "StopDiscovery", None, done)
        if self.discovery_timer:
            GLib.source_remove(self.discovery_timer); self.discovery_timer = 0

    def device_op(self, path, method, on_done=None):
        """Pair / Connect / Disconnect with per-device busy + error tracking."""
        if path in self.busy:
            return
        self.busy[path] = method
        self.errors.pop(path, None)
        self._notify()

        def done(err):
            self.busy.pop(path, None)
            if err:
                name, msg = err
                if method == "Pair" and name in ("org.freedesktop.DBus.Error.NoReply",
                                                 "org.bluez.Error.AuthenticationTimeout"):
                    self.call(path, DEVICE, "CancelPairing")
                self.errors[path] = L.explain_bt_error(name, msg)
            elif method == "Pair":
                # a paired device should be allowed to come back on its own
                self.set_prop(path, DEVICE, "Trusted", GLib.Variant("b", True))
            self._notify()
            if on_done:
                on_done(err)
        self.call(path, DEVICE, method, None, done)

    def forget(self, path, done=None):
        a = self.adapter_path()
        if a:
            self.call(a, ADAPTER, "RemoveDevice", GLib.Variant("(o)", (path,)), done)

    def name_of(self, path):
        d = self.objects.get(path, {}).get(DEVICE, {})
        return d.get("Alias") or d.get("Name") or d.get("Address") or path.rsplit("/", 1)[-1]


class AgentPrompt(Gtk.Window):
    """a small modal plate for pairing questions (works with the panel closed)."""

    def __init__(self, app):
        super().__init__(application=app)
        self.add_css_class("rf-window")
        LS.init_for_window(self)
        LS.set_namespace(self, "riceforge-prompt")
        LS.set_layer(self, LS.Layer.OVERLAY)
        LS.set_keyboard_mode(self, LS.KeyboardMode.NONE if TEST else LS.KeyboardMode.EXCLUSIVE)
        LS.set_anchor(self, LS.Edge.TOP, True)
        LS.set_margin(self, LS.Edge.TOP, 120)
        self.set_default_size(420, -1)
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        box.add_css_class("rf-plate"); box.add_css_class("rf-prompt")
        head = Gtk.Box(spacing=12)
        head.append(icon("bluetooth", "brass", 26))
        col = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        col.append(label("PAIRING", "rf-eyebrow"))
        self.title = label("", "rf-title", wrap=True)
        col.append(self.title)
        head.append(col)
        box.append(head)
        rule = Gtk.Box(); rule.add_css_class("rf-double-rule"); box.append(rule)
        self.text = label("", "rf-prompt-text", wrap=True)
        box.append(self.text)
        self.code = label("", "rf-passkey", xalign=0.5)
        box.append(self.code)
        self.entry = Gtk.Entry(); self.entry.add_css_class("rf-entry")
        box.append(self.entry)
        self.buttons = Gtk.Box(spacing=8, halign=Gtk.Align.END)
        box.append(self.buttons)
        self.set_child(box)
        self.respond = None
        keys = Gtk.EventControllerKey()
        keys.connect("key-pressed", self._key)
        self.add_controller(keys)

    def _key(self, _c, keyval, _code, _state):
        from gi.repository import Gdk
        if keyval == Gdk.KEY_Escape and self.respond:
            self.respond("reject")
            return True
        return False

    def ask(self, title, text, code=None, entry=None, actions=(("Reject", "reject"), ("Accept", "accept")),
            respond=None):
        self.title.set_text(title)
        self.text.set_text(text)
        self.code.set_visible(code is not None)
        self.code.set_text(code or "")
        self.entry.set_visible(entry is not None)
        self.entry.set_text("")
        if entry is not None:
            self.entry.set_placeholder_text(entry)
        clear(self.buttons)
        self.respond = None

        def make(cb_value):
            def handler():
                r, self.respond = self.respond, None
                self.set_visible(False)
                if r:
                    r(cb_value)
            return handler
        for i, (text_, value) in enumerate(actions):
            cls = "rf-primary" if i == len(actions) - 1 else "rf-ghost"
            self.buttons.append(button(text_, None, cls, on_click=make(value)))
        self.respond = respond
        self.present()
        if entry is not None:
            GLib.idle_add(self.entry.grab_focus)

    def dismiss(self):
        self.respond = None
        self.set_visible(False)


class Agent:
    """org.bluez.Agent1, answering only to bluetoothd itself."""

    def __init__(self, app, bt):
        self.app, self.bt = app, bt
        self.prompt = AgentPrompt(app)
        self.pending = None
        self.state = "exported (test mode: not registered)" if TEST else "registering"
        info = Gio.DBusNodeInfo.new_for_xml(AGENT_XML).interfaces[0]
        self.reg_id = bt.bus.register_object(AGENT_PATH, info, self._method, None, None)
        bt.agent = self
        if bt.owner:
            self.register()

    def register(self):
        if TEST:
            return

        def after_register(err):
            if err and "AlreadyExists" not in err[0]:
                self.state = f"RegisterAgent failed: {err[1]}"
                print(f"agent: {self.state}", flush=True); return

            def after_default(e):
                self.state = f"registered, not default ({e[1]})" if e else "registered as default agent"
                if e:
                    print(f"agent: {self.state}", flush=True)
            self.bt.call("/org/bluez", "org.bluez.AgentManager1", "RequestDefaultAgent",
                         GLib.Variant("(o)", (AGENT_PATH,)), after_default)
        self.bt.call("/org/bluez", "org.bluez.AgentManager1", "RegisterAgent",
                     GLib.Variant("(os)", (AGENT_PATH, "KeyboardDisplay")), after_register)

    def unregister(self):
        try:
            self.bt.bus.call_sync(BLUEZ, "/org/bluez", "org.bluez.AgentManager1", "UnregisterAgent",
                                  GLib.Variant("(o)", (AGENT_PATH,)), None, Gio.DBusCallFlags.NONE, 2000, None)
        except GLib.Error:
            pass

    def _method(self, _conn, sender, _path, _iface, method, params, inv):
        if not self.bt.owner or sender != self.bt.owner:
            inv.return_dbus_error("org.bluez.Error.Rejected", "Only bluetoothd may talk to this agent")
            return
        args = params.unpack()
        name = self.bt.name_of(args[0]) if args else ""
        reject = lambda: inv.return_dbus_error("org.bluez.Error.Rejected", "Rejected by user")  # noqa: E731

        if method == "Release":
            inv.return_value(None)
        elif method == "Cancel":
            self.prompt.dismiss()
            inv.return_value(None)
        elif method == "RequestConfirmation":
            code = f"{args[1]:06d}"
            self.prompt.ask(f"Pair with {name}?", "Confirm that this number is shown on the device.",
                            code=code, respond=lambda v: inv.return_value(None) if v == "accept" else reject())
        elif method == "DisplayPasskey":
            self.prompt.ask(f"Pairing with {name}", "Type this passkey on the device, then press Enter on it.",
                            code=f"{args[1]:06d}", actions=(("Hide", "ok"),), respond=lambda v: None)
            inv.return_value(None)
        elif method == "DisplayPinCode":
            self.prompt.ask(f"Pairing with {name}", "Enter this PIN on the device.",
                            code=str(args[1]), actions=(("Hide", "ok"),), respond=lambda v: None)
            inv.return_value(None)
        elif method == "RequestPinCode":
            def answer(v):
                pin = self.prompt.entry.get_text().strip()
                if v == "accept" and 1 <= len(pin) <= 16 and pin.isprintable():
                    inv.return_value(GLib.Variant("(s)", (pin,)))
                else:
                    reject()
            self.prompt.ask(f"PIN for {name}", "Enter the PIN the device expects (often 0000 or 1234).",
                            entry="PIN", respond=answer)
        elif method == "RequestPasskey":
            def answer(v):
                t = self.prompt.entry.get_text().strip()
                if v == "accept" and t.isdigit() and int(t) <= 999999:
                    inv.return_value(GLib.Variant("(u)", (int(t),)))
                else:
                    reject()
            self.prompt.ask(f"Passkey for {name}", "Enter the 6-digit passkey shown on the device.",
                            entry="000000", respond=answer)
        elif method == "RequestAuthorization":
            self.prompt.ask(f"Allow {name} to pair?", "The device is asking to pair with this computer.",
                            respond=lambda v: inv.return_value(None) if v == "accept" else reject())
        elif method == "AuthorizeService":
            path, uuid = args
            what = SERVICES.get(uuid[:8].lower(), "a service")

            def answer(v):
                if v == "reject":
                    reject(); return
                if v == "always":
                    self.bt.set_prop(path, DEVICE, "Trusted", GLib.Variant("b", True))
                inv.return_value(None)
            self.prompt.ask(f"Allow {name}?", f"{name} wants to use {what}.",
                            actions=(("Deny", "reject"), ("Allow once", "once"), ("Always allow", "always")),
                            respond=answer)
        else:
            inv.return_dbus_error("org.bluez.Error.Rejected", "Unsupported")


class BtPanel(Panel):
    def __init__(self, app, bt):
        super().__init__(app, title="Bluetooth", eyebrow="RESONANCE", icon_name="bluetooth", width=420)
        self.bt = bt
        self.armed = set()        # device paths whose forget button is armed
        self.power = Gtk.Switch(valign=Gtk.Align.CENTER, tooltip_text="Bluetooth power")
        self.power_handler = self.power.connect("state-set", self._on_power)
        self.discover_btn = button(None, "search", "rf-ghost", tooltip="Search for devices",
                                   on_click=self._toggle_discovery)
        self.head_extra.append(self.discover_btn)
        self.head_extra.append(self.power)
        self.message = label("", "rf-empty", wrap=True)
        self.sections = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=14)
        self.body.append(self.message)
        self.body.append(self.sections)
        bt.subscribe(self.refresh)

    def on_show(self):
        self.refresh()

    def hide(self):
        # leaving the panel ends a search we started; pairing in progress keeps its own timeout
        self.bt.stop_discovery()
        super().hide()

    def _on_power(self, _sw, state):
        self.set_status("Powering " + ("on…" if state else "off…"), busy=True)

        def done(err):
            if err:
                self.set_status(L.explain_bt_error(*err), "error")
            else:
                self.set_status("")
            self.refresh()
        self.bt.set_powered(state, done)
        return False

    def _toggle_discovery(self):
        a = self.bt.adapter() or {}
        if a.get("Discovering"):
            self.bt.stop_discovery()
        else:
            self.bt.start_discovery(lambda err: self.set_status(L.explain_bt_error(*err), "error") if err else None)

    def refresh(self):
        s = self.bt.summary()
        st = s["state"]
        self.power.handler_block(self.power_handler)
        self.power.set_active(st in ("on", "connected"))
        self.power.set_sensitive(st != "unavailable")
        self.power.handler_unblock(self.power_handler)
        discovering = s.get("discovering", False)
        self.discover_btn.set_sensitive(st in ("on", "connected"))
        if discovering:
            self.discover_btn.add_css_class("rf-active")
            if not any(self.bt.busy.values()):
                self.set_status("Searching for devices… put new devices in pairing mode.", busy=True)
        else:
            self.discover_btn.remove_css_class("rf-active")
            if self.status.has_css_class("rf-status-busy") and not self.bt.busy:
                self.set_status("")
        if st == "connected":
            names = ", ".join(d["name"] for d in s["devices"])
            self.subtitle.set_text(f"Connected · {names}")
            set_icon(self.head_icon, "bluetooth-connected")
        else:
            self.subtitle.set_text({"on": "On", "off": "Off", "unavailable": s.get("detail", "")}.get(st, ""))
            set_icon(self.head_icon, "bluetooth" if st == "on" else "bluetooth-off")

        clear(self.sections)
        self.message.set_visible(st in ("off", "unavailable"))
        self.message.set_text("Bluetooth is off." if st == "off" else s.get("detail", ""))
        if st in ("off", "unavailable"):
            return
        devs = self.bt.devices()
        groups = [
            ("Connected", [d for d in devs if d["connected"]]),
            ("Paired", [d for d in devs if d["paired"] and not d["connected"]]),
            ("Nearby", [d for d in devs if not d["paired"] and not d["connected"]
                        and d["rssi"] is not None and not d["unnamed"]]),
        ]
        hidden = sum(1 for d in devs if not d["paired"] and d["unnamed"] and d["rssi"] is not None)
        for title, items in groups:
            if not items and title != "Nearby":
                continue
            if title == "Nearby" and not items and not discovering:
                continue
            sec = section(title)
            lb = Gtk.ListBox(selection_mode=Gtk.SelectionMode.NONE)
            lb.add_css_class("rf-list")
            for d in sorted(items, key=lambda d: (-(d["rssi"] or -999), d["name"].lower())):
                lb.append(self._row(d))
            if title == "Nearby" and not items:
                lb.append(label("Listening… nothing named in range yet.", "rf-empty"))
            sec.append(lb)
            if title == "Nearby" and hidden:
                sec.append(label(f"{hidden} unnamed device{'s' if hidden != 1 else ''} not shown.", "rf-row-sub"))
            self.sections.append(sec)

    def _row(self, d):
        row = Gtk.ListBoxRow(activatable=False)
        row.add_css_class("rf-row")
        outer = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        top = Gtk.Box(spacing=12)
        top.append(icon(d["kind"], "brass" if d["connected"] else "silver", 22))
        col = Gtk.Box(orientation=Gtk.Orientation.VERTICAL); col.set_hexpand(True)
        col.append(label(d["name"], "rf-row-title", ellipsize=True))
        bits = []
        if d["connected"]:
            bits.append("connected")
        elif d["paired"]:
            bits.append("paired · not connected")
        if d["battery"] is not None:
            bits.append(f"battery {d['battery']}%")
        if d["paired"] and not d["trusted"]:
            bits.append("not trusted")
        if d["rssi"] is not None and not d["connected"]:
            bits.append(f"{d['rssi']} dBm")
        if d["blocked"]:
            bits.append("blocked")
        col.append(label(" · ".join(bits), "rf-row-sub"))
        top.append(col)
        busy = self.bt.busy.get(d["path"])
        if busy:
            top.append(label({"Pair": "pairing…", "Connect": "connecting…", "Disconnect": "disconnecting…"}
                             .get(busy, "working…"), "rf-row-sub"))
            top.append(Gtk.Spinner(spinning=True))
        else:
            err = d["path"] in self.bt.errors
            if d["connected"]:
                top.append(button("Disconnect", None, "rf-quiet",
                                  on_click=lambda: self.bt.device_op(d["path"], "Disconnect")))
            elif d["paired"]:
                top.append(button("Retry" if err else "Connect", None, "rf-quiet",
                                  on_click=lambda: self.bt.device_op(d["path"], "Connect")))
            else:
                top.append(button("Retry" if err else "Pair", None, "rf-quiet",
                                  on_click=lambda: self._pair_then_connect(d["path"])))
            if d["paired"]:
                f = button(None, "forget", "rf-ghost",
                           tooltip="Click twice to forget this device", on_click=lambda: self._forget(d))
                if d["path"] in self.armed:
                    f.add_css_class("rf-danger")
                top.append(f)
        outer.append(top)
        if d["path"] in self.bt.errors:
            outer.append(label(self.bt.errors[d["path"]], "rf-warn", wrap=True))
        row.set_child(outer)
        return row

    def _pair_then_connect(self, path):
        self.set_status(f"Pairing with {self.bt.name_of(path)}… confirm on the device if asked.", busy=True)

        def paired(err):
            if err:
                self.set_status("Pairing failed.", "error"); return
            self.set_status("Paired. Connecting…", busy=True)
            self.bt.device_op(path, "Connect",
                              lambda e: self.set_status("Paired, but the connection failed." if e else
                                                        f"Connected to {self.bt.name_of(path)}.",
                                                        "error" if e else "ok"))
        self.bt.device_op(path, "Pair", paired)

    def _forget(self, d):
        p = d["path"]
        if p not in self.armed:
            self.armed.add(p)
            self.set_status(f"Click the bin again to forget {d['name']} (removes the pairing).", "info")
            GLib.timeout_add_seconds(4, lambda: (self.armed.discard(p), self.refresh(), False)[2])
            self.refresh()
            return
        self.armed.discard(p)
        self.bt.forget(p, lambda err: self.set_status(L.explain_bt_error(*err) if err else
                                                      f"Forgot {d['name']}.", "error" if err else "info"))
