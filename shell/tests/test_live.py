#!/usr/bin/env python3
"""Non-disruptive live checks against the real NetworkManager and BlueZ.

Changes nothing: one Wi-Fi scan request (NM rate limits are respected) and a
short Bluetooth discovery that is stopped again. No connect/disconnect/pair.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from gi.repository import GLib  # noqa: E402

from bluetooth import BtState  # noqa: E402
from common import boottime_ms  # noqa: E402
from wifi import NetState  # noqa: E402

loop = GLib.MainLoop()
net, bt = NetState(), BtState()
log = []
seen_discovering = []


def step1_wifi():
    if not net.client:
        return True
    s = net.summary()
    log.append(f"wifi summary: {s['state']} {s.get('ssid', '')} {s.get('strength', '')}%")
    dev = net.device()
    nets = net.networks()
    log.append(f"networks visible: {len(nets)} -> " + ", ".join(f"{n.ssid}({n.security},{n.strength}%)" for n in nets))
    log.append(f"saved wifi profiles: {len(net.saved_wifi())}")
    before = dev.get_last_scan()

    def done(d, res):
        try:
            d.request_scan_finish(res)
            log.append("scan request accepted")
        except GLib.Error as e:
            log.append(f"scan rate-limited by NM (expected sometimes): {e.message}")
        GLib.timeout_add_seconds(6, lambda: (log.append(
            f"last_scan advanced: {dev.get_last_scan() != before} (age {(boottime_ms() - dev.get_last_scan()) // 1000}s)"),
            step2_bt(), False)[2])
    dev.request_scan_async(None, done)
    return False


def step2_bt():
    s = bt.summary()
    log.append(f"bt summary: {s['state']} devices={[d['name'] for d in s.get('devices', [])]}")
    bt.listeners.append(lambda: seen_discovering.append(bool((bt.adapter() or {}).get('Discovering'))))
    bt.start_discovery(lambda err: log.append(f"StartDiscovery error: {err}") if err else log.append("StartDiscovery ok"))
    GLib.timeout_add_seconds(8, step3_bt_stop)


def step3_bt_stop():
    nearby = [d for d in bt.devices() if not d["paired"] and d["rssi"] is not None]
    log.append(f"nearby during discovery: {len(nearby)} ({sum(1 for d in nearby if d['unnamed'])} unnamed)")
    bt.stop_discovery(lambda err: log.append(f"StopDiscovery error: {err}") if err else log.append("StopDiscovery ok"))
    GLib.timeout_add_seconds(2, finish)
    return False


def finish():
    log.append(f"Discovering went true: {any(seen_discovering)}; now: {bool((bt.adapter() or {}).get('Discovering'))}")
    loop.quit()
    return False


GLib.timeout_add(300, step1_wifi)
GLib.timeout_add_seconds(40, loop.quit)
loop.run()
print("\n".join(log))
