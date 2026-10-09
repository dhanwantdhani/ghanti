"""Exposure arithmetic shown on the ledger. Plain Python, assumptions named.

Breathing rates are short-term inhalation rates for children aged 6 to
under 11 from the US EPA Exposure Factors Handbook, chapter 6 (m3 per
minute). Check the table before quoting it in the video.
"""

RATES_M3_PER_MIN = {
    "seated": 0.0048,
    "light": 0.011,
    "moderate": 0.022,
    "vigorous": 0.042,
}
INDOOR_FACTOR = 0.7  # assumption: indoor PM2.5 at 70% of outdoor in an unfiltered classroom


def ug_avoided(headcount, minutes, intensity, c_original, call, c_new=None):
    """Micrograms of PM2.5 the group did not inhale because of the call.

    Algorithm:
        original = headcount x minutes x rate(intensity) x c_original
        if the slot MOVED outdoors to a cleaner hour:
            new = headcount x minutes x rate(intensity) x c_new
        if the slot went INDOORS (seated activity instead):
            new = headcount x minutes x rate(seated) x INDOOR_FACTOR x c_original
        otherwise nothing changed, return 0.
        return original - new, never negative.

    Args:
        headcount: int children.
        minutes: int duration.
        intensity: str light|moderate|vigorous.
        c_original: float ug/m3 at the original hour (measured when available).
        call: str MOVE or INDOORS; anything else returns 0.
        c_new: float ug/m3 at the new hour, required for MOVE.
    Returns:
        float micrograms, rounded to the nearest whole number.
    """
    rate = RATES_M3_PER_MIN.get(intensity, RATES_M3_PER_MIN["moderate"])
    original = headcount * minutes * rate * c_original
    if call == "MOVE" and c_new is not None:
        new = headcount * minutes * rate * c_new
    elif call == "INDOORS":
        new = headcount * minutes * RATES_M3_PER_MIN["seated"] * INDOOR_FACTOR * c_original
    else:
        return 0.0
    return round(max(original - new, 0.0))


def children_hours(headcount, minutes, call):
    """Headcount x hours for slots that were moved or taken indoors, else 0."""
    if call in ("MOVE", "INDOORS"):
        return round(headcount * minutes / 60, 1)
    return 0.0


if __name__ == "__main__":
    # Class 2B, 38 children, 40-minute PE moved from 140 ug/m3 to 71 ug/m3.
    print("moved:  ", ug_avoided(38, 40, "moderate", 140, "MOVE", 71), "ug")
    print("indoors:", ug_avoided(38, 40, "moderate", 140, "INDOORS"), "ug")
    print("hours:  ", children_hours(38, 40, "MOVE"))
