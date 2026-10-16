"""Pure decision logic for the Wi-Fi and Bluetooth panels (no GTK, no D-Bus),
so it can be tested on its own.
"""
from dataclasses import dataclass, field

# NetworkManager 802.11 flag bits (libnm NM80211ApFlags / NM80211ApSecurityFlags)
AP_FLAGS_PRIVACY = 0x1
SEC_KEY_MGMT_PSK = 0x100
SEC_KEY_MGMT_8021X = 0x200
SEC_KEY_MGMT_SAE = 0x400
SEC_KEY_MGMT_OWE = 0x800
SEC_KEY_MGMT_OWE_TM = 0x1000
SEC_KEY_MGMT_EAP_SUITE_B_192 = 0x2000


def classify_security(flags, wpa_flags, rsn_flags):
    """-> one of: open, owe, wep, wpa, wpa2, wpa3, wpa2/3, enterprise"""
    sec = wpa_flags | rsn_flags
    if sec & (SEC_KEY_MGMT_8021X | SEC_KEY_MGMT_EAP_SUITE_B_192):
        return "enterprise"
    if rsn_flags & SEC_KEY_MGMT_SAE:
        return "wpa2/3" if rsn_flags & SEC_KEY_MGMT_PSK else "wpa3"
    if rsn_flags & SEC_KEY_MGMT_PSK:
        return "wpa2"
    if wpa_flags & SEC_KEY_MGMT_PSK:
        return "wpa"
    if sec & (SEC_KEY_MGMT_OWE | SEC_KEY_MGMT_OWE_TM):
        return "owe"
    if flags & AP_FLAGS_PRIVACY:
        return "wep"
    return "open"


SECURITY_LABEL = {
    "open": "Open", "owe": "Enhanced open", "wep": "WEP (insecure)", "wpa": "WPA",
    "wpa2": "WPA2", "wpa3": "WPA3", "wpa2/3": "WPA2/WPA3", "enterprise": "Enterprise (802.1X)",
}


def needs_password(security):
    return security in ("wep", "wpa", "wpa2", "wpa3", "wpa2/3")


def key_mgmt_for(security):
    """NM 802-11-wireless-security.key-mgmt for a PSK network we create."""
    return {"wpa3": "sae", "wep": "none"}.get(security, "wpa-psk")


def valid_password(security, pw):
    """client-side sanity check before handing the key to NetworkManager."""
    if security == "wep":
        return len(pw) in (5, 13) or (len(pw) in (10, 26) and all(c in "0123456789abcdefABCDEF" for c in pw))
    if security in ("wpa", "wpa2", "wpa2/3", "wpa3"):
        if len(pw) == 64 and all(c in "0123456789abcdefABCDEF" for c in pw):
            return True
        return 8 <= len(pw) <= 63
    return True


def signal_level(strength):
    """0..100 -> 0..3 (matches the wifi-N icons)"""
    if strength >= 70:
        return 3
    if strength >= 45:
        return 2
    if strength >= 20:
        return 1
    return 0


def band(freq_mhz):
    if not freq_mhz:
        return ""
    if freq_mhz < 3000:
        return "2.4 GHz"
    if freq_mhz < 5925:
        return "5 GHz"
    return "6 GHz"


@dataclass
class Network:
    ssid: str
    strength: int
    security: str
    freq: int
    path: str                       # D-Bus path of the strongest AP
    bssids: list = field(default_factory=list)


def dedup_networks(aps):
    """aps: iterable of dicts(ssid, strength, security, freq, path, bssid).

    One entry per SSID (hidden SSIDs dropped), keeping the strongest AP;
    sorted strongest first, ties by name.
    """
    best = {}
    for ap in aps:
        ssid = ap.get("ssid") or ""
        if not ssid.strip():
            continue
        cur = best.get(ssid)
        if cur is None or ap["strength"] > cur.strength:
            n = Network(ssid, ap["strength"], ap["security"], ap.get("freq", 0), ap["path"],
                        (cur.bssids if cur else []))
            best[ssid] = n
            cur = n
        cur.bssids.append(ap.get("bssid", ""))
    return sorted(best.values(), key=lambda n: (-n.strength, n.ssid.lower()))


# NMDeviceStateReason nicks (from NM.DeviceStateReason value_nick) -> message
_DEVICE_REASONS = {
    "no-secrets": ("secrets", "The password was rejected or is missing."),
    "supplicant-disconnect": ("secrets", "Authentication failed: the network refused the password."),
    "supplicant-config-failed": ("error", "The Wi-Fi driver rejected the connection settings."),
    "supplicant-failed": ("error", "The Wi-Fi supplicant failed. Try again in a moment."),
    "supplicant-timeout": ("secrets", "Authentication timed out (often a wrong password)."),
    "ssid-not-found": ("error", "The network is no longer in range."),
    "ip-config-unavailable": ("error", "Connected to the access point, but no IP address was assigned."),
    "ip-config-expired": ("error", "The IP address lease expired."),
    "dhcp-start-failed": ("error", "Could not start DHCP."),
    "dhcp-error": ("error", "DHCP error from the network."),
    "dhcp-failed": ("error", "The network did not hand out an address (DHCP)."),
    "carrier": ("error", "The adapter lost its link."),
    "user-requested": ("cancel", "Disconnected."),
    "new-activation": ("cancel", "Replaced by another connection."),
    "removed": ("error", "The adapter disappeared."),
    "sleeping": ("error", "The system is going to sleep."),
}


def explain_device_reason(nick):
    """-> (kind, message); kind in secrets | error | cancel"""
    return _DEVICE_REASONS.get(nick, ("error", f"Connection failed ({nick or 'unknown reason'})."))


# BlueZ errors -> human messages
_BT_ERRORS = {
    "org.bluez.Error.AuthenticationFailed": "Pairing failed: authentication was refused.",
    "org.bluez.Error.AuthenticationCanceled": "Pairing was cancelled.",
    "org.bluez.Error.AuthenticationRejected": "The device rejected the pairing request.",
    "org.bluez.Error.AuthenticationTimeout": "Pairing timed out. Put the device in pairing mode and retry.",
    "org.bluez.Error.ConnectionAttemptFailed": "The device did not answer. Is it on and in range?",
    "org.bluez.Error.AlreadyConnected": "Already connected.",
    "org.bluez.Error.AlreadyExists": "Already paired.",
    "org.bluez.Error.InProgress": "Another operation is already running for this device.",
    "org.bluez.Error.NotReady": "The Bluetooth adapter is not ready (is it powered on?).",
    "org.bluez.Error.NotSupported": "The device does not support this operation.",
    "org.bluez.Error.DoesNotExist": "The device is no longer known to the adapter.",
    "org.freedesktop.DBus.Error.NoReply": "The operation timed out.",
    "org.freedesktop.DBus.Error.ServiceUnknown": "The Bluetooth service (bluetoothd) is not running.",
}
_BT_FAILED = {
    "br-connection-profile-unavailable":
        "No usable profile. For audio devices, check that WirePlumber/PipeWire Bluetooth support is running.",
    "br-connection-page-timeout": "The device did not answer. Is it on, in range, and not connected elsewhere?",
    "br-connection-refused": "The device refused the connection.",
    "br-connection-canceled": "The connection was cancelled.",
    "le-connection-abort-by-local": "The connection was aborted. Try again closer to the device.",
    "Host is down": "The device is off or out of range.",
    "Input/output error": "The device dropped the connection.",
}


def explain_bt_error(name, message=""):
    if name == "org.bluez.Error.Failed" or name.endswith(".Failed"):
        for key, text in _BT_FAILED.items():
            if key in (message or ""):
                return text
        return f"The operation failed{': ' + message if message else '.'}"
    return _BT_ERRORS.get(name, message or name or "Unknown error.")


def bt_kind(icon, name=""):
    """BlueZ Icon property (+ name heuristics) -> device glyph name."""
    n = (name or "").lower()
    # some speakers announce themselves as headsets (e.g. Tronsmart: Class 0x240404)
    if any(w in n for w in ("speaker", "soundlink", "boom", "tronsmart", "element", "jbl flip", "jbl charge")):
        return "dev-speaker"
    if icon in ("audio-headset", "audio-headphones"):
        return "dev-earbuds" if any(w in n for w in ("bud", "pods", "earbud")) else "dev-headset"
    return {
        "audio-card": "dev-speaker", "audio-speakers": "dev-speaker",
        "input-mouse": "dev-mouse", "input-keyboard": "dev-keyboard",
        "input-gaming": "dev-gamepad", "input-tablet": "dev-generic",
        "phone": "dev-phone", "computer": "dev-computer",
    }.get(icon or "", "dev-earbuds" if "bud" in n else "dev-generic")


def looks_unnamed(alias, address):
    """BlueZ falls back to the address (with '-' separators) when a device has no name."""
    a = (alias or "").replace("-", ":").upper()
    return not alias or a == (address or "").upper()
