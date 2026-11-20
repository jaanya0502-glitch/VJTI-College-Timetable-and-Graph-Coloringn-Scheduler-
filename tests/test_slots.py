"""Unit tests for engine/slots.py"""
import unittest
from engine.slots import SlotGrid


class TestSlots(unittest.TestCase):
    def setUp(self):
        self.grid = SlotGrid()

    def test_grid_initialization(self):
        # 5 days x 6 periods = 30 slots
        self.assertEqual(self.grid.total_slots, 30)
        self.assertEqual(len(self.grid.all_slots()), 30)

    def test_lunch_boundary_exclusion(self):
        # Period 2 is followed by lunch. So slot at period 2 cannot start a 2-period lab
        # because slot+1 would cross into Period 3 (after lunch)!
        for day_idx in range(5):
            lunch_slot_id = day_idx * 6 + 2 # Period 2
            self.assertFalse(self.grid.is_valid_lab_start(lunch_slot_id))
            self.assertEqual(self.grid.get_lab_consecutive_slots(lunch_slot_id), [])

    def test_day_boundary_exclusion(self):
        # Period 5 is the last period of the day. A 2-period lab cannot start at Period 5.
        for day_idx in range(5):
            end_slot_id = day_idx * 6 + 5 # Period 5
            self.assertFalse(self.grid.is_valid_lab_start(end_slot_id))

    def test_valid_lab_starts(self):
        # Period 0 (08:30-09:30) and Period 3 (12:15-13:15) are valid lab starts
        for day_idx in range(5):
            p0_slot = day_idx * 6 + 0
            p3_slot = day_idx * 6 + 3
            self.assertTrue(self.grid.is_valid_lab_start(p0_slot))
            self.assertTrue(self.grid.is_valid_lab_start(p3_slot))
            self.assertEqual(self.grid.get_lab_consecutive_slots(p0_slot), [p0_slot, p0_slot + 1])
            self.assertEqual(self.grid.get_lab_consecutive_slots(p3_slot), [p3_slot, p3_slot + 1])

    def test_consecutive_same_day(self):
        self.assertTrue(self.grid.is_consecutive_same_day(0, 1))
        # Between period 5 of day 0 and period 0 of day 1 is NOT consecutive in same day
        self.assertFalse(self.grid.is_consecutive_same_day(5, 6))


if __name__ == "__main__":
    unittest.main()
