"""Unit tests for io module"""
import unittest
import os
import tempfile
from api import (
    serialize_college_data, deserialize_college_data,
    serialize_timetable, deserialize_timetable,
    save_json, load_json, load_assignments_from_csv, load_rooms_from_csv,
    export_entries_to_csv, export_to_html
)
from engine.models import (
    Year, Division, Batch, Subject, Faculty, Room, RoomType,
    Assignment, Timetable, TimetableEntry
)
from engine.slots import SlotGrid


class TestIO(unittest.TestCase):
    def test_json_roundtrip(self):
        years = [Year(id="FY", name="First Year", semester=1)]
        divisions = [Division(id="FY-A", name="Div A", year_id="FY")]
        batches = [Batch(id="FY-A1", name="Batch A1", division_id="FY-A")]
        subjects = [Subject(id="CS101", code="CS101", name="DSA", year_id="FY")]
        faculty = [Faculty(id="FAC_01", name="Prof Alan", department="CS", designation="Prof")]
        rooms = [Room(id="CR_101", name="Room 101", room_type=RoomType.CLASSROOM, capacity=70)]
        assignments = [Assignment(id="ASG_01", subject_id="CS101", faculty_id="FAC_01", division_id="FY-A")]

        data = serialize_college_data(years, divisions, batches, subjects, faculty, rooms, assignments)

        with tempfile.NamedTemporaryFile("w+", delete=False, suffix=".json") as tmp:
            save_json(data, tmp.name)
            loaded_data = load_json(tmp.name)
            os.remove(tmp.name)

        y2, d2, b2, s2, f2, r2, a2 = deserialize_college_data(loaded_data)
        self.assertEqual(len(y2), 1)
        self.assertEqual(y2[0].id, "FY")
        self.assertEqual(a2[0].faculty_id, "FAC_01")

    def test_csv_loaders(self):
        data_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "data"))
        asg_csv = os.path.join(data_dir, "faculty_loads.csv")
        rooms_csv = os.path.join(data_dir, "rooms.csv")

        asgs = load_assignments_from_csv(asg_csv)
        self.assertGreater(len(asgs), 0)
        self.assertEqual(asgs[0].division_id, "FY-A")

        rooms = load_rooms_from_csv(rooms_csv)
        self.assertGreater(len(rooms), 0)
        self.assertEqual(rooms[0].room_type, RoomType.CLASSROOM)

    def test_html_exporter(self):
        grid = SlotGrid()
        e1 = TimetableEntry(
            assignment_id="a1", session_id="s1", slot_id=0, slot_ids=[0],
            day="Monday", period=0, faculty_id="FAC_01", division_id="FY-A",
            subject_id="CS101"
        )
        tt = Timetable(entries=[e1])
        with tempfile.NamedTemporaryFile("w+", delete=False, suffix=".html") as tmp:
            html = export_to_html(tt, grid, tmp.name)
            self.assertTrue(os.path.exists(tmp.name))
            os.remove(tmp.name)
        self.assertIn("CS101", html)
        self.assertIn("FY-A", html)

    def test_csv_exporter(self):
        tt = Timetable(entries=[TimetableEntry(
            assignment_id="a1", session_id="s1", slot_id=0, slot_ids=[0],
            day="Monday", period=0, faculty_id="FAC_01", division_id="FY-A",
            subject_id="CS101"
        )])
        with tempfile.NamedTemporaryFile("w+", delete=False, suffix=".csv") as tmp:
            export_entries_to_csv(tt, tmp.name)
            tmp.seek(0)
            content = tmp.read()
            os.remove(tmp.name)
        self.assertIn("Session ID", content)
        self.assertIn("CS101", content)


if __name__ == "__main__":
    unittest.main()
