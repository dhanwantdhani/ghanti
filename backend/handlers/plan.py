"""6 PM: decide tomorrow's calls for the live school and deliver them."""
from ghanti import store, forecast, rules, messaging
from handlers.common import tomorrow, live_school_id, new_token, teacher_url, slots_from_school, now_ist


def plan_for(school, date, weekday, excluded_windows=None, hourly=None):
    """Compute calls for one school and one date without side effects.

    Algorithm: fetch the forecast if not given; pick the hours for the date;
    run rules.decide with the school's slots and move windows; return the
    calls as dicts plus the hourly dict used.
    """
    if hourly is None:
        data = forecast.fetch_hourly(school["lat"], school["lon"], forecast_days=2)
        hourly = data.get(date, {})
    calls = rules.decide(slots_from_school(school), hourly, school.get("move_windows", []), weekday, excluded_windows)
    return [c.to_dict() for c in calls], hourly


def handler(event=None, context=None):
    """Plan tomorrow, store it, and message the coordinator and the teacher.

    Algorithm: load the live school; compute tomorrow's calls; store the
    forecast and one token for the teacher link; store each call with the
    token; write the message (model, with template fallback); send it to the
    coordinator and the teacher on Telegram and, if configured, by SMS.
    """
    school = store.get_school(live_school_id())
    if not school:
        return {"ok": False, "error": "live school not seeded"}
    date, weekday = tomorrow()
    calls, hourly = plan_for(school, date, weekday)
    if not calls:
        return {"ok": True, "date": date, "calls": 0, "note": "no outdoor slots tomorrow"}

    token = new_token()
    store.put_forecast(school["school_id"], date, hourly, issued=now_ist().isoformat(timespec="minutes"))
    store.put_token(school["school_id"], date, token)
    url = teacher_url(token)
    text, used_model = messaging.model_text(school["name"], date, calls, url)
    for c in calls:
        store.put_call(school["school_id"], date, c, token, status="SENT", message=text)

    sent = {
        "coordinator": messaging.telegram_send(school.get("coordinator_chat_id"), text, url, "Open tomorrow's plan"),
        "teacher": messaging.telegram_send(school.get("teacher_chat_id"), text, url, "Confirm or object"),
        "sms": messaging.sms_send(messaging.template_text(school["name"], date, calls)),
    }
    return {"ok": True, "date": date, "calls": [c["call"] for c in calls], "used_model": used_model, "sent": sent}


if __name__ == "__main__":
    print(handler())
