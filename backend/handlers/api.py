"""HTTP API behind a Lambda Function URL.

Routes (all JSON, CORS open):
    GET  /school                 the live school (slots, station, move windows)
    GET  /calls?date=YYYY-MM-DD  calls for a date (default: tomorrow, falling back to today)
    GET  /ledger                 recent ledger rows
    GET  /replay                 the stored replay week (school_id = replay)
    GET  /teacher?token=...      calls for the date behind a teacher token
    POST /reply                  {token, slot_id, action: ok|cant, reason, note}
    POST /sandbox                {lat, lon, slots:[...], move_windows:[...]} -> tomorrow's calls, stateless
"""
import json
from ghanti import store, rules, messaging, forecast
from handlers.common import tomorrow, today, live_school_id, slots_from_school, teacher_url
from handlers.plan import plan_for

CANT_REASONS = {
    "class_busy": "My class has a test or event then",
    "teacher_busy": "I am teaching another class then",
    "ground_busy": "The ground or hall is taken then",
}


def _resp(status, body):
    # CORS headers come from the Function URL config in template.yaml. Adding
    # them here too makes browsers see duplicates and reject the response.
    return {"statusCode": status, "headers": {"Content-Type": "application/json"},
            "body": json.dumps(body, default=str)}


def handler(event, context=None):
    """Route one Function URL request. See module docstring for routes."""
    http = event.get("requestContext", {}).get("http", {})
    method, path = http.get("method", "GET"), http.get("path", "/")
    qs = event.get("queryStringParameters") or {}
    if method == "OPTIONS":
        return _resp(200, {})
    try:
        body = json.loads(event["body"]) if event.get("body") else {}
    except json.JSONDecodeError:
        return _resp(400, {"error": "bad json"})

    if path == "/school":
        s = store.get_school(live_school_id())
        if s:
            s.pop("coordinator_chat_id", None)
            s.pop("teacher_chat_id", None)
        return _resp(200, s or {})
    if path == "/calls":
        date = qs.get("date") or tomorrow()[0]
        calls = store.get_calls(live_school_id(), date)
        if not calls and not qs.get("date"):
            date = today()[0]
            calls = store.get_calls(live_school_id(), date)
        return _resp(200, {"date": date, "calls": _public(calls),
                           "forecast": store.get_forecast(live_school_id(), date)})
    if path == "/ledger":
        return _resp(200, {"ledger": store.get_ledger(live_school_id())})
    if path == "/replay":
        week = store.get_ledger("replay", limit=200)
        return _resp(200, {"label": "REPLAY: modelled air, Nov 2025", "rows": week})
    if path == "/teacher":
        school_id, date = store.resolve_token(qs.get("token", ""))
        if not school_id:
            return _resp(404, {"error": "unknown link"})
        return _resp(200, {"date": date, "calls": _public(store.get_calls(school_id, date)), "reasons": CANT_REASONS})
    if path == "/reply" and method == "POST":
        return _reply(body)
    if path == "/sandbox" and method == "POST":
        return _sandbox(body)
    return _resp(404, {"error": "no such route"})


def _public(calls):
    for c in calls:
        c.pop("token", None)
    return calls


def _reply(body):
    """Record a teacher's OK or Can't; on Can't, re-plan with that window excluded.

    Algorithm: resolve the token to a school and date; find the call; on OK
    set status OK; on CANT set status CANT with the reason, add the slot's
    move window (if any) to the excluded set, re-run the rules using the
    stored forecast, update any call whose decision changed, and message the
    coordinator with the change. Return the full list of calls after the reply.
    """
    school_id, date = store.resolve_token(body.get("token", ""))
    if not school_id:
        return _resp(404, {"error": "unknown link"})
    school = store.get_school(school_id)
    calls = store.get_calls(school_id, date)
    target = next((c for c in calls if c["slot_id"] == body.get("slot_id")), None)
    if not target:
        return _resp(404, {"error": "unknown slot"})
    action = body.get("action")
    if action == "ok":
        store.update_call(school_id, date, target["slot_id"], status="OK")
        messaging.telegram_send(school.get("coordinator_chat_id"), f"{target['label']}: teacher confirmed {target['call']}.")
        return _resp(200, {"calls": _public(store.get_calls(school_id, date))})
    if action != "cant":
        return _resp(400, {"error": "action must be ok or cant"})
    reason = body.get("reason", "")
    store.update_call(school_id, date, target["slot_id"], status="CANT", cant_reason=reason, note=body.get("note", ""))
    excluded = {c["move_to"] for c in calls if c.get("status") == "CANT" and c.get("move_to")}
    if target.get("move_to"):
        excluded.add(target["move_to"])
    hourly = store.get_forecast(school_id, date)
    weekday = ["mon", "tue", "wed", "thu", "fri", "sat", "sun"][__import__("datetime").date.fromisoformat(date).weekday()]
    new_calls = rules.decide(slots_from_school(school), hourly, school.get("move_windows", []), weekday, excluded)
    changed = []
    for c in new_calls:
        prev = next((p for p in calls if p["slot_id"] == c.slot_id), None)
        if prev and (prev["call"] != c.call or prev.get("move_to") != c.move_to):
            store.update_call(school_id, date, c.slot_id, call=c.call, move_to=c.move_to, reason=c.reason,
                              children_hours=c.children_hours, status="SENT")
            changed.append(c.to_dict())
    note = CANT_REASONS.get(reason, reason)
    text = f"{target['label']}: teacher says '{note}'."
    if changed:
        text += "\nNew plan:\n" + messaging.template_text(school["name"], date, changed)
    messaging.telegram_send(school.get("coordinator_chat_id"), text)
    return _resp(200, {"changed": [c["slot_id"] for c in changed], "calls": _public(store.get_calls(school_id, date))})


def _sandbox(body):
    """Stateless 'try your school': live forecast, rules, template text. No model call, nothing stored.

    Expected body: {"lat": float, "lon": float, "name": str,
                    "slots": [{slot_id,label,start,minutes,headcount,intensity,weekdays,max_age}],
                    "move_windows": ["11:10", ...]}
    """
    try:
        school = {"name": body.get("name", "Your school"), "lat": float(body["lat"]), "lon": float(body["lon"]),
                  "slots": body.get("slots", []), "move_windows": body.get("move_windows", [])}
    except (KeyError, ValueError):
        return _resp(400, {"error": "lat and lon are required"})
    date, weekday = tomorrow()
    calls, hourly = plan_for(school, date, weekday)
    return _resp(200, {"date": date, "weekday": weekday, "calls": calls, "hourly": hourly,
                       "message": messaging.template_text(school["name"], date, calls),
                       "source": "CAMS model via Open-Meteo, 45 km grid, 12-hourly. Rules, not AI."})
