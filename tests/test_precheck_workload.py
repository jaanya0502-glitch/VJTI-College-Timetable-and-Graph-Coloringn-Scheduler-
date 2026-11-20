"""Unit tests for engine/precheck.py and engine/workload.py"""
import unittest
from engine.models import Faculty, Room, RoomType, Assignment, Timetable, TimetableEntry, Division, Year
from engine.slots import SlotGrid
from engine.precheck import FeasibilityChecker
from engine.workload import compute_workload_analytics


class TestPrecheckWorkload(unittest.TestCase):
    def test_precheck_detects_overloaded_faculty(self):
        grid = SlotGrid()
        faculty = [Faculty(id="FAC_01", name="Prof Turing", department="CS", designation="Prof", max_hours_per_week=10)]
        rooms = [Room(id="CR_101", name="R1", room_type=RoomType.CLASSROOM, capacity=70)]
        checker = FeasibilityChecker(grid, rooms, faculty)

        # Assign 15 hours to FAC_01 (exceeds max of 10)
        asgs = [Assignment(id="a1", subject_id="CS1", faculty_id="FAC_01", division_id="FY-A", weekly_hours=15)]
        report = checker.check(asgs)

        self.assertFalse(report.is_feasible)
        categories = [i.category for i in report.issues]
        self.assertIn("FACULTY_OVERLOAD", categories)

    def test_workload_analytics(self):
        grid = SlotGrid()
        faculty = [Faculty(id="FAC_01", name="Prof Alan", department="CS", designation="Prof", max_hours_per_week=16)]
        divs = [Division(id="FY-A", name="Div A", year_id="FY")]
        years = [Year(id="FY", name="First Year", semester=1)]

        e1 = TimetableEntry(assignment_id="a1", session_id="s1", slot_id=0, slot_ids=[0], day="Monday", period=0, faculty_id="FAC_01", division_id="FY-A", subject_id="CS101")
        tt = Timetable(entries=[e1])

        analytics = compute_workload_analytics(tt, grid, faculty, divs, years)
        self.assertEqual(analytics["faculty_workload"]["FAC_01"]["assigned_hours"], 1)
        self.assertEqual(analytics["division_workload"]["FY-A"]["theory_hours"], 1)
        self.assertEqual(len(analytics["heatmap"]), 30) # 5 days x 6 periods


if __name__ == "__main__":
    unittest.main()
