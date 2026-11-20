"""Unit tests for engine/sessions.py"""
import unittest
from engine.models import Assignment, RoomType
from engine.sessions import expand_assignments_to_sessions


class TestSessions(unittest.TestCase):
    def test_expand_theory_assignment(self):
        asg = Assignment(
            id="ASG_TH_01",
            subject_id="CS101",
            faculty_id="FAC_01",
            division_id="FY-A",
            weekly_hours=4,
            is_lab=False
        )
        sessions = expand_assignments_to_sessions([asg])
        self.assertEqual(len(sessions), 4)
        for s in sessions:
            self.assertEqual(s.duration_periods, 1)
            self.assertFalse(s.is_lab)
            self.assertEqual(s.faculty_id, "FAC_01")

    def test_expand_lab_assignment(self):
        asg = Assignment(
            id="ASG_LAB_01",
            subject_id="CS101L",
            faculty_id="FAC_02",
            division_id="FY-A",
            batch_id="FY-A1",
            weekly_hours=2,
            is_lab=True,
            room_type_required=RoomType.COMPUTER_LAB
        )
        sessions = expand_assignments_to_sessions([asg])
        self.assertEqual(len(sessions), 1)
        self.assertEqual(sessions[0].duration_periods, 2)
        self.assertTrue(sessions[0].is_lab)
        self.assertEqual(sessions[0].batch_id, "FY-A1")

    def test_expands_each_weekly_theory_hour_to_a_session(self):
        asg = Assignment(
            id="ASG_LOCK",
            subject_id="CS101",
            faculty_id="FAC_01",
            division_id="FY-A",
            weekly_hours=2,
            is_lab=False
        )
        sessions = expand_assignments_to_sessions([asg])
        self.assertEqual(len(sessions), 2)
        self.assertEqual({session.duration_periods for session in sessions}, {1})


if __name__ == "__main__":
    unittest.main()
