"""Unit tests for engine/models.py"""
import unittest
from engine.models import (
    Year, Division, Batch, Subject, Faculty, Room, RoomType,
    Assignment, TimeSlot, SessionNode, TimetableEntry, Timetable
)


class TestModels(unittest.TestCase):
    def test_year_creation(self):
        y = Year(id="FY", name="First Year", semester=1)
        self.assertEqual(y.id, "FY")
        self.assertEqual(y.semester, 1)

    def test_division_and_batch(self):
        div = Division(id="FY-A", name="Div A", year_id="FY", student_count=60)
        batch = Batch(id="FY-A1", name="Batch A1", division_id="FY-A", student_count=20)
        self.assertEqual(div.student_count, 60)
        self.assertEqual(batch.division_id, "FY-A")

    def test_room_from_dict(self):
        r_dict = {
            "id": "CR_101",
            "name": "LH 101",
            "room_type": "CLASSROOM",
            "capacity": 70,
            "building": "Main",
            "floor": 1
        }
        r = Room.from_dict(r_dict)
        self.assertEqual(r.room_type, RoomType.CLASSROOM)
        self.assertEqual(r.capacity, 70)

    def test_assignment_from_dict(self):
        a_dict = {
            "id": "ASG_01",
            "subject_id": "CS101",
            "faculty_id": "FAC_01",
            "division_id": "FY-A",
            "batch_id": None,
            "weekly_hours": 4,
            "is_lab": False,
            "room_type_required": "CLASSROOM"
        }
        asg = Assignment.from_dict(a_dict)
        self.assertEqual(asg.weekly_hours, 4)
        self.assertFalse(asg.is_lab)
        self.assertIsNone(asg.batch_id)

    def test_session_node_hash_eq(self):
        s1 = SessionNode(
            id="node_1", assignment_id="a1", subject_id="s1",
            faculty_id="f1", division_id="d1"
        )
        s2 = SessionNode(
            id="node_1", assignment_id="a1", subject_id="s1",
            faculty_id="f1", division_id="d1"
        )
        s3 = SessionNode(
            id="node_2", assignment_id="a1", subject_id="s1",
            faculty_id="f1", division_id="d1"
        )
        self.assertEqual(s1, s2)
        self.assertNotEqual(s1, s3)
        self.assertEqual(len({s1, s2, s3}), 2)


if __name__ == "__main__":
    unittest.main()
