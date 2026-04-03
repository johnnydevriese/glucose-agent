import datetime as dt
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from glucose_agent.parser import extract_candidate_from_text, validate_candidate
from glucose_agent.schemas import MealStatus


class ParserTests(unittest.TestCase):
    def test_extracts_today_and_fasting(self):
        today = dt.date(2026, 4, 3)
        candidate = extract_candidate_from_text(
            "My blood sugar was 118 mg/dL today fasting", today
        )
        self.assertEqual(candidate.glucose_level, 118.0)
        self.assertEqual(candidate.date, today)
        self.assertEqual(candidate.meal_status, MealStatus.FASTING)
        self.assertIsNone(validate_candidate(candidate, today))

    def test_extracts_yesterday_after_breakfast(self):
        today = dt.date(2026, 4, 3)
        candidate = extract_candidate_from_text(
            "I was 142 yesterday after breakfast", today
        )
        self.assertEqual(candidate.glucose_level, 142.0)
        self.assertEqual(candidate.date, dt.date(2026, 4, 2))
        self.assertEqual(candidate.meal_status, MealStatus.PRANDIAL)


if __name__ == "__main__":
    unittest.main()
