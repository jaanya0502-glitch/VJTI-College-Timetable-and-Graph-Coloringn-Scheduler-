"""Unit tests for engine/rooms.py"""
import unittest
from engine.models import Room, RoomType, SessionNode
from engine.rooms import RoomAllocator, bipartite_match


class TestRooms(unittest.TestCase):
    def test_bipartite_match_basic(self):
        s1 = SessionNode(id="s1", assignment_id="a1", subject_id="c1", faculty_id="f1", division_id="d1")
        s2 = SessionNode(id="s2", assignment_id="a2", subject_id="c2", faculty_id="f2", division_id="d2")
        rooms = [
            Room(id="r1", name="R1", room_type=RoomType.CLASSROOM, capacity=70),
            Room(id="r2", name="R2", room_type=RoomType.CLASSROOM, capacity=70)
        ]
        eligible_map = {
            "s1": ["r1", "r2"],
            "s2": ["r1"]
        }
        matching = bipartite_match([s1, s2], rooms, eligible_map)
        self.assertEqual(len(matching), 2)
        # Both must get distinct rooms
        self.assertNotEqual(matching["s1"], matching["s2"])

    def test_room_allocator_lab_vs_classroom(self):
        rooms = [
            Room(id="CR_101", name="Classroom 101", room_type=RoomType.CLASSROOM, capacity=70),
            Room(id="LAB_01", name="Computer Lab", room_type=RoomType.COMPUTER_LAB, capacity=30)
        ]
        allocator = RoomAllocator(rooms)

        th_node = SessionNode(id="th1", assignment_id="a1", subject_id="CS1", faculty_id="f1", division_id="FY-A", student_count=60, is_lab=False, room_type_required=RoomType.CLASSROOM)
        lab_node = SessionNode(id="lab1", assignment_id="a2", subject_id="CS1L", faculty_id="f2", division_id="FY-A", student_count=20, is_lab=True, room_type_required=RoomType.COMPUTER_LAB)

        slot_allocations = {
            "th1": [0],
            "lab1": [0, 1]
        }
        session_nodes = {"th1": th_node, "lab1": lab_node}

        rm_assignments, unassigned = allocator.assign_rooms_for_timetable(slot_allocations, session_nodes)

        self.assertEqual(len(unassigned), 0)
        self.assertEqual(rm_assignments["th1"], "CR_101")
        self.assertEqual(rm_assignments["lab1"], "LAB_01")


if __name__ == "__main__":
    unittest.main()
