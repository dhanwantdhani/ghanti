"""Seed the live school. Edit SCHOOL below, then: make seed

Schema of SCHOOL (also what store.get_school returns):
    school_id: str
    name: str
    city: str
    lat, lon: float               the school's coordinates
    coordinator_chat_id: str      Telegram chat id (send /start to the bot, read it from getUpdates)
    teacher_chat_id: str
    move_windows: list of "HH:MM" times the ground is free for a moved slot
    slots: list of {slot_id, label, start, minutes, headcount, intensity, weekdays, max_age}
"""
import os
import sys
import json

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

# The live school. The LOCATION is real (Rohini Sector 9, Delhi: a same-hour
# station 1.2 km away and the DTU archive monitor 3 km away). The timetable
# is ILLUSTRATIVE, modelled on a typical Delhi private school day (assembly
# 7:50, 40-minute periods, recess 10:50, Saturday working), and is labelled
# as such on the page and in the README. Replace it with a real one if a
# teacher shares theirs.
SCHOOL = {
    "school_id": "demo-school",
    "name": "Demo Public School, Rohini",
    "city": "Delhi",
    "lat": 28.7234,
    "lon": 77.1123,
    "illustrative": True,
    "coordinator_chat_id": os.environ.get("COORDINATOR_CHAT_ID", ""),
    "teacher_chat_id": os.environ.get("TEACHER_CHAT_ID", ""),
    "move_windows": ["11:50", "12:30", "13:20"],
    "slots": [
        {"slot_id": "assembly", "label": "Morning assembly", "start": "07:50", "minutes": 20, "headcount": 400,
         "intensity": "light", "weekdays": ["mon", "tue", "wed", "thu", "fri", "sat"], "max_age": 14},
        {"slot_id": "pe_2b", "label": "PE, Class 2B", "start": "08:30", "minutes": 40, "headcount": 38,
         "intensity": "moderate", "weekdays": ["mon", "wed", "fri", "sat"], "max_age": 7},
        {"slot_id": "pe_4a", "label": "PE, Class 4A", "start": "09:50", "minutes": 40, "headcount": 40,
         "intensity": "moderate", "weekdays": ["tue", "thu", "sat"], "max_age": 9},
        {"slot_id": "recess", "label": "Recess, outdoor play", "start": "10:50", "minutes": 20, "headcount": 400,
         "intensity": "light", "weekdays": ["mon", "tue", "wed", "thu", "fri", "sat"], "max_age": 14},
        {"slot_id": "pe_7c", "label": "PE, Class 7C", "start": "11:10", "minutes": 40, "headcount": 42,
         "intensity": "vigorous", "weekdays": ["mon", "wed", "fri"], "max_age": 12},
        {"slot_id": "games", "label": "Games period", "start": "12:30", "minutes": 40, "headcount": 60,
         "intensity": "moderate", "weekdays": ["mon", "tue", "wed", "thu", "fri"], "max_age": 14},
        {"slot_id": "practice", "label": "Saturday sports practice", "start": "08:00", "minutes": 90, "headcount": 30,
         "intensity": "vigorous", "weekdays": ["sat"], "max_age": 16},
    ],
}

if __name__ == "__main__":
    if os.environ.get("SCHOOLS_TABLE"):
        from ghanti import store
        store.put_school(SCHOOL)
        print("seeded", SCHOOL["school_id"], "into", os.environ["SCHOOLS_TABLE"])
    else:
        print("SCHOOLS_TABLE not set; printing the record instead")
        print(json.dumps(SCHOOL, indent=2))
