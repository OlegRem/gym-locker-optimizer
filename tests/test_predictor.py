import unittest
from datetime import datetime

from lockerfit.models import VisitRecord
from lockerfit.predictor import DurationPredictor


class DurationPredictorTest(unittest.TestCase):
    def test_uses_visitor_weekday_history_when_available(self):
        records = [
            VisitRecord(
                "anon-a",
                datetime.fromisoformat("2026-06-01T18:00:00"),
                datetime.fromisoformat("2026-06-01T19:20:00"),
            ),
            VisitRecord(
                "anon-a",
                datetime.fromisoformat("2026-06-08T18:00:00"),
                datetime.fromisoformat("2026-06-08T19:30:00"),
            ),
            VisitRecord(
                "anon-a",
                datetime.fromisoformat("2026-06-15T18:00:00"),
                datetime.fromisoformat("2026-06-15T19:40:00"),
            ),
        ]

        prediction = DurationPredictor().fit(records).predict(
            datetime.fromisoformat("2026-06-22T18:00:00"),
            "anon-a",
        )

        self.assertEqual(int(prediction.total_seconds() // 60), 90)


if __name__ == "__main__":
    unittest.main()
