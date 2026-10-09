"""Measured PM2.5 from the nearest official (CPCB/SPCB) station.

Two sources, used for different jobs:

  WAQI (aqicn.org, free token in WAQI_TOKEN): the same CPCB stations within
  the hour. Used for the 6 AM re-check and the same-day 3 PM verification.
  Attribution is required and raw archives must not be republished, so the
  public API exposes per-slot means and right/wrong, never the raw polls.

  OpenAQ v3 (free key in OPENAQ_API_KEY): hourly averages, but for Indian
  stations it runs 1-2 days behind (measured on 9 Oct 2026: 43 hours).
  Used for the replay archive and to backfill Readings later, which lets the
  ledger upgrade a row from "WAQI" to "OpenAQ archive" once it arrives.
"""
import os
from datetime import datetime, timedelta, timezone
import requests

OPENAQ = "https://api.openaq.org/v3"
WAQI = "https://api.waqi.info"


def _headers():
    key = os.environ.get("OPENAQ_API_KEY", "")
    if not key:
        raise RuntimeError("OPENAQ_API_KEY is not set")
    return {"X-API-Key": key}


def _iso(dt):
    return dt.isoformat(timespec="seconds")


def nearest_pm25_sensor(lat, lon, radius_m=25000, max_age_days=4):
    """Find the closest station with a PM2.5 sensor that actually returns data.

    Algorithm: ask OpenAQ for every location within the radius (max 25 km);
    drop any whose last report is older than max_age_days; sort by distance;
    for each remaining location and each of its pm25 sensors, probe the hours
    endpoint for the last 3 days and return the first sensor that has rows.
    Returns None if nothing qualifies.

    Returns:
        dict {location_id, name, distance_km, sensor_id, last_seen} or None.
    """
    r = requests.get(f"{OPENAQ}/locations", headers=_headers(), params={
        "coordinates": f"{lat},{lon}", "radius": min(radius_m, 25000), "limit": 50,
    }, timeout=20)
    r.raise_for_status()
    cutoff = datetime.now(timezone.utc) - timedelta(days=max_age_days)
    candidates = []
    for loc in r.json().get("results", []):
        last = (loc.get("datetimeLast") or {}).get("utc")
        if not last:
            continue
        try:
            last_dt = datetime.fromisoformat(last.replace("Z", "+00:00"))
        except ValueError:
            continue
        if last_dt < cutoff:
            continue
        candidates.append((loc.get("distance") or 1e12, loc))
    candidates.sort(key=lambda x: x[0])
    now = datetime.now(timezone(timedelta(hours=5, minutes=30)))
    for dist, loc in candidates:
        for s in loc.get("sensors", []):
            if s.get("parameter", {}).get("name") != "pm25":
                continue
            rows = hourly_values(s["id"], _iso(now - timedelta(days=3)), _iso(now))
            if rows:
                return {
                    "location_id": loc["id"],
                    "name": loc["name"],
                    "distance_km": round(dist / 1000, 1),
                    "sensor_id": s["id"],
                    "last_seen": (loc.get("datetimeLast") or {}).get("local"),
                }
    return None


def hourly_values(sensor_id, datetime_from, datetime_to):
    """Hourly PM2.5 averages for an OpenAQ sensor between two ISO timestamps.

    Returns:
        list of (ts_hour_local "YYYY-MM-DDTHH", value_float), oldest first.
    """
    r = requests.get(f"{OPENAQ}/sensors/{sensor_id}/hours", headers=_headers(), params={
        "datetime_from": datetime_from, "datetime_to": datetime_to, "limit": 200,
    }, timeout=20)
    r.raise_for_status()
    out = []
    for row in r.json().get("results", []):
        local = row["period"]["datetimeFrom"]["local"]  # 2026-10-09T07:00:00+05:30
        out.append((local[:13], float(row["value"])))
    out.sort()
    return out


WAQI_MAX_KM = 30  # the geo feed silently returns a Delhi station for cities whose feed is dead


def _km(lat1, lon1, lat2, lon2):
    """Great-circle distance in km (haversine)."""
    from math import radians, sin, cos, asin, sqrt
    p1, p2, dl = radians(lat1), radians(lat2), radians(lon2 - lon1)
    a = sin((p2 - p1) / 2) ** 2 + cos(p1) * cos(p2) * sin(dl / 2) ** 2
    return 6371 * 2 * asin(sqrt(a))


def waqi_now(lat, lon):
    """Current PM2.5 at the nearest WAQI station, if it is really nearby.

    Algorithm: call the geo feed for the coordinates; reject the answer if
    the station it picked is more than WAQI_MAX_KM away (measured 9 Oct 2026:
    outside Delhi-NCR the feed returns a Delhi station because the local
    stations stopped on 23 June 2026); read iaqi.pm25.v, a US AQI sub-index,
    and convert it to ug/m3 with the EPA breakpoints; return station name,
    value, the reading's local hour ("YYYY-MM-DDTHH"), distance and WAQI id.
    None if no token, no PM2.5, or no station nearby.
    """
    token = os.environ.get("WAQI_TOKEN", "")
    if not token:
        return None
    r = requests.get(f"{WAQI}/feed/geo:{lat};{lon}/", params={"token": token}, timeout=20)
    r.raise_for_status()
    body = r.json()
    if body.get("status") != "ok":
        return None
    d = body.get("data") or {}
    geo = (d.get("city") or {}).get("geo") or [None, None]
    if geo[0] is None or _km(lat, lon, float(geo[0]), float(geo[1])) > WAQI_MAX_KM:
        return None
    aqi = (d.get("iaqi") or {}).get("pm25", {}).get("v")
    if aqi is None:
        return None
    t = (d.get("time") or {}).get("iso") or (d.get("time") or {}).get("s", "")
    ts_hour = t[:13].replace(" ", "T")
    return {"name": (d.get("city") or {}).get("name"), "pm25": _us_aqi_to_ugm3(float(aqi)),
            "ts_hour": ts_hour, "distance_km": round(_km(lat, lon, float(geo[0]), float(geo[1])), 1),
            "waqi_id": d.get("idx")}


def _us_aqi_to_ugm3(aqi):
    """Invert the US EPA PM2.5 AQI breakpoints (2024 revision)."""
    table = [(0, 50, 0.0, 9.0), (51, 100, 9.1, 35.4), (101, 150, 35.5, 55.4),
             (151, 200, 55.5, 125.4), (201, 300, 125.5, 225.4), (301, 500, 225.5, 325.4)]
    for alo, ahi, clo, chi in table:
        if alo <= aqi <= ahi:
            return round(clo + (aqi - alo) * (chi - clo) / (ahi - alo), 1)
    return 325.4


if __name__ == "__main__":
    # Needs OPENAQ_API_KEY (and optionally WAQI_TOKEN) in the environment. CHANGE ME: coordinates.
    s = nearest_pm25_sensor(26.85, 80.95)
    print("openaq:", s)
    print("waqi:  ", waqi_now(26.85, 80.95))
