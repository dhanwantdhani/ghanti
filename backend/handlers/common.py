"""Shared helpers for the handlers: dates in IST and the live school."""
import os
import secrets
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

IST = ZoneInfo("Asia/Kolkata")
WEEKDAYS = ["mon", "tue", "wed", "thu", "fri", "sat", "sun"]


def now_ist():
    return datetime.now(IST)


def date_str(dt):
    return dt.strftime("%Y-%m-%d")


def tomorrow():
    """(date_str, weekday_str) for tomorrow in IST."""
    d = now_ist() + timedelta(days=1)
    return date_str(d), WEEKDAYS[d.weekday()]


def today():
    d = now_ist()
    return date_str(d), WEEKDAYS[d.weekday()]


def live_school_id():
    return os.environ.get("LIVE_SCHOOL_ID", "demo-school")


def new_token():
    return secrets.token_urlsafe(8)


def teacher_url(token):
    base = os.environ.get("PUBLIC_BASE_URL", "").rstrip("/")
    return f"{base}/#/t/{token}" if base else f"#/t/{token}"


def slots_from_school(school):
    """Build rules.Slot objects from the stored school record.

    Expected school["slots"] schema: list of dicts with keys
    slot_id, label, start, minutes, headcount, intensity, weekdays, max_age.
    """
    from ghanti.rules import Slot
    return [Slot(**{k: s[k] for k in ("slot_id", "label", "start", "minutes", "headcount", "intensity", "weekdays")},
                 max_age=s.get("max_age", 18)) for s in school["slots"]]
