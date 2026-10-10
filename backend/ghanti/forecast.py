"""Open-Meteo air-quality client. No key. CAMS global model, about 45 km grid,
updated every 12 hours. Say that on screen wherever a forecast is shown.
"""
import requests

BASE = "https://air-quality-api.open-meteo.com/v1/air-quality"
TZ = "Asia/Kolkata"


def _by_day(payload):
    """Turn Open-Meteo's flat hourly arrays into {date: {hour: pm25}}.

    Algorithm: zip the time and pm2_5 arrays; split each timestamp
    "YYYY-MM-DDTHH:MM" into date and hour; skip null values.
    """
    out = {}
    for t, v in zip(payload["hourly"]["time"], payload["hourly"]["pm2_5"]):
        if v is None:
            continue
        day, hhmm = t.split("T")
        out.setdefault(day, {})[int(hhmm[:2])] = float(v)
    return out


def fetch_hourly(lat, lon, forecast_days=2):
    """Hourly PM2.5 forecast for today and the next days, grouped by date.

    Returns:
        dict {date_str: {hour_int: pm25_float}}, plus the model issue time
        under the key "_issued" (string, from the response's generation time
        if present, else None).
    """
    r = requests.get(BASE, params={
        "latitude": lat, "longitude": lon, "hourly": "pm2_5",
        "forecast_days": forecast_days, "timezone": TZ,
    }, timeout=20)
    r.raise_for_status()
    data = _by_day(r.json())
    return data


def fetch_archive(lat, lon, start_date, end_date):
    """Hourly PM2.5 for a past window (used for the labelled replay)."""
    r = requests.get(BASE, params={
        "latitude": lat, "longitude": lon, "hourly": "pm2_5",
        "start_date": start_date, "end_date": end_date, "timezone": TZ,
    }, timeout=30)
    r.raise_for_status()
    return _by_day(r.json())


def fetch_for_date(lat, lon, date):
    """Hourly PM2.5 for one date: archive if past, else a forecast long enough to reach it (max 5 days)."""
    from datetime import date as _d
    from zoneinfo import ZoneInfo
    from datetime import datetime
    today = datetime.now(ZoneInfo(TZ)).date()
    target = _d.fromisoformat(date)
    if target < today:
        return fetch_archive(lat, lon, date, date).get(date, {})
    days = min(max((target - today).days + 1, 1), 5)
    return fetch_hourly(lat, lon, forecast_days=days).get(date, {})


if __name__ == "__main__":
    # CHANGE ME: your school's coordinates.
    data = fetch_hourly(26.85, 80.95)
    for day, hours in data.items():
        line = " ".join(f"{h:02d}:{round(v)}" for h, v in sorted(hours.items()) if 6 <= h <= 17)
        print(day, line)
