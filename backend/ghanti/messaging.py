"""Message text and delivery.

Bedrock writes the words. The calls themselves come from rules.py and the
model cannot change them; if Bedrock fails we fall back to a template and
record that the template was used.
"""
import os
import json
import requests
import boto3

TELEGRAM = "https://api.telegram.org/bot{token}/{method}"


def template_text(school_name, date, calls, teacher_url=None):
    """Plain template used when the model is unavailable or for the sandbox.

    Algorithm: one line per call in slot order: label, start, the call,
    the move window if any, and the forecast value with its band. Append the
    teacher link when given.
    """
    import datetime as _dt
    try:
        d = _dt.date.fromisoformat(date)
        nice = f"{d.strftime('%A')} {d.day} {d.strftime('%B')}"
    except ValueError:
        nice = date
    lines = [f"Ghanti call for {school_name}, {nice}:"]
    for c in calls:
        where = {"OUTDOORS": "outdoors", "CAUTION": "outdoors, keep it short",
                 "INDOORS": "indoors", "NO_CHANGE": "as planned",
                 "MOVE": f"move to {c.get('move_to')}"}[c["call"]]
        lines.append(f"- {c['label']} ({c['start']}): {where}. Forecast {round(c['forecast_pm25'])} µg/m³, {c['band']}.")
    if teacher_url:
        lines.append(f"Confirm or object: {teacher_url}")
    lines.append("Forecast: CAMS model via Open-Meteo, 45 km grid. Not medical advice.")
    return "\n".join(lines)


def model_text(school_name, date, calls, teacher_url=None):
    """Ask Bedrock Nova for a short, warm message that states every call exactly.

    Algorithm: send the calls as JSON with strict instructions (do not change
    any call, name every slot, give the forecast number, under 90 words,
    plain English). Validate that every slot label and call word appears in
    the reply; if not, or on any error, return the template and a flag.

    Returns:
        (text, used_model_bool)
    """
    model_id = os.environ.get("BEDROCK_MODEL_ID", "amazon.nova-lite-v1:0")
    prompt = (
        "You write a short evening message to a school PE teacher about tomorrow's outdoor periods. "
        "Rules: do not change any decision; mention every slot by its label and its decision word exactly "
        "(OUTDOORS, CAUTION, MOVE, INDOORS, NO_CHANGE); include each forecast number; under 90 words; "
        "plain English; no emoji; end with 'Reply on the link.'\n\n"
        f"School: {school_name}. Date: {date}.\nDecisions (JSON): {json.dumps(calls)}"
    )
    try:
        client = boto3.client("bedrock-runtime")
        resp = client.converse(modelId=model_id, messages=[{"role": "user", "content": [{"text": prompt}]}],
                               inferenceConfig={"maxTokens": 300, "temperature": 0.2})
        text = resp["output"]["message"]["content"][0]["text"].strip()
        ok = all(c["label"] in text and c["call"] in text for c in calls)
        if not ok:
            return template_text(school_name, date, calls, teacher_url), False
        if teacher_url:
            text += f"\n{teacher_url}"
        text += "\nForecast: CAMS model via Open-Meteo, 45 km grid. Not medical advice."
        return text, True
    except Exception:
        return template_text(school_name, date, calls, teacher_url), False


def telegram_send(chat_id, text, button_url=None, button_label="Open"):
    """Send a Telegram message, optionally with one link button. Returns True on success."""
    token = os.environ.get("TELEGRAM_BOT_TOKEN", "")
    if not token or not chat_id:
        return False
    payload = {"chat_id": chat_id, "text": text, "disable_web_page_preview": True}
    if button_url:
        payload["reply_markup"] = {"inline_keyboard": [[{"text": button_label, "url": button_url}]]}
    r = requests.post(TELEGRAM.format(token=token, method="sendMessage"), json=payload, timeout=15)
    return r.ok


def sms_send(text):
    """SNS SMS to the comma-separated numbers in SMS_NUMBERS (your own verified phones). ASCII, short."""
    numbers = [n.strip() for n in os.environ.get("SMS_NUMBERS", "").split(",") if n.strip()]
    if not numbers:
        return 0
    sns = boto3.client("sns")
    sent = 0
    for n in numbers:
        sns.publish(PhoneNumber=n, Message=text[:150])
        sent += 1
    return sent


if __name__ == "__main__":
    calls = [
        {"slot_id": "assembly", "label": "Morning assembly", "start": "07:50", "forecast_pm25": 146, "band": "Very Poor", "call": "MOVE", "move_to": "13:20"},
        {"slot_id": "pe_2b", "label": "PE, Class 2B", "start": "08:30", "forecast_pm25": 131, "band": "Very Poor", "call": "INDOORS", "move_to": None},
    ]
    print(template_text("Sector 9 Public School, Rohini", "2026-10-10", calls, "https://example.com/#/t/abc"))
