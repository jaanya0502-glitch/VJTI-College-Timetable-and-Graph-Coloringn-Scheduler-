"""Unit tests for engine/graph.py"""
import unittest
from engine.models import SessionNode
from engine.graph import ConflictGraph, EdgeType


class TestConflictGraph(unittest.TestCase):
    def test_faculty_conflict_edge(self):
        # Two sessions taught by the same faculty must conflict
        n1 = SessionNode(id="n1", assignment_id="a1", subject_id="CS1", faculty_id="FAC_01", division_id="FY-A")
        n2 = SessionNode(id="n2", assignment_id="a2", subject_id="CS2", faculty_id="FAC_01", division_id="SY-A")
        g = ConflictGraph([n1, n2])

        self.assertTrue(g.has_edge("n1", "n2"))
        self.assertEqual(g.get_edge_type("n1", "n2"), EdgeType.FACULTY)

    def test_division_theory_conflict_edge(self):
        # Two whole-division theory sessions for the same division must conflict
        n1 = SessionNode(id="n1", assignment_id="a1", subject_id="CS1", faculty_id="FAC_01", division_id="FY-A")
        n2 = SessionNode(id="n2", assignment_id="a2", subject_id="MA1", faculty_id="FAC_02", division_id="FY-A")
        g = ConflictGraph([n1, n2])

        self.assertTrue(g.has_edge("n1", "n2"))
        self.assertEqual(g.get_edge_type("n1", "n2"), EdgeType.DIVISION)

    def test_batch_division_conflict_edge(self):
        # Whole-division theory vs batch lab of the same division must conflict
        th = SessionNode(id="th", assignment_id="a1", subject_id="CS1", faculty_id="FAC_01", division_id="FY-A", batch_id=None)
        lab = SessionNode(id="lab", assignment_id="a2", subject_id="CS1L", faculty_id="FAC_02", division_id="FY-A", batch_id="FY-A1", is_lab=True)
        g = ConflictGraph([th, lab])

        self.assertTrue(g.has_edge("th", "lab"))
        self.assertEqual(g.get_edge_type("th", "lab"), EdgeType.BATCH_DIVISION)

    def test_batch_parallel_labs_no_conflict(self):
        # Two different batches (A1 and A2) of the same division in lab with different faculties do NOT conflict!
        lab1 = SessionNode(id="l1", assignment_id="a1", subject_id="CS1L", faculty_id="FAC_01", division_id="FY-A", batch_id="FY-A1", is_lab=True)
        lab2 = SessionNode(id="l2", assignment_id="a2", subject_id="CS1L", faculty_id="FAC_02", division_id="FY-A", batch_id="FY-A2", is_lab=True)
        g = ConflictGraph([lab1, lab2])

        self.assertFalse(g.has_edge("l1", "l2"))

    def test_chromatic_lower_bound(self):
        # If faculty has 6 sessions, lower bound >= 6
        nodes = [
            SessionNode(id=f"n_{i}", assignment_id=f"a_{i}", subject_id=f"CS_{i}", faculty_id="FAC_HEAVY", division_id=f"DIV_{i}")
            for i in range(6)
        ]
        g = ConflictGraph(nodes)
        self.assertGreaterEqual(g.chromatic_lower_bound(), 6)


if __name__ == "__main__":
    unittest.main()
