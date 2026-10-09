"""6 AM: compare the station's latest reading with the forecast and update calls if needed."""
from ghanti import store, rules, messaging
from handlers.common import today, live_school_id, slots_from_school, teacher_url

TOLERANCE = 0.4  # update when the station is more than 40% off the forecast


def handler(event=None, context=None):
    """Re-run today's calls if the morning station reading disagrees with the forecast.

    Algorithm: load the live school and today's stored forecast and calls;
    read the latest hourly station value; look up the forecast for that same
    hour; if the ratio station/forecast is outside 1 +/- TOLERANCE, scale the
    whole day's forecast by that ratio, re-run the rules, and for every slot
    whose call changed update the record to UPDATED and message both people.
    Always write what happened to the log entry so the ledger can show it.
    """
    school = store.get_school(live_school_id())
    date, weekday = today()
    hourly = store.get_forecast(school["school_id"], date) if school else None
    calls = store.get_calls(school["school_id"], date) if school else []
    if not (school and hourly and calls):
        return {"ok": True, "note": "nothing planned for today"}
    station_id = school.get("station", {}).get("sensor_id")
    ts_hour, measured = store.latest_reading(station_id) if station_id else (None, None)
    if measured is None:
        return {"ok": True, "note": "no station reading yet"}
    if ts_hour[:10] != date:
        return {"ok": True, "note": f"latest station reading is from {ts_hour}, not this morning; forecast stands"}
    hour = int(ts_hour[11:13])
    f = hourly.get(hour)
    if not f:
        return {"ok": True, "note": f"no forecast for hour {hour}"}
    ratio = measured / f
    if abs(ratio - 1) <= TOLERANCE:
        return {"ok": True, "ratio": round(ratio, 2), "note": "forecast holds; no update"}

    scaled = {h: v * ratio for h, v in hourly.items()}
    new_calls = rules.decide(slots_from_school(school), scaled, school.get("move_windows", []), weekday)
    old = {c["slot_id"]: c for c in calls}
    changed = []
    for c in new_calls:
        prev = old.get(c.slot_id)
        if prev and (prev["call"] != c.call or prev.get("move_to") != c.move_to):
            store.update_call(school["school_id"], date, c.slot_id, call=c.call, move_to=c.move_to,
                              forecast_pm25=round(c.forecast_pm25, 1), band=c.band, reason=c.reason,
                              status="UPDATED", children_hours=c.children_hours)
            changed.append(c.to_dict())
    if changed:
        token = calls[0].get("token")
        text = (f"Updated {ts_hour[11:13]}:00: station {school['station']['name']} reads {round(measured)} ug/m3, "
                f"forecast was {round(f)}.\n" + messaging.template_text(school["name"], date, changed))
        url = teacher_url(token)
        messaging.telegram_send(school.get("coordinator_chat_id"), text, url, "Open the updated plan")
        messaging.telegram_send(school.get("teacher_chat_id"), text, url, "Confirm or object")
    return {"ok": True, "ratio": round(ratio, 2), "changed": [c["slot_id"] for c in changed]}


if __name__ == "__main__":
    print(handler())
