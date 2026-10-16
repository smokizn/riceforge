#!/usr/bin/env python3
"""Plain-assert tests for the pure logic. Run: python3 -I tests/test_logic.py"""
import sys
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import astro  # noqa: E402
import netlogic as N  # noqa: E402

FAILED = []


def check(name, cond, detail=""):
    print(("ok   " if cond else "FAIL ") + name + (f"  ({detail})" if detail else ""))
    if not cond:
        FAILED.append(name)


def utc(*a):
    return datetime(*a, tzinfo=timezone.utc)


def near(a, b, minutes):
    return abs((a - b).total_seconds()) <= minutes * 60


# ── moon: well documented events ─────────────────────────────────────
events = [
    ("new moon / total solar eclipse 2024-04-08", 0.0, utc(2024, 4, 8, 18, 21)),
    ("full moon 2024-04-23", 0.5, utc(2024, 4, 23, 23, 49)),
    ("new moon 2025-01-29", 0.0, utc(2025, 1, 29, 12, 36)),
    ("full moon / total lunar eclipse 2025-03-14", 0.5, utc(2025, 3, 14, 6, 55)),
]
for name, ph, when in events:
    jd = astro.jd_from_datetime(when - timedelta(days=3))
    got = astro.datetime_from_jd(astro.phase_event(jd, ph, +1))
    check(name, near(got, when, 60), f"computed {got:%Y-%m-%d %H:%M} UTC")

m = astro.moon_at(utc(2024, 4, 8, 18, 30))
check("phase at eclipse is New Moon", m.index == 0 and m.illumination < 0.01, f"{m.name}, {m.illumination:.3f}")
m = astro.moon_at(utc(2025, 3, 14, 7, 0))
check("phase at lunar eclipse is Full Moon", m.index == 4 and m.illumination > 0.99, f"{m.name}, {m.illumination:.3f}")
m = astro.moon_at(utc(2024, 4, 16, 0, 0))
check("a week after new moon is waxing, near quarter", m.waxing and m.index in (1, 2, 3), m.name)
check("next full after 2024-04-16 is 04-23", m.next_full.date() == date(2024, 4, 23), str(m.next_full))

# ── sun ──────────────────────────────────────────────────────────────
s = astro.sun_day(date(2024, 3, 20), 0.0, 0.0)
check("equator equinox sunrise ~06:04 UTC", near(s.sunrise, utc(2024, 3, 20, 6, 4), 6), f"{s.sunrise:%H:%M}")
check("equator equinox sunset ~18:11 UTC", near(s.sunset, utc(2024, 3, 20, 18, 11), 6), f"{s.sunset:%H:%M}")
s = astro.sun_day(date(2024, 6, 21), 60.17, 24.94)
hours = s.day_length.total_seconds() / 3600
check("Helsinki midsummer day ~18.9 h", 18.5 < hours < 19.3, f"{hours:.2f} h")
s = astro.sun_day(date(2024, 6, 21), 78.2, 15.6)
check("Svalbard midsummer is polar day", s.polar == "day")
s = astro.sun_day(date(2024, 12, 21), 78.2, 15.6)
check("Svalbard midwinter is polar night", s.polar == "night")

# ── wifi logic ───────────────────────────────────────────────────────
check("open network", N.classify_security(0, 0, 0) == "open")
check("WEP via privacy bit", N.classify_security(N.AP_FLAGS_PRIVACY, 0, 0) == "wep")
check("WPA2 personal", N.classify_security(1, 0, N.SEC_KEY_MGMT_PSK) == "wpa2")
check("WPA (v1) personal", N.classify_security(1, N.SEC_KEY_MGMT_PSK, 0) == "wpa")
check("WPA3 only", N.classify_security(1, 0, N.SEC_KEY_MGMT_SAE) == "wpa3")
check("WPA2/3 transition", N.classify_security(1, 0, N.SEC_KEY_MGMT_SAE | N.SEC_KEY_MGMT_PSK) == "wpa2/3")
check("enterprise", N.classify_security(1, 0, N.SEC_KEY_MGMT_8021X) == "enterprise")
check("OWE is not open-with-password", N.classify_security(0, 0, N.SEC_KEY_MGMT_OWE) == "owe")
check("WPA3 uses SAE key-mgmt", N.key_mgmt_for("wpa3") == "sae")
check("WPA2 uses wpa-psk", N.key_mgmt_for("wpa2") == "wpa-psk")
check("short WPA password rejected", not N.valid_password("wpa2", "1234567"))
check("8-char WPA password ok", N.valid_password("wpa2", "12345678"))
check("64-hex PSK ok", N.valid_password("wpa2", "a" * 64))
check("64 non-hex rejected", not N.valid_password("wpa2", "z" * 64))
check("WEP 13-char ok", N.valid_password("wep", "abcdefghijklm"))

aps = [
    dict(ssid="home", strength=40, security="wpa2", freq=2437, path="/a1", bssid="aa"),
    dict(ssid="home", strength=80, security="wpa2", freq=5180, path="/a2", bssid="bb"),
    dict(ssid="", strength=99, security="open", freq=2412, path="/h", bssid="cc"),
    dict(ssid="cafe", strength=80, security="open", freq=2412, path="/c", bssid="dd"),
]
nets = N.dedup_networks(aps)
check("dedup keeps one entry per SSID, drops hidden", [n.ssid for n in nets] == ["cafe", "home"], str([n.ssid for n in nets]))
check("dedup keeps strongest AP path", next(n for n in nets if n.ssid == "home").path == "/a2")
check("dedup remembers all BSSIDs", sorted(next(n for n in nets if n.ssid == "home").bssids) == ["aa", "bb"])
check("signal levels", [N.signal_level(x) for x in (5, 30, 50, 90)] == [0, 1, 2, 3])
check("bands", (N.band(2412), N.band(5180), N.band(6115)) == ("2.4 GHz", "5 GHz", "6 GHz"))
check("no-secrets means password problem", N.explain_device_reason("no-secrets")[0] == "secrets")
check("ssid-not-found is a plain error", N.explain_device_reason("ssid-not-found")[0] == "error")
check("unknown reason still explained", "weird" in N.explain_device_reason("weird")[1])

# ── bluetooth logic ──────────────────────────────────────────────────
check("profile-unavailable hint mentions audio",
      "audio" in N.explain_bt_error("org.bluez.Error.Failed", "br-connection-profile-unavailable"))
check("auth failed message", "refused" in N.explain_bt_error("org.bluez.Error.AuthenticationFailed"))
check("unknown bluez error passes message through", N.explain_bt_error("x.y", "boom") == "boom")
check("earbuds by name", N.bt_kind("audio-headset", "Example Buds Pro") == "dev-earbuds")
check("speaker icon", N.bt_kind("audio-card", "Some Speaker") == "dev-speaker")
check("speaker that claims to be a headset", N.bt_kind("audio-headset", "Tronsmart Element T6 Plus") == "dev-speaker")
check("gamepad icon", N.bt_kind("input-gaming") == "dev-gamepad")
check("unnamed device detection", N.looks_unnamed("02-00-00-00-00-01", "02:00:00:00:00:01"))
check("named device", not N.looks_unnamed("Tronsmart", "02:00:00:00:00:01"))

print(f"\n{len(FAILED)} failed" if FAILED else "\nall passed")
sys.exit(1 if FAILED else 0)
