"""CSV import helpers for faculty assignments and college rooms."""

import csv
from typing import List, TextIO, Union

from engine.models import Assignment, Room, RoomType


def _rows(filepath: Union[str, TextIO]):
    if hasattr(filepath, "read"):
        yield from csv.DictReader(filepath)
        return
    with open(filepath, mode="r", encoding="utf-8", newline="") as file:
        yield from csv.DictReader(file)


def load_assignments_from_csv(filepath: Union[str, TextIO]) -> List[Assignment]:
    """Load assignment rows from a faculty_loads.csv file."""
    assignments = []
    for row in _rows(filepath):
        batch = (row.get("batch_id") or "").strip()
        is_lab = (row.get("is_lab") or "false").strip().lower() in {"true", "1", "yes", "t"}
        room_type = (row.get("room_type") or "CLASSROOM").strip()
        assignments.append(Assignment(
            id=row["assignment_id"].strip(),
            subject_id=row["subject_id"].strip(),
            faculty_id=row["faculty_id"].strip(),
            division_id=row["division_id"].strip(),
            batch_id=batch if batch and batch.lower() not in {"none", "null", "-"} else None,
            weekly_hours=int(row.get("weekly_hours") or 4),
            is_lab=is_lab,
            room_type_required=RoomType(room_type),
            student_count=int(row.get("student_count") or 60),
        ))
    return assignments


def load_rooms_from_csv(filepath: Union[str, TextIO]) -> List[Room]:
    """Load room rows from a rooms.csv file."""
    rooms = []
    for row in _rows(filepath):
        rooms.append(Room(
            id=row["room_id"].strip(),
            name=row["name"].strip(),
            room_type=RoomType((row.get("room_type") or "CLASSROOM").strip()),
            capacity=int(row.get("capacity") or 60),
            building=(row.get("building") or "Main Block").strip(),
            floor=int(row.get("floor") or 1),
        ))
    return rooms
