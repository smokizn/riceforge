"""Wi-Fi: a shared NetworkManager client (NetState) and the panel.

Everything goes through libnm's async API and NM's own signals; nothing is
polled and no subprocesses are run. Passwords are handed straight to
NetworkManager (stored by NM itself, psk-flags 0) and never logged or
written anywhere by this code.
"""
import gi

gi.require_version("NM", "1.0")
from gi.repository import GLib, Gtk, NM  # noqa: E402

import netlogic as L  # noqa: E402
from common import (Panel, boottime_ms, button, clear, debounce, icon,  # noqa: E402
                    label, section, set_icon)

CONNECT_TIMEOUT_S = 45
SCAN_STALE_MS = 30_000


class NetState:
    """one NM client for the whole shell; notifies listeners on any change."""

    def __init__(self):
        self.client = None
        self.error = None
        self.listeners = []
        self._notify = debounce(self._emit, 120)
        NM.Client.new_async(None, self._on_client)

    # ── plumbing ──
    def subscribe(self, fn):
        self.listeners.append(fn)
        fn()

    def _emit(self):
        for fn in list(self.listeners):
            fn()

    def _on_client(self, _src, res):
        try:
            self.client = NM.Client.new_finish(res)
        except GLib.Error as e:
            self.error = f"NetworkManager is unavailable: {e.message}"
            self._notify(); return
        c = self.client
        for sig in ("device-added", "device-removed", "connection-added", "connection-removed",
                    "active-connection-added", "active-connection-removed",
                    "notify::wireless-enabled", "notify::nm-running", "notify::connectivity"):
            c.connect(sig, self._on_change)
        c.connect("device-added", lambda *_: self._wire_devices())
        self._wire_devices()
        self._notify()

    def _wire_devices(self):
        for d in self.wifi_devices():
            if getattr(d, "_rf_wired", False):
                continue
            d._rf_wired = True
            for sig in ("access-point-added", "access-point-removed", "state-changed",
                        "notify::active-access-point", "notify::last-scan"):
                d.connect(sig, self._on_change)

    def _on_change(self, *_):
        self._notify()

    # ── queries ──
    def running(self):
        return self.client is not None and self.client.get_nm_running()

    def wifi_devices(self):
        if not self.client:
            return []
        return [d for d in self.client.get_devices() if d.get_device_type() == NM.DeviceType.WIFI]

    def device(self):
        devs = self.wifi_devices()
        return devs[0] if devs else None

    def radio_on(self):
        return bool(self.client and self.client.wireless_get_enabled())

    def saved_wifi(self):
        if not self.client:
            return []
        out = []
        for c in self.client.get_connections():
            if c.get_connection_type() != "802-11-wireless":
                continue
            sw = c.get_setting_wireless()
            ssid = NM.utils_ssid_to_utf8(sw.get_ssid().get_data()) if sw and sw.get_ssid() else c.get_id()
            out.append((ssid, c))
        return out

    def saved_for(self, ssid):
        for s, c in self.saved_wifi():
            if s == ssid:
                return c
        return None

    def networks(self):
        dev = self.device()
        if not dev:
            return []
        aps = []
        for ap in dev.get_access_points():
            ssid_b = ap.get_ssid()
            ssid = NM.utils_ssid_to_utf8(ssid_b.get_data()) if ssid_b else ""
            aps.append(dict(ssid=ssid, strength=ap.get_strength(),
                            security=L.classify_security(int(ap.get_flags()), int(ap.get_wpa_flags()),
                                                         int(ap.get_rsn_flags())),
                            freq=ap.get_frequency(), path=ap.get_path(), bssid=ap.get_bssid()))
        return L.dedup_networks(aps)

    def summary(self):
        """compact state for the bar/widgets."""
        if not self.client:
            return {"state": "loading"}
        if not self.running():
            return {"state": "unavailable", "detail": "NetworkManager is not running"}
        dev = self.device()
        if not dev:
            return {"state": "unavailable", "detail": "No Wi-Fi adapter"}
        if not self.radio_on():
            return {"state": "off"}
        st = dev.get_state()
        ap = dev.get_active_access_point()
        if st == NM.DeviceState.ACTIVATED and ap:
            return {"state": "connected", "ssid": NM.utils_ssid_to_utf8(ap.get_ssid().get_data()),
                    "strength": ap.get_strength(),
                    "security": L.classify_security(int(ap.get_flags()), int(ap.get_wpa_flags()),
                                                    int(ap.get_rsn_flags())),
                    "freq": ap.get_frequency(), "ac": dev.get_active_connection()}
        if NM.DeviceState.PREPARE <= st < NM.DeviceState.ACTIVATED:
            ac = dev.get_active_connection()
            return {"state": "connecting", "ssid": ac.get_id() if ac else ""}
        return {"state": "disconnected"}


def _ip4(ac):
    try:
        cfg = ac.get_ip4_config()
        addrs = cfg.get_addresses() if cfg else []
        return addrs[0].get_address() if addrs else ""
    except Exception:
        return ""


def build_connection(ssid, security, password, hidden=False, autoconnect=True):
    con = NM.SimpleConnection.new()
    s_con = NM.SettingConnection.new()
    s_con.set_property(NM.SETTING_CONNECTION_ID, ssid)
    s_con.set_property(NM.SETTING_CONNECTION_UUID, NM.utils_uuid_generate())
    s_con.set_property(NM.SETTING_CONNECTION_TYPE, "802-11-wireless")
    s_con.set_property(NM.SETTING_CONNECTION_AUTOCONNECT, autoconnect)
    con.add_setting(s_con)
    s_wifi = NM.SettingWireless.new()
    s_wifi.set_property(NM.SETTING_WIRELESS_SSID, GLib.Bytes.new(ssid.encode()))
    s_wifi.set_property(NM.SETTING_WIRELESS_MODE, "infrastructure")
    if hidden:
        s_wifi.set_property(NM.SETTING_WIRELESS_HIDDEN, True)
    con.add_setting(s_wifi)
    if L.needs_password(security):
        s_sec = NM.SettingWirelessSecurity.new()
        km = L.key_mgmt_for(security)
        s_sec.set_property(NM.SETTING_WIRELESS_SECURITY_KEY_MGMT, km)
        if km == "none":   # WEP
            s_sec.set_property(NM.SETTING_WIRELESS_SECURITY_WEP_KEY0, password)
            s_sec.set_property(NM.SETTING_WIRELESS_SECURITY_WEP_KEY_TYPE, NM.WepKeyType.KEY)
        else:
            s_sec.set_property(NM.SETTING_WIRELESS_SECURITY_PSK, password)
        con.add_setting(s_sec)
    elif security == "owe":
        s_sec = NM.SettingWirelessSecurity.new()
        s_sec.set_property(NM.SETTING_WIRELESS_SECURITY_KEY_MGMT, "owe")
        con.add_setting(s_sec)
    for cls in (NM.SettingIP4Config, NM.SettingIP6Config):
        s = cls.new()
        s.set_property(NM.SETTING_IP_CONFIG_METHOD, "auto")
        con.add_setting(s)
    return con


class Attempt:
    """one connection attempt, judged only by NetworkManager's own state."""

    def __init__(self, panel, ssid, created=False):
        self.panel, self.ssid, self.created = panel, ssid, created
        self.ac = None
        self.done = False
        self.timer = GLib.timeout_add_seconds(CONNECT_TIMEOUT_S, self._timeout)

    def started(self, ac):
        self.ac = ac
        ac.connect("state-changed", self._on_state)
        self._on_state(ac, ac.get_state(), 0)

    def _on_state(self, ac, state, _reason):
        if self.done:
            return
        if state == NM.ActiveConnectionState.ACTIVATED:
            self._finish(True, f"Connected to {self.ssid}.")
        elif state == NM.ActiveConnectionState.DEACTIVATED:
            dev = self.panel.net.device()
            nick = ""
            if dev:
                nick = NM.DeviceStateReason(dev.get_state_reason()).value_nick
            kind, msg = L.explain_device_reason(nick)
            self._finish(False, msg, kind)

    def _timeout(self):
        self.timer = 0
        if not self.done:
            if self.ac:
                self.panel.net.client.deactivate_connection_async(self.ac, None, lambda *a: None)
            self._finish(False, f"Gave up after {CONNECT_TIMEOUT_S} s without a connection.", "error")
        return False

    def fail_early(self, message):
        self._finish(False, message, "error")

    def _finish(self, ok, message, kind="ok"):
        self.done = True
        if self.timer:
            GLib.source_remove(self.timer); self.timer = 0
        # a profile we created whose password was refused must not linger
        if not ok and self.created and kind == "secrets" and self.ac:
            rc = self.ac.get_connection()
            if rc:
                rc.delete_async(None, lambda *a: None)
        self.panel.attempt_finished(self, ok, message, kind)


class WifiPanel(Panel):
    def __init__(self, app, net):
        super().__init__(app, title="Wi-Fi", eyebrow="AETHER", icon_name="wifi-3", width=420)
        self.net = net
        self.attempt = None
        self.expanded = None           # ssid whose row is open
        self.scanning = False
        self.scan_timer = 0
        self.prompt_reason = {}        # ssid -> message shown over its password field

        self.radio = Gtk.Switch(valign=Gtk.Align.CENTER, tooltip_text="Wi-Fi radio")
        self.radio_handler = self.radio.connect("state-set", self._on_radio)
        self.scan_btn = button(None, "refresh", "rf-ghost", tooltip="Scan for networks", on_click=self.scan)
        self.head_extra.append(self.scan_btn)
        self.head_extra.append(self.radio)

        self.current_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        self.nearby_sec = section("Nearby")
        self.list = Gtk.ListBox(selection_mode=Gtk.SelectionMode.NONE)
        self.list.add_css_class("rf-list")
        self.nearby_sec.append(self.list)
        self.saved_exp = Gtk.Expander(label="Saved networks")
        self.saved_exp.add_css_class("rf-expander")
        self.saved_list = Gtk.ListBox(selection_mode=Gtk.SelectionMode.NONE)
        self.saved_list.add_css_class("rf-list")
        self.saved_exp.set_child(self.saved_list)
        self.hidden_exp = Gtk.Expander(label="Join a hidden network")
        self.hidden_exp.add_css_class("rf-expander")
        self.hidden_exp.set_child(self._hidden_form())
        self.message = label("", "rf-empty", wrap=True)
        for w in (self.message, self.current_box, self.nearby_sec, self.saved_exp, self.hidden_exp):
            self.body.append(w)
        net.subscribe(self.refresh)

    # ── lifecycle ──
    def on_show(self):
        self.refresh()
        dev = self.net.device()
        if dev and self.net.radio_on() and boottime_ms() - dev.get_last_scan() > SCAN_STALE_MS:
            self.scan()

    # ── actions ──
    def _on_radio(self, _sw, state):
        if not self.net.client:
            return True
        self.set_status("Turning Wi-Fi " + ("on…" if state else "off…"), busy=True)

        def done(c, res):
            try:
                c.dbus_set_property_finish(res)
                self.set_status("")
            except GLib.Error as e:
                self.set_status(f"Could not switch the radio: {e.message}", "error")
                self.refresh()
        self.net.client.dbus_set_property(NM.DBUS_PATH, NM.DBUS_INTERFACE, "WirelessEnabled",
                                          GLib.Variant("b", state), -1, None, done)
        return False

    def scan(self):
        dev = self.net.device()
        if not dev or self.scanning or not self.net.radio_on():
            return
        self.scanning = True
        self.scan_btn.set_sensitive(False)
        self.set_status("Scanning the air…", busy=True)
        before = dev.get_last_scan()

        def finished(d, res):
            try:
                d.request_scan_finish(res)
            except GLib.Error as e:
                # NM rate-limits scans; the list we already have is recent
                age = (boottime_ms() - d.get_last_scan()) // 1000
                self._end_scan(f"Showing results from {age} s ago ({e.message.rstrip('.')}).", "info")
                return
            # the request was accepted: wait for NM to publish new results
            def poll():
                if d.get_last_scan() != before:
                    self._end_scan("", "info"); return False
                return True
            self.scan_timer = GLib.timeout_add(250, poll)
            GLib.timeout_add_seconds(15, lambda: (self._end_scan("Scan took too long; showing what is known.", "info")
                                                  if self.scanning else None, False)[1])
        dev.request_scan_async(None, finished)

    def _end_scan(self, msg, kind):
        if self.scan_timer:
            GLib.source_remove(self.scan_timer); self.scan_timer = 0
        self.scanning = False
        self.scan_btn.set_sensitive(True)
        if not self.attempt:
            self.set_status(msg, kind)
        self.refresh()

    def connect_network(self, net, password=None, autoconnect=True):
        dev = self.net.device()
        if not dev or self.attempt:
            return
        saved = self.net.saved_for(net.ssid)
        self.set_status(f"Connecting to {net.ssid}…", busy=True)
        self.prompt_reason.pop(net.ssid, None)
        if saved and password is None:
            att = self.attempt = Attempt(self, net.ssid)

            def done(c, res):
                try:
                    att.started(c.activate_connection_finish(res))
                except GLib.Error as e:
                    att.fail_early(e.message)
            self.net.client.activate_connection_async(saved, dev, net.path, None, done)
        elif saved and password is not None:
            # the saved key was refused: update it in place, then retry
            att = self.attempt = Attempt(self, net.ssid)
            sec = saved.get_setting_wireless_security()
            if sec is None:
                att.fail_early("This saved profile has no security settings to update."); return
            if L.key_mgmt_for(net.security) == "none":
                sec.set_property(NM.SETTING_WIRELESS_SECURITY_WEP_KEY0, password)
            else:
                sec.set_property(NM.SETTING_WIRELESS_SECURITY_PSK, password)

            def committed(rc, res):
                try:
                    rc.commit_changes_finish(res)
                except GLib.Error as e:
                    att.fail_early(f"Could not update the saved password: {e.message}"); return

                def done(c, r2):
                    try:
                        att.started(c.activate_connection_finish(r2))
                    except GLib.Error as e:
                        att.fail_early(e.message)
                self.net.client.activate_connection_async(saved, dev, net.path, None, done)
            saved.commit_changes_async(True, None, committed)
        else:
            if net.security == "enterprise":
                self.set_status("Enterprise (802.1X) networks need the full editor: run nm-connection-editor.", "error")
                return
            con = build_connection(net.ssid, net.security, password or "", autoconnect=autoconnect)
            att = self.attempt = Attempt(self, net.ssid, created=True)

            def done(c, res):
                try:
                    att.started(c.add_and_activate_connection_finish(res))
                except GLib.Error as e:
                    att.fail_early(e.message)
            self.net.client.add_and_activate_connection_async(con, dev, net.path, None, done)
        self.refresh()

    def attempt_finished(self, att, ok, message, kind):
        if att is not self.attempt:
            return
        self.attempt = None
        if ok:
            self.expanded = None
            self.set_status(message, "ok")
        elif kind == "cancel":
            self.set_status(message, "info")
        else:
            if kind == "secrets":
                self.expanded = att.ssid
                self.prompt_reason[att.ssid] = message
            self.set_status(message, "error")
        self.refresh()

    def disconnect(self):
        dev = self.net.device()
        if not dev:
            return
        self.set_status("Disconnecting…", busy=True)

        def done(d, res):
            try:
                d.disconnect_finish(res)
                self.set_status("Disconnected.", "info")
            except GLib.Error as e:
                self.set_status(f"Could not disconnect: {e.message}", "error")
        dev.disconnect_async(None, done)

    def forget(self, ssid, conn):
        def done(c, res):
            try:
                c.delete_finish(res)
                self.set_status(f"Forgot {ssid}.", "info")
            except GLib.Error as e:
                self.set_status(f"Could not forget {ssid}: {e.message}", "error")
        conn.delete_async(None, done)

    def set_autoconnect(self, conn, value):
        s = conn.get_setting_connection()
        s.set_property(NM.SETTING_CONNECTION_AUTOCONNECT, value)

        def done(c, res):
            try:
                c.commit_changes_finish(res)
            except GLib.Error as e:
                self.set_status(f"Could not save: {e.message}", "error")
        conn.commit_changes_async(True, None, done)

    # ── rendering ──
    def refresh(self):
        s = self.net.summary()
        state = s["state"]
        self.radio.handler_block(self.radio_handler)
        self.radio.set_active(self.net.radio_on())
        self.radio.set_sensitive(state not in ("loading", "unavailable"))
        self.radio.handler_unblock(self.radio_handler)
        self.scan_btn.set_sensitive(not self.scanning and state not in ("off", "unavailable", "loading"))

        sub = {"loading": "Reading NetworkManager…", "unavailable": s.get("detail", ""), "off": "Radio off",
               "disconnected": "Not connected", "connecting": f"Connecting to {s.get('ssid', '')}…"}
        if state == "connected":
            sub_text = f"{s['ssid']} · {s['strength']}%"
            set_icon(self.head_icon, f"wifi-{L.signal_level(s['strength'])}")
        else:
            sub_text = sub.get(state, "")
            set_icon(self.head_icon, "wifi-off" if state in ("off", "unavailable") else "wifi-0")
        self.subtitle.set_text(sub_text)

        clear(self.current_box)
        visible = state in ("connected", "connecting", "disconnected")
        self.message.set_visible(not visible)
        self.message.set_text({"loading": "Reading NetworkManager…",
                               "unavailable": (self.net.error or s.get("detail", "")),
                               "off": "Wi-Fi is off. Turn the radio on to see networks."}.get(state, ""))
        for w in (self.nearby_sec, self.saved_exp, self.hidden_exp):
            w.set_visible(visible)
        if not visible:
            return
        if state == "connected":
            self.current_box.append(self._current_card(s))

        clear(self.list)
        nets = self.net.networks()
        current = s.get("ssid") if state == "connected" else None
        shown = 0
        for n in nets:
            if n.ssid == current:
                continue
            self.list.append(self._network_row(n))
            shown += 1
        if not shown:
            self.list.append(label("Nothing else in range." if not self.scanning else "Listening…", "rf-empty"))

        clear(self.saved_list)
        saved = self.net.saved_wifi()
        self.saved_exp.set_label(f"Saved networks ({len(saved)})")
        for ssid, conn in sorted(saved, key=lambda x: x[0].lower()):
            self.saved_list.append(self._saved_row(ssid, conn))

    def _current_card(self, s):
        card = Gtk.Box(spacing=12)
        card.add_css_class("rf-card"); card.add_css_class("rf-card-active")
        card.append(icon(f"wifi-{L.signal_level(s['strength'])}", "brass", 26))
        col = Gtk.Box(orientation=Gtk.Orientation.VERTICAL); col.set_hexpand(True)
        col.append(label(s["ssid"], "rf-row-title"))
        bits = [f"{s['strength']}%", L.SECURITY_LABEL.get(s["security"], ""), L.band(s["freq"])]
        ip = _ip4(s.get("ac")) if s.get("ac") else ""
        if ip:
            bits.append(ip)
        conn = self.net.client.get_connectivity() if self.net.client else None
        if conn == NM.ConnectivityState.PORTAL:
            bits.append("sign-in required")
        elif conn == NM.ConnectivityState.LIMITED:
            bits.append("no internet")
        col.append(label(" · ".join(b for b in bits if b), "rf-row-sub"))
        card.append(col)
        card.append(button("Disconnect", None, "rf-quiet", on_click=self.disconnect))
        return card

    def _network_row(self, n):
        row = Gtk.ListBoxRow(activatable=False)
        row.add_css_class("rf-row")
        outer = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        top = Gtk.Box(spacing=12)
        locked = L.needs_password(n.security) or n.security == "enterprise"
        top.append(icon(f"wifi-{L.signal_level(n.strength)}{'-lock' if locked else ''}", "silver", 20))
        col = Gtk.Box(orientation=Gtk.Orientation.VERTICAL); col.set_hexpand(True)
        col.append(label(n.ssid, "rf-row-title", ellipsize=True))
        saved = self.net.saved_for(n.ssid) is not None
        bits = [L.SECURITY_LABEL.get(n.security, n.security), L.band(n.freq), f"{n.strength}%"]
        if saved:
            bits.insert(0, "saved")
        col.append(label(" · ".join(b for b in bits if b), "rf-row-sub"))
        top.append(col)
        busy = self.attempt is not None and self.attempt.ssid == n.ssid
        if busy:
            sp = Gtk.Spinner(spinning=True); top.append(sp)
        else:
            act = button("Connect", None, "rf-quiet",
                         on_click=lambda: self._row_primary(n, saved))
            act.set_sensitive(self.attempt is None)
            top.append(act)
        outer.append(top)
        if self.expanded == n.ssid and not busy:
            outer.append(self._password_form(n, saved))
        row.set_child(outer)
        return row

    def _row_primary(self, n, saved):
        if (saved or not L.needs_password(n.security)) and n.ssid not in self.prompt_reason:
            self.connect_network(n)
        else:
            self.expanded = None if self.expanded == n.ssid else n.ssid
            self.refresh()

    def _password_form(self, n, saved):
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        box.add_css_class("rf-form")
        if n.ssid in self.prompt_reason:
            box.append(label(self.prompt_reason[n.ssid] + " Enter the current password.", "rf-warn", wrap=True))
        pw = Gtk.PasswordEntry(show_peek_icon=True, placeholder_text="Password")
        pw.add_css_class("rf-entry")
        box.append(pw)
        auto = Gtk.CheckButton(label="Connect automatically", active=True)
        if not saved:
            box.append(auto)
        hint = label("", "rf-row-sub")
        box.append(hint)
        row = Gtk.Box(spacing=8, halign=Gtk.Align.END)

        def go(*_):
            text = pw.get_text()
            if not L.valid_password(n.security, text):
                hint.set_text("WPA passwords are 8–63 characters (or 64 hex digits)."
                              if n.security != "wep" else "WEP keys are 5/13 characters or 10/26 hex digits.")
                hint.add_css_class("rf-warn")
                return
            self.connect_network(n, text, auto.get_active())
            pw.set_text("")
        pw.connect("activate", go)
        row.append(button("Cancel", None, "rf-ghost", on_click=lambda: (setattr(self, "expanded", None),
                                                                        self.prompt_reason.pop(n.ssid, None),
                                                                        self.refresh())))
        row.append(button("Join", None, "rf-primary", on_click=go))
        box.append(row)
        GLib.idle_add(pw.grab_focus)
        return box

    def _saved_row(self, ssid, conn):
        row = Gtk.ListBoxRow(activatable=False)
        row.add_css_class("rf-row")
        box = Gtk.Box(spacing=10)
        col = Gtk.Box(orientation=Gtk.Orientation.VERTICAL); col.set_hexpand(True)
        col.append(label(ssid, "rf-row-title", ellipsize=True))
        auto = conn.get_setting_connection().get_autoconnect()
        col.append(label("connects automatically" if auto else "manual", "rf-row-sub"))
        box.append(col)
        sw = Gtk.Switch(active=auto, valign=Gtk.Align.CENTER, tooltip_text="Connect automatically")
        sw.connect("state-set", lambda _s, v: (self.set_autoconnect(conn, v), False)[1])
        box.append(sw)
        forget = button(None, "forget", "rf-ghost", tooltip=f"Forget {ssid}")
        confirm_state = {"armed": False}

        def on_forget(*_):
            if not confirm_state["armed"]:
                confirm_state["armed"] = True
                forget.add_css_class("rf-danger")
                forget.set_tooltip_text("Click again to forget")
                self.set_status(f"Click the bin again to forget {ssid}.", "info")
                GLib.timeout_add_seconds(4, lambda: (confirm_state.update(armed=False),
                                                     forget.remove_css_class("rf-danger"), False)[2])
            else:
                self.forget(ssid, conn)
        forget.connect("clicked", on_forget)
        box.append(forget)
        row.set_child(box)
        return row

    def _hidden_form(self):
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        box.add_css_class("rf-form")
        ssid = Gtk.Entry(placeholder_text="Network name (SSID)"); ssid.add_css_class("rf-entry")
        pw = Gtk.PasswordEntry(show_peek_icon=True, placeholder_text="Password (blank if open)")
        pw.add_css_class("rf-entry")
        box.append(ssid); box.append(pw)

        def go(*_):
            name = ssid.get_text().strip()
            key = pw.get_text()
            if not name:
                self.set_status("Enter the network name.", "error"); return
            sec = "wpa2" if key else "open"
            if key and not L.valid_password(sec, key):
                self.set_status("WPA passwords are 8–63 characters.", "error"); return
            dev = self.net.device()
            if not dev or self.attempt:
                return
            con = build_connection(name, sec, key, hidden=True)
            att = self.attempt = Attempt(self, name, created=True)
            self.set_status(f"Looking for {name}…", busy=True)

            def done(c, res):
                try:
                    att.started(c.add_and_activate_connection_finish(res))
                except GLib.Error as e:
                    att.fail_early(e.message)
            self.net.client.add_and_activate_connection_async(con, dev, None, None, done)
            pw.set_text("")
        box.append(button("Join", None, "rf-primary", on_click=go))
        return box
