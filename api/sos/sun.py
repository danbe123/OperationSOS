"""Sunrise and sunset from the NOAA solar calculator equations: pure arithmetic, no data files and no network.

A port of `web/src/tools/sun.ts` so the engine can decide whether it is dark at home without asking the browser.
Times are timezone-aware UTC datetimes; the caller formats them in the box's zone."""
from __future__ import annotations

import math
from datetime import date, datetime, timedelta, timezone

RAD = math.pi / 180.0
ZENITH_SUN = 90.833          # the sun's centre at rise and set, allowing for refraction and its radius
ZENITH_CIVIL = 96.0


def _julian_day(moment: datetime) -> float:
    return moment.timestamp() / 86400.0 + 2440587.5


def _solar_params(jd: float) -> tuple[float, float]:
    """Equation of time (minutes) and the solar declination (degrees) for a Julian day."""
    t = (jd - 2451545.0) / 36525.0
    l0 = (280.46646 + t * (36000.76983 + t * 0.0003032)) % 360.0
    m = 357.52911 + t * (35999.05029 - 0.0001537 * t)
    e = 0.016708634 - t * (0.000042037 + 0.0000001267 * t)
    c = (math.sin(m * RAD) * (1.914602 - t * (0.004817 + 0.000014 * t))
         + math.sin(2 * m * RAD) * (0.019993 - 0.000101 * t)
         + math.sin(3 * m * RAD) * 0.000289)
    true_long = l0 + c
    omega = 125.04 - 1934.136 * t
    apparent_long = true_long - 0.00569 - 0.00478 * math.sin(omega * RAD)
    obliq0 = 23 + (26 + (21.448 - t * (46.815 + t * (0.00059 - t * 0.001813))) / 60) / 60
    obliq = obliq0 + 0.00256 * math.cos(omega * RAD)
    declination = math.asin(math.sin(obliq * RAD) * math.sin(apparent_long * RAD)) / RAD
    y = math.tan((obliq / 2) * RAD) ** 2
    eq_time = 4 / RAD * (
        y * math.sin(2 * l0 * RAD) - 2 * e * math.sin(m * RAD) + 4 * e * y * math.sin(m * RAD) * math.cos(2 * l0 * RAD)
        - 0.5 * y * y * math.sin(4 * l0 * RAD) - 1.25 * e * e * math.sin(2 * m * RAD))
    return eq_time, declination


def _hour_angle(lat: float, declination: float, zenith: float) -> float | None:
    """Degrees from solar noon at which the sun reaches the zenith, or None on a polar day or night."""
    cos_h = (math.cos(zenith * RAD) / (math.cos(lat * RAD) * math.cos(declination * RAD))
             - math.tan(lat * RAD) * math.tan(declination * RAD))
    if cos_h > 1 or cos_h < -1:
        return None
    return math.acos(cos_h) / RAD


def _at(day_start: datetime, minutes: float) -> datetime:
    return day_start + timedelta(minutes=minutes)


def sun_times(lat: float, lon: float, day: date | datetime) -> tuple[datetime | None, datetime | None]:
    """Sunrise and sunset in UTC for the UTC calendar day of `day`.

    Returns (None, None) on a polar day or night, when the sun neither rises nor sets."""
    if isinstance(day, datetime):
        day = day.astimezone(timezone.utc).date() if day.tzinfo else day.date()
    day_start = datetime(day.year, day.month, day.day, tzinfo=timezone.utc)
    noon_guess = _julian_day(day_start) + 0.5 - lon / 360.0
    eq0, _ = _solar_params(noon_guess)
    noon_min = 720 - 4 * lon - eq0
    solar_noon = _at(day_start, noon_min)
    eq_noon, dec_noon = _solar_params(_julian_day(solar_noon))
    ha = _hour_angle(lat, dec_noon, ZENITH_SUN)
    if ha is None:
        return None, None
    eq_rise, dec_rise = _solar_params(_julian_day(_at(day_start, noon_min - ha * 4)))
    eq_set, dec_set = _solar_params(_julian_day(_at(day_start, noon_min + ha * 4)))
    ha_rise = _hour_angle(lat, dec_rise, ZENITH_SUN) or ha
    ha_set = _hour_angle(lat, dec_set, ZENITH_SUN) or ha
    sunrise = _at(day_start, 720 - 4 * (lon + ha_rise) - eq_rise)
    sunset = _at(day_start, 720 - 4 * (lon - ha_set) - eq_set)
    return sunrise, sunset


def is_dark(lat: float, lon: float, now: datetime) -> bool:
    """True between sunset and sunrise. On a polar day it is never dark; on a polar night, always."""
    now = now if now.tzinfo else now.replace(tzinfo=timezone.utc)
    sunrise, sunset = sun_times(lat, lon, now)
    if sunrise is None or sunset is None:
        _, dec = _solar_params(_julian_day(now))
        return lat * dec < 0                       # the sun is over the other hemisphere: polar night
    return now < sunrise or now >= sunset
