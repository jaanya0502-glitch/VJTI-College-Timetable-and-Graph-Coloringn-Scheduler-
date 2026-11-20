"""
engine/rooms.py: Greedy best-fit room allocator for classrooms and specialized labs.
Assigns 2-period labs and larger classes first to the smallest fitting free room.
College lab project implementation avoiding complex bipartite matching algorithms.
"""

from typing import Dict, List, Set, Tuple, Any
from .models import Room, RoomType, SessionNode


def allocate_rooms(
    sessions: Any,
    slot_allocations: Dict[str, List[int]],
    rooms: List[Room]
) -> Tuple[Dict[str, str], List[str]]:
    """Greedy best-fit room allocator matching capacity, type, and tags chronologically."""
    session_map = sessions if isinstance(sessions, dict) else {s.id: s for s in sessions}
    assigned, busy = {}, set()

    # Process slot by slot chronologically.
    all_slots = sorted(list({s for slots in slot_allocations.values() for s in slots}))
    for slot in all_slots:
        current_sessions = [
            session_map[sid] for sid, slots in slot_allocations.items()
            if sid in session_map and slots and slots[0] == slot and sid not in assigned
        ]
        # 2-period labs and larger classes take priority
        current_sessions.sort(key=lambda n: (not n.is_lab, -n.duration_periods, -n.student_count))

        for node in current_sessions:
            needed = slot_allocations.get(node.id, [slot])
            eligible = [
                r for r in rooms
                if ((r.room_type == node.room_type_required) if node.is_lab else (
                    r.room_type in (RoomType.CLASSROOM, RoomType.SEMINAR_HALL, "CLASSROOM", "SEMINAR_HALL")
                ))
                and r.capacity >= node.student_count
                and all(tag in getattr(r, "tags", []) for tag in getattr(node, "required_tags", []))
                and all((r.id, s) not in busy for s in needed)
            ]
            if eligible:
                best = min(eligible, key=lambda r: r.capacity)
                assigned[node.id] = best.id
                for s in needed:
                    busy.add((best.id, s))

    return assigned, [sid for sid in session_map if sid not in assigned]


class RoomAllocator:
    def __init__(self, rooms: List[Room]):
        self.rooms = rooms

    def assign_rooms_for_timetable(self, slot_allocations, session_nodes):
        return allocate_rooms(session_nodes, slot_allocations, self.rooms)


def bipartite_match(sessions, rooms, eligible_map):
    """Compatibility match helper using standard augmenting paths."""
    match_r, match_s = {}, {}
    def dfs(u, visited):
        for v in eligible_map.get(u, []):
            if v not in visited:
                visited.add(v)
                if v not in match_r or dfs(match_r[v], visited):
                    match_r[v], match_s[u] = u, v
                    return True
        return False
    for s in sessions:
        dfs(s.id, set())
    return match_s
