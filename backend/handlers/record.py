"""Hourly: record measured PM2.5 for the live school's station.

Two writes each hour:
  1. WAQI current value (near real time). Stored with source "waqi".
  2. OpenAQ hourly values for the last 3 days, which arrive 1-2 days late.
     Stored with source "openaq" and allowed to overwrite the WAQI value for
     the same hour, so the ledger upgrades itself when the archive lands.

Runs every hour. Every missed hour is lost, so deploy this first.
"""
from datetime import timedelta
from ghanti import store, station
from handlers.common import now_ist, live_school_id


def handler(event=None, context=None):
    """Store this hour's WAQI reading and backfill OpenAQ hours.

    Algorithm: load the live school; if it has no OpenAQ station yet, find
    the nearest sensor that returns data and save it on the school; poll
    WAQI for the current value and store it under the school's station id
    (so one key holds both sources); then fetch OpenAQ hours for the last 3
    days and store them, overwriting same-hour WAQI rows. Return a summary.
    """
    school = store.get_school(live_school_id())
    if not school:
        return {"ok": False, "error": "live school not seeded"}
    if not school.get("station"):
        s = station.nearest_pm25_sensor(school["lat"], school["lon"])
        if s:
            school["station"] = s
            store.put_school(school)
    station_id = (school.get("station") or {}).get("sensor_id") or f"waqi-{school['school_id']}"

    out = {"ok": True, "station": (school.get("station") or {}).get("name"), "waqi": None, "openaq_rows": 0}
    w = station.waqi_now(school["lat"], school["lon"])
    if w and w.get("ts_hour"):
        store.put_readings(station_id, [(w["ts_hour"], w["pm25"])], source="waqi")
        out["waqi"] = w
        if not school.get("waqi_station") or school["waqi_station"] != w["name"]:
            school["waqi_station"] = w["name"]
            store.put_school(school)
    if school.get("station"):
        now = now_ist()
        rows = station.hourly_values(school["station"]["sensor_id"],
                                     (now - timedelta(days=3)).isoformat(timespec="seconds"),
                                     now.isoformat(timespec="seconds"))
        if rows:
            store.put_readings(station_id, rows, source="openaq")
            out["openaq_rows"] = len(rows)
            out["openaq_latest"] = rows[-1]
    return out


if __name__ == "__main__":
    print(handler())
