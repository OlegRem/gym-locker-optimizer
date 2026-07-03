import unittest

from lockerfit.layout import LockerLayout


class LockerLayoutTest(unittest.TestCase):
    def test_odd_even_neighbors_match_physical_layout(self):
        layout = LockerLayout.odd_even(number_of_lockers=530, pairs_per_row=53)

        self.assertEqual(layout.get(101).tier, "top")
        self.assertEqual(layout.get(102).tier, "bottom")
        self.assertAlmostEqual(layout.distance(101, 103), 1.0)
        self.assertLess(layout.distance(101, 102), 1.0)

    def test_rows_have_gap(self):
        layout = LockerLayout.odd_even(number_of_lockers=530, pairs_per_row=53)

        self.assertGreater(layout.distance(1, 107), layout.distance(1, 3))


if __name__ == "__main__":
    unittest.main()
