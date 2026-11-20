"""
io/json_store.py
Save and load complete college snapshots and generated timetables to/from JSON.
Part of Chakshu's deliverables.
"""

import json
from dataclasses import asdict
from typing import Dict, Any, List, Tuple
from engine.models import (
    Year, Division, Batch, Subject, Faculty, Room, RoomType,
    Assignment, SessionNode, TimetableEntry, Timetable
)


def serialize_college_data(
    years: List[Year],
    divisions: List[Division],
    batches: List[Batch],
    subjects: List[Subject],
    faculty: List[Faculty],
    rooms: List[Room],
    assignments: List[Assignment]
) -> Dict[str, Any]:
    return {
        "years": [asdict(y) for y in years],
        "divisions": [asdict(d) for d in divisions],
        "batches": [asdict(b) for b in batches],
        "subjects": [asdict(s) for s in subjects],
        "faculty": [asdict(f) for f in faculty],
        "rooms": [asdict(r) for r in rooms],
        "assignments": [asdict(a) for a in assignments],
    }


def deserialize_college_data(
    data: Dict[str, Any]
) -> Tuple[List[Year], List[Division], List[Batch], List[Subject], List[Faculty], List[Room], List[Assignment]]:
    years = [Year(**y) for y in data.get("years", [])]
    divisions = [Division(**d) for d in data.get("divisions", [])]
    batches = [Batch(**b) for b in data.get("batches", [])]
    subjects = [Subject(**s) for s in data.get("subjects", [])]
    faculty = [Faculty(**f) for f in data.get("faculty", [])]
    rooms = [Room.from_dict(r) for r in data.get("rooms", [])]
    assignments = [Assignment.from_dict(a) for a in data.get("assignments", [])]
    return years, divisions, batches, subjects, faculty, rooms, assignments


def serialize_timetable(timetable: Timetable) -> Dict[str, Any]:
    return {
        "entries": [asdict(e) for e in timetable.entries],
        "unplaced_sessions": [asdict(s) for s in timetable.unplaced_sessions],
        "conflicts": timetable.conflicts,
        "metadata": timetable.metadata
    }


def deserialize_timetable(data: Dict[str, Any]) -> Timetable:
    entries = [TimetableEntry(**e) for e in data.get("entries", [])]
    unplaced = []
    for s in data.get("unplaced_sessions", []):
        rtype = s.get("room_type_required", "CLASSROOM")
        if isinstance(rtype, str):
            rtype = RoomType(rtype)
        unplaced.append(SessionNode(
            id=s["id"],
            assignment_id=s["assignment_id"],
            subject_id=s["subject_id"],
            faculty_id=s["faculty_id"],
            division_id=s["division_id"],
            batch_id=s.get("batch_id"),
            duration_periods=s.get("duration_periods", 1),
            is_lab=s.get("is_lab", False),
            room_type_required=rtype,
            student_count=s.get("student_count", 60),
        ))
    return Timetable(
        entries=entries,
        unplaced_sessions=unplaced,
        conflicts=data.get("conflicts", []),
        metadata=data.get("metadata", {})
    )


def save_json(data: Any, filepath: str) -> None:
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)


def load_json(filepath: str) -> Any:
    with open(filepath, "r", encoding="utf-8") as f:
        return json.load(f)
