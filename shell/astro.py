"""Sun and moon, computed locally (no network, no subprocess).

Moon phases use the classic Meeus/moontool `truephase` series (accuracy:
minutes). Sun times use the NOAA general solar position equations
(accuracy: a minute or two away from the poles).
"""
import math
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

SYNODIC = 29.530588853
PHASE_NAMES = ["New Moon", "Waxing Crescent", "First Quarter", "Waxing Gibbous",
               "Full Moon", "Waning Gibbous", "Last Quarter", "Waning Crescent"]


def _dsin(d):
    return math.sin(math.radians(d))


def _dcos(d):
    return math.cos(math.radians(d))


def jd_from_datetime(dt):
    dt = dt.astimezone(timezone.utc)
    return dt.timestamp() / 86400.0 + 2440587.5


def datetime_from_jd(jd):
    return datetime.fromtimestamp((jd - 2440587.5) * 86400.0, tz=timezone.utc)


def truephase(k, phase):
    """JD of the lunation k (counted from Jan 1900) at phase 0, .25, .5 or .75."""
    k = k + phase
    t = k / 1236.85
    t2, t3 = t * t, t * t * t
    pt = (2415020.75933 + SYNODIC * k + 0.0001178 * t2 - 0.000000155 * t3
          + 0.00033 * _dsin(166.56 + 132.87 * t - 0.009173 * t2))
    m = 359.2242 + 29.10535608 * k - 0.0000333 * t2 - 0.00000347 * t3
    mp = 306.0253 + 385.81691806 * k + 0.0107306 * t2 + 0.00001236 * t3
    f = 21.2964 + 390.67050646 * k - 0.0016528 * t2 - 0.00000239 * t3
    if phase < 0.01 or abs(phase - 0.5) < 0.01:
        pt += ((0.1734 - 0.000393 * t) * _dsin(m) + 0.0021 * _dsin(2 * m)
               - 0.4068 * _dsin(mp) + 0.0161 * _dsin(2 * mp) - 0.0004 * _dsin(3 * mp)
               + 0.0104 * _dsin(2 * f) - 0.0051 * _dsin(m + mp) - 0.0074 * _dsin(m - mp)
               + 0.0004 * _dsin(2 * f + m) - 0.0004 * _dsin(2 * f - m)
               - 0.0006 * _dsin(2 * f + mp) + 0.0010 * _dsin(2 * f - mp)
               + 0.0005 * _dsin(m + 2 * mp))
    else:
        pt += ((0.1721 - 0.0004 * t) * _dsin(m) + 0.0021 * _dsin(2 * m)
               - 0.6280 * _dsin(mp) + 0.0089 * _dsin(2 * mp) - 0.0004 * _dsin(3 * mp)
               + 0.0079 * _dsin(2 * f) - 0.0119 * _dsin(m + mp) - 0.0047 * _dsin(m - mp)
               + 0.0003 * _dsin(2 * f + m) - 0.0004 * _dsin(2 * f - m)
               - 0.0006 * _dsin(2 * f + mp) + 0.0021 * _dsin(2 * f - mp)
               + 0.0003 * _dsin(m + 2 * mp) + 0.0004 * _dsin(m - 2 * mp)
               - 0.0003 * _dsin(2 * m + mp))
        adj = 0.0028 - 0.0004 * _dcos(m) + 0.0003 * _dcos(mp)
        pt += adj if phase < 0.5 else -adj
    return pt


def _k_near(jd):
    return math.floor((jd - 2415020.75933) / SYNODIC)


def phase_event(jd, phase, direction):
    """first JD of `phase` strictly after (direction=+1) or before (-1) jd."""
    k = _k_near(jd) - 2 * direction
    for _ in range(8):
        t = truephase(k, phase)
        if (direction > 0 and t > jd) or (direction < 0 and t < jd):
            # step back toward jd to make sure it is the nearest one
            while True:
                t2 = truephase(k - direction, phase)
                if (direction > 0 and t2 > jd) or (direction < 0 and t2 < jd):
                    k -= direction; t = t2
                else:
                    return t
        k += direction
    return truephase(k, phase)


@dataclass
class Moon:
    fraction: float        # 0 new .. 0.5 full .. 1 new
    illumination: float    # 0..1
    age_days: float
    index: int             # 0..7, see PHASE_NAMES
    name: str
    next_new: datetime
    next_full: datetime
    waxing: bool


def moon_at(dt=None):
    dt = dt or datetime.now(timezone.utc)
    jd = jd_from_datetime(dt)
    prev_new = phase_event(jd, 0.0, -1)
    next_new = phase_event(jd, 0.0, +1)
    next_full = phase_event(jd, 0.5, +1)
    frac = (jd - prev_new) / (next_new - prev_new)
    illum = (1 - math.cos(2 * math.pi * frac)) / 2
    idx = int(math.floor(frac * 8 + 0.5)) % 8
    return Moon(frac, illum, jd - prev_new, idx, PHASE_NAMES[idx],
                datetime_from_jd(next_new), datetime_from_jd(next_full), frac < 0.5)


@dataclass
class SunDay:
    sunrise: datetime | None
    sunset: datetime | None
    noon: datetime
    polar: str | None      # None, "day" (midnight sun) or "night"

    @property
    def day_length(self):
        if self.polar == "day":
            return timedelta(hours=24)
        if self.polar == "night":
            return timedelta(0)
        return self.sunset - self.sunrise


def sun_day(date, lat, lon):
    """NOAA sunrise/noon/sunset (UTC datetimes) for a calendar date at lat/lon."""
    n = date.timetuple().tm_yday
    g = 2 * math.pi / 365 * (n - 1)
    eqtime = 229.18 * (0.000075 + 0.001868 * math.cos(g) - 0.032077 * math.sin(g)
                       - 0.014615 * math.cos(2 * g) - 0.040849 * math.sin(2 * g))
    decl = (0.006918 - 0.399912 * math.cos(g) + 0.070257 * math.sin(g)
            - 0.006758 * math.cos(2 * g) + 0.000907 * math.sin(2 * g)
            - 0.002697 * math.cos(3 * g) + 0.00148 * math.sin(3 * g))
    la = math.radians(lat)
    base = datetime(date.year, date.month, date.day, tzinfo=timezone.utc)
    noon = base + timedelta(minutes=720 - 4 * lon - eqtime)
    x = math.cos(math.radians(90.833)) / (math.cos(la) * math.cos(decl)) - math.tan(la) * math.tan(decl)
    if x < -1:
        return SunDay(None, None, noon, "day")
    if x > 1:
        return SunDay(None, None, noon, "night")
    ha = math.degrees(math.acos(x))
    rise = base + timedelta(minutes=720 - 4 * (lon + ha) - eqtime)
    sset = base + timedelta(minutes=720 - 4 * (lon - ha) - eqtime)
    return SunDay(rise, sset, noon, None)
