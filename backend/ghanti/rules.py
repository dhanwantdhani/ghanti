"""Deterministic outdoor-call rules. No model touches anything in this file.

Bands are India's NAQI PM2.5 breakpoints (24-hour standard) applied to
hourly values. That is a simplification and the UI says so.

    0-30 Good | 31-60 Satisfactory | 61-90 Moderate | 91-120 Poor
    121-250 Very Poor | 251+ Severe
"""
from dataclasses import dataclass, field, asdict

POOR = 91          # at or above this, children do not go outdoors
WATCH = 61         # 61-90 is the caution band
MOVE_RATIO = 0.7   # a move must cut the slot's value to 70% or less
FLAT_SPREAD = 0.15 # under 15% spread between hours, do not disturb the day
CHILD_AGE = 10     # classes up to this age get the stricter rule

BANDS = [
    (30, "Good"),
    (60, "Satisfactory"),
    (90, "Moderate"),
    (120, "Poor"),
    (250, "Very Poor"),
    (float("inf"), "Severe"),
]


def band(pm25):
    """Return the NAQI band name for a PM2.5 value in ug/m3.

    Algorithm: walk the BANDS table from the lowest upper bound upward and
    return the first band whose upper bound is at or above the value.

    Args:
        pm25: float, micrograms per cubic metre.
    Returns:
        str, one of Good, Satisfactory, Moderate, Poor, Very Poor, Severe.
    """
    for upper, name in BANDS:
        if pm25 <= upper:
            return name
    return "Severe"


@dataclass
class Slot:
    """One outdoor slot in the school day.

    Schema:
        slot_id: str, stable id such as "assembly"
        label: str, shown to humans, such as "Morning assembly"
        start: str, "HH:MM" 24-hour local time
        minutes: int, duration
        headcount: int, children in the slot
        intensity: str, one of light, moderate, vigorous
        weekdays: list of str, subset of mon tue wed thu fri sat sun
        max_age: int, age of the youngest children in the slot
    """
    slot_id: str
    label: str
    start: str
    minutes: int
    headcount: int
    intensity: str
    weekdays: list
    max_age: int = 18


@dataclass
class Call:
    """The decision for one slot on one date.

    Schema:
        slot_id, label, start: copied from the slot
        forecast_pm25: float, the value the decision used
        band: str, NAQI band of forecast_pm25
        call: str, one of OUTDOORS, CAUTION, MOVE, INDOORS, NO_CHANGE
        move_to: str or None, "HH:MM" of the window the slot moves to
        move_to_pm25: float or None, forecast at that window
        reason: str, one plain sentence
        children_hours: float, headcount x minutes / 60 when the slot is moved or taken indoors, else 0
    """
    slot_id: str
    label: str
    start: str
    forecast_pm25: float
    band: str
    call: str
    move_to: str = None
    move_to_pm25: float = None
    reason: str = ""
    children_hours: float = 0.0

    def to_dict(self):
        return asdict(self)


def _hour_of(hhmm):
    return int(hhmm.split(":")[0])


def slot_value(hourly, start, minutes):
    """Mean forecast over the hours a slot covers.

    Algorithm: take the start hour and every later hour the slot touches,
    look each up in the hourly dict (hour -> ug/m3), and average the ones
    that exist. If none exist, return None so the caller can skip the slot.

    Args:
        hourly: dict mapping int hour (0-23) to float PM2.5.
        start: str "HH:MM".
        minutes: int duration.
    Returns:
        float or None.
    """
    h0 = _hour_of(start)
    end_minute = int(start.split(":")[1]) + minutes
    hours = list(range(h0, h0 + 1 + (end_minute - 1) // 60))
    vals = [hourly[h] for h in hours if h in hourly]
    if not vals:
        return None
    return round(sum(vals) / len(vals), 1)


def _pick_window(windows, hourly, v, ceiling, taken, excluded):
    """Pick the cleanest free move window that satisfies the thresholds.

    Algorithm: for each window time, read its hourly value; keep it if the
    value is at or below the ceiling, at or below MOVE_RATIO of the slot's
    own value, not already taken by another move today, and not excluded by
    a teacher's objection. Return the window with the lowest value, or None.
    """
    best = None
    for w in windows:
        if w in taken or w in excluded:
            continue
        wv = hourly.get(_hour_of(w))
        if wv is None or wv > ceiling or wv > MOVE_RATIO * v:
            continue
        if best is None or wv < best[1]:
            best = (w, wv)
    return best


def decide(slots, hourly, move_windows, weekday, excluded_windows=None):
    """Produce one Call per slot for a given day.

    Algorithm:
        1. Keep only slots scheduled on this weekday and compute each slot's value.
        2. If every slot is at or above POOR, send everything indoors and say
           that moving would not help.
        3. If the worst slot is in the caution band (61-90), nothing is at or
           above POOR, and the spread between best and worst is under
           FLAT_SPREAD, return NO_CHANGE for all. (A uniformly clean day is
           simply OUTDOORS.)
        4. Otherwise decide each slot, worst first so the worst slot gets the
           best free window:
             value <= 60: OUTDOORS
             61-90 and (light activity and older than CHILD_AGE): OUTDOORS
             61-90 otherwise: try a move to a window <= 60; else CAUTION (outdoors, shortened)
             >= 91: try a move to a window <= 90; else INDOORS
        5. A move window can be used once per day.

    Args:
        slots: list of Slot.
        hourly: dict int hour -> float PM2.5 for the day.
        move_windows: list of "HH:MM" times the ground is free for a move.
        weekday: str, three letters, lower case.
        excluded_windows: set of "HH:MM" a teacher has ruled out today.
    Returns:
        list of Call, in the slots' original order.
    """
    excluded = set(excluded_windows or [])
    todays = [s for s in slots if weekday in s.weekdays]
    valued = []
    for s in todays:
        v = slot_value(hourly, s.start, s.minutes)
        if v is not None:
            valued.append((s, v))
    if not valued:
        return []

    values = [v for _, v in valued]
    if min(values) >= POOR:
        return [
            Call(s.slot_id, s.label, s.start, v, band(v), "INDOORS",
                 reason="Every hour of the school day is Poor or worse; moving would not help.",
                 children_hours=round(s.headcount * s.minutes / 60, 1))
            for s, v in valued
        ]
    spread = (max(values) - min(values)) / max(values) if max(values) else 0
    if WATCH <= max(values) < POOR and spread < FLAT_SPREAD:
        return [
            Call(s.slot_id, s.label, s.start, v, band(v), "NO_CHANGE",
                 reason="Hours are flat today; nothing to gain by moving.")
            for s, v in valued
        ]

    taken = set()
    out = {}
    for s, v in sorted(valued, key=lambda sv: -sv[1]):
        hours = round(s.headcount * s.minutes / 60, 1)
        if v < WATCH:
            out[s.slot_id] = Call(s.slot_id, s.label, s.start, v, band(v), "OUTDOORS",
                                  reason="Air is Satisfactory or better at this hour.")
            continue
        if v < POOR:
            if s.intensity == "light" and s.max_age > CHILD_AGE:
                out[s.slot_id] = Call(s.slot_id, s.label, s.start, v, band(v), "OUTDOORS",
                                      reason="Moderate air; light activity for older children is fine.")
                continue
            w = _pick_window(move_windows, hourly, v, WATCH - 1, taken, excluded)
            if w:
                taken.add(w[0])
                out[s.slot_id] = Call(s.slot_id, s.label, s.start, v, band(v), "MOVE", w[0], w[1],
                                      reason=f"Moderate air at {s.start}; {w[0]} is Satisfactory.",
                                      children_hours=hours)
            else:
                out[s.slot_id] = Call(s.slot_id, s.label, s.start, v, band(v), "CAUTION",
                                      reason="Moderate air and no cleaner window; keep it short and low intensity.")
            continue
        w = _pick_window(move_windows, hourly, v, POOR - 1, taken, excluded)
        if w:
            taken.add(w[0])
            out[s.slot_id] = Call(s.slot_id, s.label, s.start, v, band(v), "MOVE", w[0], w[1],
                                  reason=f"{band(v)} air at {s.start}; {w[0]} is {band(w[1])}.",
                                  children_hours=hours)
        else:
            out[s.slot_id] = Call(s.slot_id, s.label, s.start, v, band(v), "INDOORS",
                                  reason=f"{band(v)} air and no window under 91 today.",
                                  children_hours=hours)
    return [out[s.slot_id] for s, _ in valued]


def was_right(forecast_pm25, measured_pm25):
    """Score a call after the fact.

    Algorithm: the call hinged on whether the hour was Poor or worse. It was
    right if the forecast and the measured value fell on the same side of
    POOR. Returns None when there is no measurement.
    """
    if measured_pm25 is None:
        return None
    return (forecast_pm25 >= POOR) == (measured_pm25 >= POOR)


if __name__ == "__main__":
    # A typical North Indian winter morning: dirty at 8, clearing by noon.
    hourly = {7: 150, 8: 142, 9: 120, 10: 98, 11: 80, 12: 66, 13: 58, 14: 55, 15: 60, 16: 90}
    slots = [
        Slot("assembly", "Morning assembly", "07:50", 20, 400, "light", ["mon", "tue", "wed", "thu", "fri", "sat"], max_age=16),
        Slot("pe_2b", "PE, Class 2B", "08:30", 40, 38, "moderate", ["mon", "wed", "fri", "sat"], max_age=7),
        Slot("pe_7c", "PE, Class 7C", "10:10", 40, 42, "vigorous", ["mon", "wed", "fri", "sat"], max_age=12),
        Slot("games", "Games period", "12:30", 40, 60, "moderate", ["mon", "tue", "wed", "thu", "fri", "sat"], max_age=14),
    ]
    windows = ["11:10", "12:30", "13:20"]
    for c in decide(slots, hourly, windows, "fri"):
        print(f"{c.label:<18} {c.start}  {c.forecast_pm25:>6}  {c.band:<12} {c.call:<9} "
              f"{(c.move_to or ''):<6} {c.reason}")
