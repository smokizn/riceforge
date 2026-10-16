#!/usr/bin/env python3
"""Live tests that briefly interrupt connectivity. Run only with consent.

    test_disruptive.py wifi SSID          disconnect, then reconnect through Attempt
    test_disruptive.py bt "DEVICE NAME"    disconnect, then reconnect through BtState.device_op

Both use the panels' own code paths. The Wi-Fi test restores the connection
with `nmcli connection up SSID` if anything goes wrong.
"""
import subprocess
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import gi  # noqa: E402

gi.require_version("NM", "1.0")
from gi.repository import GLib, NM  # noqa: E402

loop = GLib.MainLoop()
log = []
t0 = time.monotonic()


def note(msg):
    log.append(f"[{time.monotonic() - t0:5.1f}s] {msg}")


def wifi(ssid):
    from wifi import Attempt, NetState
    net = NetState()
    result = {"ok": None}

    class FakePanel:            # the slice of WifiPanel that Attempt talks to
        def __init__(self):
            self.net = net

        def attempt_finished(self, att, ok, message, kind):
            result["ok"] = ok
            note(f"Attempt finished: ok={ok} kind={kind} message={message!r}")
            loop.quit()

    def start():
        if not net.client:
            return True
        dev, saved = net.device(), net.saved_for(ssid)
        if not dev or not saved:
            note("no wifi device or no saved profile; aborting"); loop.quit(); return False
        note(f"connected to {net.summary().get('ssid')!r}; disconnecting via Device.disconnect_async")

        def disconnected(d, res):
            try:
                d.disconnect_finish(res)
                note("disconnect accepted")
            except GLib.Error as e:
                note(f"disconnect failed: {e.message}"); loop.quit(); return

            def wait_down():
                if d.get_state() <= NM.DeviceState.DISCONNECTED:
                    note(f"device state: {d.get_state().value_nick}; reconnecting via Attempt")
                    att = Attempt(FakePanel(), ssid)

                    def activated(c, r):
                        try:
                            att.started(c.activate_connection_finish(r))
                            note("activate_connection accepted; waiting for NM to report ACTIVATED")
                        except GLib.Error as e:
                            att.fail_early(e.message)
                    net.client.activate_connection_async(saved, d, None, None, activated)
                    return False
                return True
            GLib.timeout_add(200, wait_down)
        dev.disconnect_async(None, disconnected)
        return False

    GLib.timeout_add(300, start)
    GLib.timeout_add_seconds(70, loop.quit)
    loop.run()
    if not result["ok"]:
        note("restoring with nmcli (guard)")
        r = subprocess.run(["nmcli", "connection", "up", ssid], capture_output=True, text=True, timeout=60)
        note(f"nmcli: {r.returncode} {r.stdout.strip() or r.stderr.strip()}")
    return result["ok"]


def bt(name):
    from bluetooth import BtState
    bt = BtState()
    state = {"phase": "init", "ok": False}

    def find():
        for d in bt.devices():
            if d["name"] == name:
                return d
        return None

    def start():
        d = find()
        if not d:
            if bt.owner:
                note(f"device {name!r} not found"); loop.quit(); return False
            return True
        if not d["connected"]:
            note("device is not connected; nothing to test"); loop.quit(); return False
        path = d["path"]
        note("connected; Disconnect via device_op")
        state["phase"] = "disconnecting"

        def after_disconnect(err):
            note(f"Disconnect returned err={err}")
            if err:
                loop.quit(); return

            def reconnect():
                note(f"device connected now: {find()['connected']}; Connect via device_op")

                def after_connect(err2):
                    note(f"Connect returned err={err2}")
                    def confirm():
                        c = find()["connected"]
                        note(f"BlueZ reports Connected={c}")
                        state["ok"] = (err2 is None) and c
                        loop.quit()
                        return False
                    GLib.timeout_add_seconds(2, confirm)
                bt.device_op(path, "Connect", after_connect)
                return False
            GLib.timeout_add_seconds(3, reconnect)
        bt.device_op(path, "Disconnect", after_disconnect)
        return False

    GLib.timeout_add(500, start)
    GLib.timeout_add_seconds(60, loop.quit)
    loop.run()
    return state["ok"]


if __name__ == "__main__":
    kind, target = sys.argv[1], sys.argv[2]
    ok = wifi(target) if kind == "wifi" else bt(target)
    print("\n".join(log))
    print("RESULT:", "PASS" if ok else "FAIL")
