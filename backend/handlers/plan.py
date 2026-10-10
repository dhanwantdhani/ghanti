"""6 PM: decide tomorrow's calls for the live school and deliver them."""
from ghanti import store, forecast, rules, messaging
from handlers.common import tomorrow, live_school_id, new_token, teacher_url, slots_from_school, now_ist


def plan_for(school, date, weekday, excluded_windows=None, hourly=None):
    """Compute calls for one school and one date without side effects.

    Algorithm: if no hourly values are given, fetch them: the forecast when
    the date is today or later, the archive (modelled, past air) when the
    date is in the past; pick the hours for the date; run rules.decide with
    the school's slots and move windows; return the calls as dicts plus the
    hourly dict used.
    """
    if hourly is None:
        hourly = forecast.fetch_for_date(school["lat"], school["lon"], date)
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
    if isinstance(event, dict) and event.get("date"):
        import datetime as _dt
        d = _dt.date.fromisoformat(event["date"])
        date, weekday = d.isoformat(), ["mon", "tue", "wed", "thu", "fri", "sat", "sun"][d.weekday()]
    trace = []
    calls = hourly = prose = None
    try:
        from ghanti.agent import plan_with_agent, compose
        calls, hourly, prose, trace = plan_with_agent(school, date, weekday)
    except Exception as e:
        trace.append(f"agent unavailable: {type(e).__name__}")
    if not calls:
        calls, hourly = plan_for(school, date, weekday)
        trace.append("deterministic path used for the calls")
    if not calls:
        return {"ok": True, "date": date, "calls": 0, "note": "no outdoor slots tomorrow", "trace": trace}

    token = new_token()
    store.put_forecast(school["school_id"], date, hourly, issued=now_ist().isoformat(timespec="minutes"), trace=trace)
    store.put_token(school["school_id"], date, token)
    url = teacher_url(token)
    if prose:
        text, used_model = compose(school["name"], date, prose, calls, url), True
    else:
        text, used_model = messaging.model_text(school["name"], date, calls, url)
        trace.append("message: " + ("Nova direct" if used_model else "template"))
    for c in calls:
        store.put_call(school["school_id"], date, c, token, status="SENT", message=text)

    sent = {
        "coordinator": messaging.telegram_send(school.get("coordinator_chat_id"), text, url, "Open tomorrow's plan"),
        "teacher": messaging.telegram_send(school.get("teacher_chat_id"), text, url, "Confirm or object"),
        "sms": messaging.sms_send(messaging.template_text(school["name"], date, calls)),
    }
    return {"ok": True, "date": date, "calls": [c["call"] for c in calls], "used_model": used_model, "sent": sent, "trace": trace}


if __name__ == "__main__":
    print(handler())
