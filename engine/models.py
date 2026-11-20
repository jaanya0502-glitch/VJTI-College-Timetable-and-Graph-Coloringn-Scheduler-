"""
engine/models.py
Plain dataclasses for academic scheduling entities.
Part of Chakshu's deliverables.
"""

from __future__ import annotations
from dataclasses import dataclass, field, asdict
from enum import Enum
from typing import List, Optional, Dict, Any


class RoomType(str, Enum):
    CLASSROOM = "CLASSROOM"
    COMPUTER_LAB = "COMPUTER_LAB"
    ELECTRONICS_LAB = "ELECTRONICS_LAB"
    SEMINAR_HALL = "SEMINAR_HALL"


@dataclass
class Year:
    id: str                # e.g., "FY", "SY", "TY"
    name: str              # e.g., "First Year"
    semester: int          # e.g., 1, 3, 5


@dataclass
class Division:
    id: str                # e.g., "FY-A"
    name: str              # e.g., "Division A"
    year_id: str           # e.g., "FY"
    student_count: int = 60


@dataclass
class Batch:
    id: str                # e.g., "FY-A1"
    name: str              # e.g., "Batch A1"
    division_id: str       # e.g., "FY-A"
    student_count: int = 20


@dataclass
class Subject:
    id: str                # e.g., "CS101"
    code: str              # e.g., "CS101"
    name: str              # e.g., "Data Structures"
    year_id: str           # e.g., "FY"
    is_lab: bool = False
    weekly_hours: int = 4
    credits: int = 4


@dataclass
class Faculty:
    id: str                # e.g., "FAC_01"
    name: str              # e.g., "Dr. Alan Turing"
    department: str        # e.g., "Computer Science"
    designation: str        # e.g., "Professor", "HOD", "Assistant Professor"
    max_hours_per_day: int = 4
    max_hours_per_week: int = 16
    unavailable_slots: List[int] = field(default_factory=list) # Slot IDs where faculty cannot teach


@dataclass
class Room:
    id: str                # e.g., "R_101"
    name: str              # e.g., "LH 101"
    room_type: RoomType    # e.g., RoomType.CLASSROOM
    capacity: int          # e.g., 70
    building: str = "Main Block"
    floor: int = 1
    tags: List[str] = field(default_factory=list)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> Room:
        rtype = data.get("room_type", "CLASSROOM")
        if isinstance(rtype, str):
            rtype = RoomType(rtype)
        return cls(
            id=data["id"],
            name=data["name"],
            room_type=rtype,
            capacity=data.get("capacity", 60),
            building=data.get("building", "Main Block"),
            floor=data.get("floor", 1),
            tags=data.get("tags", []),
        )


@dataclass
class Assignment:
    id: str                               # e.g., "ASG_01"
    subject_id: str                       # e.g., "CS101"
    faculty_id: str                       # e.g., "FAC_01"
    division_id: str                      # e.g., "FY-A"
    batch_id: Optional[str] = None        # e.g., "FY-A1" or None if entire division
    weekly_hours: int = 4                 # e.g., 4 for theory, 2 for lab
    is_lab: bool = False
    room_type_required: RoomType = RoomType.CLASSROOM
    student_count: int = 60

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> Assignment:
        rtype = data.get("room_type_required", "CLASSROOM")
        if isinstance(rtype, str):
            rtype = RoomType(rtype)
        return cls(
            id=data["id"],
            subject_id=data["subject_id"],
            faculty_id=data["faculty_id"],
            division_id=data["division_id"],
            batch_id=data.get("batch_id"),
            weekly_hours=data.get("weekly_hours", 4),
            is_lab=data.get("is_lab", False),
            room_type_required=rtype,
            student_count=data.get("student_count", 60),
        )


@dataclass
class TimeSlot:
    id: int                # 0..N-1
    day_index: int         # 0..4 (Mon-Fri)
    day_name: str          # "Monday", "Tuesday", etc.
    period_index: int      # 0..5
    start_time: str        # e.g., "08:30"
    end_time: str          # e.g., "09:30"
    is_lunch: bool = False
    is_lab_start: bool = False # Whether a 2-period lab can begin at this slot


@dataclass
class SessionNode:
    """
    Atomic schedulable session expanded from an assignment.
    """
    id: str                               # e.g., "ASG_01_s0"
    assignment_id: str
    subject_id: str
    faculty_id: str
    division_id: str
    batch_id: Optional[str] = None
    duration_periods: int = 1             # 1 for theory, 2 for lab block
    is_lab: bool = False
    room_type_required: RoomType = RoomType.CLASSROOM
    student_count: int = 60
    required_tags: List[str] = field(default_factory=list)

    def __hash__(self):
        return hash(self.id)

    def __eq__(self, other):
        if not isinstance(other, SessionNode):
            return False
        return self.id == other.id


@dataclass
class TimetableEntry:
    assignment_id: str
    session_id: str
    slot_id: int
    slot_ids: List[int]                   # [slot_id] or [slot_id, slot_id + 1]
    day: str
    period: int
    faculty_id: str
    division_id: str
    subject_id: str
    batch_id: Optional[str] = None
    room_id: Optional[str] = None
    is_lab: bool = False


@dataclass
class Timetable:
    entries: List[TimetableEntry] = field(default_factory=list)
    unplaced_sessions: List[SessionNode] = field(default_factory=list)
    conflicts: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
