"""Unit tests for engine/validator.py"""
import unittest
from engine.models import Timetable, TimetableEntry, Room, RoomType, Faculty
from engine.slots import SlotGrid
from engine.validator import IndependentValidator


class TestValidator(unittest.TestCase):
    def setUp(self):
        self.grid = SlotGrid()
        self.rooms = [
            Room(id="CR_101", name="Room 101", room_type=RoomType.CLASSROOM, capacity=70),
            Room(id="LAB_01", name="Lab 01", room_type=RoomType.COMPUTER_LAB, capacity=30)
        ]
        self.faculty = [
            Faculty(id="FAC_01", name="Prof Turing", department="CS", designation="Prof", max_hours_per_day=3, unavailable_slots=[0])
        ]
        self.validator = IndependentValidator(self.grid, self.rooms, self.faculty)

    def test_valid_timetable_passes(self):
        e1 = TimetableEntry(
            assignment_id="a1", session_id="s1", slot_id=1, slot_ids=[1],
            day="Monday", period=1, faculty_id="FAC_01", division_id="FY-A",
            subject_id="CS101", room_id="CR_101", is_lab=False
        )
        e2 = TimetableEntry(
            assignment_id="a2", session_id="s2", slot_id=2, slot_ids=[2],
            day="Monday", period=2, faculty_id="FAC_01", division_id="FY-A",
            subject_id="CS101", room_id="CR_101", is_lab=False
        )
        tt = Timetable(entries=[e1, e2])
        report = self.validator.validate(tt)
        self.assertTrue(report.is_valid)
        self.assertEqual(report.error_count, 0)

    def test_detect_faculty_double_booked(self):
        # Same faculty in two places at slot 1
        e1 = TimetableEntry(
            assignment_id="a1", session_id="s1", slot_id=1, slot_ids=[1],
            day="Monday", period=1, faculty_id="FAC_01", division_id="FY-A",
            subject_id="CS101"
        )
        e2 = TimetableEntry(
            assignment_id="a2", session_id="s2", slot_id=1, slot_ids=[1],
            day="Monday", period=1, faculty_id="FAC_01", division_id="SY-A",
            subject_id="CS201"
        )
        tt = Timetable(entries=[e1, e2])
        report = self.validator.validate(tt)
        self.assertFalse(report.is_valid)
        codes = [v.code for v in report.violations]
        self.assertIn("FACULTY_DOUBLE_BOOKED", codes)

    def test_detect_batch_division_clash(self):
        # Whole division FY-A in lecture while FY-A1 is in lab at slot 1
        e_div = TimetableEntry(
            assignment_id="a1", session_id="s1", slot_id=1, slot_ids=[1],
            day="Monday", period=1, faculty_id="FAC_02", division_id="FY-A",
            subject_id="CS101", batch_id=None
        )
        e_batch = TimetableEntry(
            assignment_id="a2", session_id="s2", slot_id=1, slot_ids=[1],
            day="Monday", period=1, faculty_id="FAC_03", division_id="FY-A",
            batch_id="FY-A1", subject_id="CS101L", is_lab=True
        )
        tt = Timetable(entries=[e_div, e_batch])
        report = self.validator.validate(tt)
        self.assertFalse(report.is_valid)
        codes = [v.code for v in report.violations]
        self.assertIn("BATCH_DIVISION_CLASH", codes)

    def test_detect_faculty_unavailable_violation(self):
        # FAC_01 is unavailable at slot 0
        e1 = TimetableEntry(
            assignment_id="a1", session_id="s1", slot_id=0, slot_ids=[0],
            day="Monday", period=0, faculty_id="FAC_01", division_id="FY-A",
            subject_id="CS101"
        )
        tt = Timetable(entries=[e1])
        report = self.validator.validate(tt)
        self.assertFalse(report.is_valid)
        codes = [v.code for v in report.violations]
        self.assertIn("FACULTY_UNAVAILABLE", codes)

    def test_detect_lab_cross_lunch_violation(self):
        # Lab starting at period 2 crosses lunch
        e_lab = TimetableEntry(
            assignment_id="a1", session_id="s1", slot_id=2, slot_ids=[2, 3],
            day="Monday", period=2, faculty_id="FAC_01", division_id="FY-A",
            subject_id="CS101L", is_lab=True
        )
        tt = Timetable(entries=[e_lab])
        report = self.validator.validate(tt)
        self.assertFalse(report.is_valid)
        codes = [v.code for v in report.violations]
        self.assertIn("LAB_CROSS_LUNCH", codes)


if __name__ == "__main__":
    unittest.main()
