import unittest
from datetime import datetime

from lockerfit.layout import LockerLayout
from lockerfit.models import ActiveSession, AssignmentRequest
from lockerfit.optimizer import LockerAssigner
from lockerfit.predictor import DurationPredictor


class LockerAssignerTest(unittest.TestCase):
    def test_recommends_available_locker_far_from_active_sessions(self):
        layout = LockerLayout.odd_even(number_of_lockers=20, pairs_per_row=10)
        assigner = LockerAssigner(layout=layout, predictor=DurationPredictor(default_minutes=90))
        active = [
            ActiveSession(
                session_id="a",
                locker_id=1,
                check_in=datetime.fromisoformat("2026-07-03T18:00:00"),
                expected_check_out=datetime.fromisoformat("2026-07-03T19:30:00"),
            ),
            ActiveSession(
                session_id="b",
                locker_id=3,
                check_in=datetime.fromisoformat("2026-07-03T18:02:00"),
                expected_check_out=datetime.fromisoformat("2026-07-03T19:40:00"),
            ),
        ]

        options = assigner.recommend(
            AssignmentRequest(
                arrived_at=datetime.fromisoformat("2026-07-03T18:05:00"),
                preferred_tier="top",
            ),
            active,
            top_k=3,
        )

        self.assertNotIn(options[0].locker_id, {1, 3})
        self.assertGreaterEqual(options[0].locker_id, 15)

    def test_can_skip_regenerated_options(self):
        layout = LockerLayout.odd_even(number_of_lockers=20, pairs_per_row=10)
        assigner = LockerAssigner(layout=layout)
        request = AssignmentRequest(arrived_at=datetime.fromisoformat("2026-07-03T18:05:00"))

        first = assigner.assign(request, [])
        second = assigner.assign(request, [], skip_locker_ids={first.locker_id})

        self.assertNotEqual(first.locker_id, second.locker_id)


if __name__ == "__main__":
    unittest.main()
