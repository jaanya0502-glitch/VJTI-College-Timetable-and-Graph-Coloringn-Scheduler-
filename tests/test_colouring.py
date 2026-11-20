"""Unit tests for engine/colouring.py"""
import unittest
from engine.models import SessionNode, Faculty
from engine.slots import SlotGrid
from engine.graph import ConflictGraph
from engine.colouring import TimetableColorer


class TestColouring(unittest.TestCase):
    def setUp(self):
        self.grid = SlotGrid()

    def test_dsatur_basic_coloring(self):
        # 3 clashing nodes should receive 3 distinct slots
        n1 = SessionNode(id="n1", assignment_id="a1", subject_id="CS1", faculty_id="FAC_01", division_id="FY-A")
        n2 = SessionNode(id="n2", assignment_id="a2", subject_id="CS2", faculty_id="FAC_01", division_id="SY-A")
        n3 = SessionNode(id="n3", assignment_id="a3", subject_id="CS3", faculty_id="FAC_01", division_id="TY-A")
        g = ConflictGraph([n1, n2, n3])

        colorer = TimetableColorer(g, self.grid)
        res = colorer.solve_dsatur()

        self.assertEqual(res.algorithm, "DSATUR")
        self.assertEqual(len(res.assignments), 3)
        self.assertEqual(len(res.unallocated), 0)
        self.assertEqual(res.chromatic_number, 3)
        # All assigned slots should be distinct
        slots = list(res.assignments.values())
        self.assertEqual(len(set(slots)), 3)

    def test_welsh_powell_coloring(self):
        n1 = SessionNode(id="n1", assignment_id="a1", subject_id="CS1", faculty_id="FAC_01", division_id="FY-A")
        n2 = SessionNode(id="n2", assignment_id="a2", subject_id="CS2", faculty_id="FAC_01", division_id="SY-A")
        g = ConflictGraph([n1, n2])

        colorer = TimetableColorer(g, self.grid)
        res = colorer.solve_welsh_powell()

        self.assertEqual(len(res.assignments), 2)
        self.assertNotEqual(res.assignments["n1"], res.assignments["n2"])

    def test_faculty_unavailability_enforcement(self):
        # Faculty unavailable at slot 0
        fac = Faculty(id="FAC_01", name="Prof Test", department="CS", designation="Prof", unavailable_slots=[0])
        n1 = SessionNode(id="n1", assignment_id="a1", subject_id="CS1", faculty_id="FAC_01", division_id="FY-A")
        g = ConflictGraph([n1])

        colorer = TimetableColorer(g, self.grid, faculty_map={"FAC_01": fac})
        res = colorer.solve_dsatur()

        # Slot 0 was unavailable, so it must NOT be assigned slot 0
        self.assertNotEqual(res.assignments["n1"], 0)

    def test_two_period_lab_consecutive_slots(self):
        # 2-period lab should allocate [s, s+1]
        lab = SessionNode(id="lab1", assignment_id="a1", subject_id="CS101L", faculty_id="FAC_01", division_id="FY-A", batch_id="FY-A1", duration_periods=2, is_lab=True)
        g = ConflictGraph([lab])

        colorer = TimetableColorer(g, self.grid)
        res = colorer.solve_dsatur()

        allocated_slots = res.slot_allocations["lab1"]
        self.assertEqual(len(allocated_slots), 2)
        self.assertEqual(allocated_slots[1], allocated_slots[0] + 1)
        self.assertTrue(self.grid.is_valid_lab_start(allocated_slots[0]))


if __name__ == "__main__":
    unittest.main()
