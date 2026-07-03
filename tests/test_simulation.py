import unittest

from lockerfit.layout import LockerLayout
from lockerfit.simulation import compare_strategies, generate_visits


class SimulationTest(unittest.TestCase):
    def test_compare_strategies_returns_metrics(self):
        layout = LockerLayout.odd_even(number_of_lockers=80, pairs_per_row=20)
        visits = generate_visits(days=3, visitors_per_day=25, seed=3)

        random_result, smart_result = compare_strategies(layout, visits, seed=5)

        self.assertEqual(random_result.strategy, "random")
        self.assertEqual(smart_result.strategy, "smart")
        self.assertGreater(random_result.assigned, 0)
        self.assertGreater(smart_result.assigned, 0)
        self.assertGreaterEqual(random_result.close_overlap_rate, 0)
        self.assertGreaterEqual(smart_result.average_nearest_distance, 0)


if __name__ == "__main__":
    unittest.main()
