"""Unit tests for the deterministic rules. Run: make test"""
import unittest
from ghanti.rules import Slot, decide, band, slot_value, was_right
from ghanti.dose import ug_avoided, children_hours

SLOTS = [
    Slot("assembly", "Morning assembly", "07:50", 20, 400, "light", ["mon", "tue", "wed", "thu", "fri", "sat"], max_age=16),
    Slot("pe_2b", "PE, Class 2B", "08:30", 40, 38, "moderate", ["mon", "wed", "fri", "sat"], max_age=7),
    Slot("games", "Games period", "12:30", 40, 60, "moderate", ["mon", "tue", "wed", "thu", "fri", "sat"], max_age=14),
]
WINDOWS = ["11:10", "12:30", "13:20"]


def calls_by_id(calls):
    return {c.slot_id: c for c in calls}


class RulesTest(unittest.TestCase):

    def test_bands(self):
        self.assertEqual(band(30), "Good")
        self.assertEqual(band(60), "Satisfactory")
        self.assertEqual(band(90), "Moderate")
        self.assertEqual(band(91), "Poor")
        self.assertEqual(band(250), "Very Poor")
        self.assertEqual(band(251), "Severe")

    def test_slot_value_spans_hours(self):
        self.assertEqual(slot_value({7: 100, 8: 50}, "07:50", 20), 75.0)
        self.assertIsNone(slot_value({}, "07:50", 20))

    def test_clean_day_is_outdoors(self):
        hourly = {h: 40 for h in range(6, 18)}
        for c in decide(SLOTS, hourly, WINDOWS, "fri"):
            self.assertEqual(c.call, "OUTDOORS")

    def test_flat_moderate_day_is_no_change(self):
        hourly = {h: 75 for h in range(6, 18)}
        for c in decide(SLOTS, hourly, WINDOWS, "fri"):
            self.assertEqual(c.call, "NO_CHANGE")

    def test_everything_poor_is_indoors(self):
        hourly = {h: 150 for h in range(6, 18)}
        calls = decide(SLOTS, hourly, WINDOWS, "fri")
        self.assertTrue(all(c.call == "INDOORS" for c in calls))
        self.assertIn("would not help", calls[0].reason)

    def test_dirty_morning_moves_to_clean_window(self):
        hourly = {7: 150, 8: 142, 9: 120, 10: 98, 11: 80, 12: 66, 13: 58, 14: 55}
        calls = calls_by_id(decide(SLOTS, hourly, WINDOWS, "fri"))
        self.assertEqual(calls["assembly"].call, "MOVE")
        self.assertEqual(calls["assembly"].move_to, "13:20")
        self.assertEqual(calls["pe_2b"].call, "MOVE")
        self.assertEqual(calls["pe_2b"].move_to, "12:30")
        self.assertEqual(calls["games"].call, "CAUTION")
        self.assertEqual(calls["assembly"].children_hours, round(400 * 20 / 60, 1))

    def test_excluded_window_is_skipped(self):
        hourly = {7: 150, 8: 142, 9: 120, 10: 98, 11: 80, 12: 66, 13: 58, 14: 55}
        calls = calls_by_id(decide(SLOTS, hourly, WINDOWS, "fri", excluded_windows={"13:20"}))
        self.assertEqual(calls["assembly"].move_to, "12:30")   # worst slot takes the best free window
        self.assertEqual(calls["pe_2b"].call, "MOVE")
        self.assertEqual(calls["pe_2b"].move_to, "11:10")      # 80 is under 90 and under 0.7 x 131
        # with every window ruled out, the slot goes indoors
        calls = calls_by_id(decide(SLOTS, hourly, WINDOWS, "fri", excluded_windows={"11:10", "12:30", "13:20"}))
        self.assertEqual(calls["pe_2b"].call, "INDOORS")

    def test_weekday_filter(self):
        hourly = {h: 40 for h in range(6, 18)}
        ids = [c.slot_id for c in decide(SLOTS, hourly, WINDOWS, "tue")]
        self.assertEqual(ids, ["assembly", "games"])

    def test_children_rule_in_moderate_band(self):
        hourly = {h: 75 for h in range(6, 18)}
        hourly[13] = 40  # one clean window
        calls = calls_by_id(decide(SLOTS, hourly, WINDOWS, "fri"))
        self.assertEqual(calls["assembly"].call, "OUTDOORS")   # light, older children
        self.assertEqual(calls["pe_2b"].call, "MOVE")           # age 7, moderate intensity

    def test_was_right(self):
        self.assertTrue(was_right(120, 100))
        self.assertFalse(was_right(120, 60))
        self.assertTrue(was_right(60, 40))
        self.assertIsNone(was_right(120, None))


class DoseTest(unittest.TestCase):

    def test_move_reduces_dose(self):
        self.assertEqual(ug_avoided(38, 40, "moderate", 140, "MOVE", 71), round(38 * 40 * 0.022 * (140 - 71)))

    def test_indoors_uses_seated_rate_and_factor(self):
        original = 38 * 40 * 0.022 * 140
        new = 38 * 40 * 0.0048 * 0.7 * 140
        self.assertEqual(ug_avoided(38, 40, "moderate", 140, "INDOORS"), round(original - new))

    def test_unchanged_is_zero(self):
        self.assertEqual(ug_avoided(38, 40, "moderate", 140, "OUTDOORS"), 0.0)
        self.assertEqual(children_hours(38, 40, "OUTDOORS"), 0.0)
        self.assertEqual(children_hours(38, 40, "MOVE"), 25.3)


if __name__ == "__main__":
    unittest.main()
