"""Build the labelled replay week and store it under school_id "replay".

Uses Open-Meteo's archive (modelled air) for the seed school's coordinates
over a real November 2025 week, runs the same rules, and writes ledger rows
that the /replay route serves. Every row carries replay=True and the
label "modelled air". If you obtain the station's recorded hourly values
for that week from OpenAQ, swap them in and change the label to "recorded".
"""
import os
import sys
import json

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from datetime import date as ddate
from ghanti import forecast, rules, dose
from scripts.seed_school import SCHOOL

START, END = "2025-11-10", "2025-11-14"   # Monday to Friday
WEEKDAYS = ["mon", "tue", "wed", "thu", "fri", "sat", "sun"]

if __name__ == "__main__":
    days = forecast.fetch_archive(SCHOOL["lat"], SCHOOL["lon"], START, END)
    slots = [rules.Slot(**{k: s[k] for k in ("slot_id", "label", "start", "minutes", "headcount", "intensity", "weekdays")},
                        max_age=s.get("max_age", 18)) for s in SCHOOL["slots"]]
    by_id = {s["slot_id"]: s for s in SCHOOL["slots"]}
    rows = []
    for day in sorted(days):
        hourly = days[day]
        weekday = WEEKDAYS[ddate.fromisoformat(day).weekday()]
        for c in rules.decide(slots, hourly, SCHOOL["move_windows"], weekday):
            s = by_id[c.slot_id]
            c_new = hourly.get(int(c.move_to[:2])) if c.move_to else None
            rows.append({
                "date": day, "slot_id": c.slot_id, "label": c.label, "start": c.start, "call": c.call,
                "move_to": c.move_to, "forecast_pm25": c.forecast_pm25, "band": c.band, "reason": c.reason,
                "children_hours_moved": dose.children_hours(s["headcount"], s["minutes"], c.call),
                "ug_avoided": dose.ug_avoided(s["headcount"], s["minutes"], s["intensity"], c.forecast_pm25, c.call, c_new),
                "replay": True, "label_source": "REPLAY: modelled air (CAMS via Open-Meteo), Nov 2025",
            })
    for r in rows:
        print(f"{r['date']} {r['label']:<24} {r['start']} {r['forecast_pm25']:>6} {r['call']:<9} {(r['move_to'] or ''):<6} {r['children_hours_moved']:>6} h")
    out = os.path.join(os.path.dirname(__file__), "..", "seed", "replay_week.json")
    os.makedirs(os.path.dirname(out), exist_ok=True)
    json.dump(rows, open(out, "w"), indent=1)
    print("wrote", out)
    if os.environ.get("CALLS_TABLE"):
        from ghanti import store
        for r in rows:
            store.put_ledger("replay", r["date"], r["slot_id"], r)
        print("stored", len(rows), "replay rows in", os.environ["CALLS_TABLE"])
