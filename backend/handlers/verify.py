"""3 PM: score calls against what the station measured, for every recent day
whose station data has arrived. Writes the ledger.

Station data timing (measured 9 Oct 2026): WAQI is same-hour but only in
Delhi-NCR; OpenAQ covers the rest of India one to two days late. So this job
looks back five days and fills whatever it can. A row with no measurement
yet is written as "awaiting station data" and replaced when the data lands.
"""
from datetime import timedelta
from ghanti import store, rules, dose, messaging
from handlers.common import now_ist, date_str, live_school_id

LOOKBACK_DAYS = 5


def handler(event=None, context=None):
    """Fill the ledger for the last LOOKBACK_DAYS days.

    Algorithm: for each date from today back five days, load that date's
    calls; skip dates with none; load the station's readings for the date;
    for each call, skip it if a ledger row with a measurement already exists;
    compute the mean measured value over the slot's hours; mark right or
    wrong with rules.was_right; count children-hours for calls the teacher
    confirmed; compute micrograms avoided from measured values where they
    exist; write the row (with measured None meaning "awaiting station
    data"). Send one Telegram summary line for any date that gained
    newly verified rows.
    """
    school = store.get_school(live_school_id())
    if not school:
        return {"ok": False, "error": "live school not seeded"}
    station_id = (school.get("station") or {}).get("sensor_id") or f"waqi-{school['school_id']}"
    slots = {s["slot_id"]: s for s in school["slots"]}
    report = {}
    for back in range(LOOKBACK_DAYS):
        date = date_str(now_ist() - timedelta(days=back))
        calls = store.get_calls(school["school_id"], date)
        if not calls:
            continue
        existing = store.get_ledger_for_date(school["school_id"], date)
        readings = store.get_readings(station_id, date)
        right = wrong = newly = 0
        hours_total = 0.0
        ug_total = 0
        for c in calls:
            s = slots.get(c["slot_id"])
            if not s:
                continue
            prev = existing.get(c["slot_id"])
            if prev and prev.get("measured_pm25") is not None:
                continue
            measured = rules.slot_value(readings, c["start"], s["minutes"]) if readings else None
            if prev and measured is None:
                continue  # still awaiting; nothing new to write
            ok = rules.was_right(float(c["forecast_pm25"]), measured)
            confirmed = c.get("status") in ("OK", "UPDATED")
            hours = dose.children_hours(s["headcount"], s["minutes"], c["call"]) if confirmed else 0.0
            c_new = readings.get(int(c["move_to"][:2])) if (c["call"] == "MOVE" and c.get("move_to") and readings) else None
            base = measured if measured is not None else float(c["forecast_pm25"])
            ug = dose.ug_avoided(s["headcount"], s["minutes"], s["intensity"], base, c["call"], c_new) if confirmed else 0
            store.put_ledger(school["school_id"], date, c["slot_id"], {
                "label": c["label"], "start": c["start"], "call": c["call"], "move_to": c.get("move_to"),
                "forecast_pm25": c["forecast_pm25"], "measured_pm25": measured,
                "measured_band": rules.band(measured) if measured is not None else None,
                "call_was_right": ok, "teacher_confirmed": confirmed,
                "children_hours_moved": hours, "ug_avoided": ug,
                "measured_source": "station archive (OpenAQ) or same-hour (WAQI, Delhi-NCR only)" if measured is not None else "awaiting station data",
                "verified_at": now_ist().isoformat(timespec="minutes") if measured is not None else None,
                "assumptions": "breathing rates EPA EFH ch.6 ages 6-11; indoor factor 0.7; NAQI 24h bands on hourly values",
                "station": (school.get("station") or {}).get("name") or school.get("waqi_station"),
            })
            if measured is not None:
                newly += 1
                right += 1 if ok else 0
                wrong += 0 if ok else 1
                hours_total += hours
                ug_total += ug
        report[date] = {"calls": len(calls), "newly_verified": newly, "right": right, "wrong": wrong,
                        "children_hours": round(hours_total, 1), "ug": ug_total}
        if newly:
            messaging.telegram_send(school.get("coordinator_chat_id"),
                                    f"Ghanti ledger {date}: {right} right, {wrong} wrong, "
                                    f"{round(hours_total, 1)} children-hours moved, {ug_total} ug PM2.5 avoided.")
    return {"ok": True, "dates": report}


if __name__ == "__main__":
    print(handler())
