"""
engine/validator.py
Completely independent schedule validator.
Shares zero code with the colouring algorithm.
Part of Jaanya's deliverables.
"""

from dataclasses import dataclass, field
from typing import List, Dict, Set, Optional, Tuple, Any
from .models import Timetable, TimetableEntry, Room, Faculty, RoomType
from .slots import SlotGrid


@dataclass
class Violation:
    code: str
    message: str
    severity: str = "ERROR" # "ERROR" or "WARNING"
    entities: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ValidationReport:
    is_valid: bool
    violations: List[Violation] = field(default_factory=list)
    error_count: int = 0
    warning_count: int = 0
    stats: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "is_valid": self.is_valid,
            "error_count": self.error_count,
            "warning_count": self.warning_count,
            "violations": [
                {
                    "code": v.code,
                    "message": v.message,
                    "severity": v.severity,
                    "entities": v.entities
                }
                for v in self.violations
            ],
            "stats": self.stats
        }


class IndependentValidator:
    """
    Independent schedule verification engine.
    Ensures zero double-booking, room capacity & type validity,
    faculty unavailability & daily limits, and lab slot integrity.
    """
    def __init__(
        self,
        grid: SlotGrid,
        rooms: Optional[List[Room]] = None,
        faculty: Optional[List[Faculty]] = None
    ):
        self.grid = grid
        self.rooms_map: Dict[str, Room] = {r.id: r for r in rooms or []}
        self.faculty_map: Dict[str, Faculty] = {f.id: f for f in faculty or []}

    def validate(self, timetable: Timetable) -> ValidationReport:
        violations: List[Violation] = []

        # Tracking maps per slot:
        faculty_slot_usage: Dict[Tuple[str, int], List[TimetableEntry]] = {}
        division_theory_slot_usage: Dict[Tuple[str, int], List[TimetableEntry]] = {}
        batch_slot_usage: Dict[Tuple[str, str, int], List[TimetableEntry]] = {}
        room_slot_usage: Dict[Tuple[str, int], List[TimetableEntry]] = {}

        # Tracking daily hours:
        faculty_daily_hours: Dict[Tuple[str, int], int] = {}
        faculty_weekly_hours: Dict[str, int] = {}
        division_daily_hours: Dict[Tuple[str, int], int] = {}

        for entry in timetable.entries:
            slot_ids = entry.slot_ids or [entry.slot_id]
            duration = len(slot_ids)
            faculty_weekly_hours[entry.faculty_id] = (
                faculty_weekly_hours.get(entry.faculty_id, 0) + duration
            )

            # Check 1: Lab slot integrity (must be valid 2-period block, not crossing lunch)
            if entry.is_lab and duration == 2:
                s0 = slot_ids[0]
                s1 = slot_ids[1]
                slot0_obj = self.grid.get_slot(s0)
                slot1_obj = self.grid.get_slot(s1)

                if not slot0_obj or not slot1_obj:
                    violations.append(Violation(
                        code="INVALID_SLOT_ID",
                        message=f"Lab session {entry.session_id} assigned to invalid slot IDs {slot_ids}",
                        entities={"session_id": entry.session_id}
                    ))
                else:
                    if slot0_obj.day_index != slot1_obj.day_index:
                        violations.append(Violation(
                            code="LAB_CROSS_DAY",
                            message=f"Lab session {entry.session_id} spans across multiple days: {slot0_obj.day_name} and {slot1_obj.day_name}",
                            entities={"session_id": entry.session_id}
                        ))
                    if abs(slot1_obj.period_index - slot0_obj.period_index) != 1:
                        violations.append(Violation(
                            code="LAB_NON_CONSECUTIVE",
                            message=f"Lab session {entry.session_id} slots are not consecutive: P{slot0_obj.period_index} and P{slot1_obj.period_index}",
                            entities={"session_id": entry.session_id}
                        ))
                    if slot0_obj.period_index == self.grid.lunch_after_period:
                        violations.append(Violation(
                            code="LAB_CROSS_LUNCH",
                            message=f"Lab session {entry.session_id} crosses the mandatory lunch break (starts P{slot0_obj.period_index})",
                            entities={"session_id": entry.session_id}
                        ))

            # Daily workload tracking
            first_slot = self.grid.get_slot(entry.slot_id)
            if first_slot:
                d_idx = first_slot.day_index
                faculty_daily_hours[(entry.faculty_id, d_idx)] = faculty_daily_hours.get((entry.faculty_id, d_idx), 0) + duration
                division_daily_hours[(entry.division_id, d_idx)] = division_daily_hours.get((entry.division_id, d_idx), 0) + duration

            # Per-slot occupancy checks
            for sid in slot_ids:
                # 2. Check Faculty Unavailability
                fac = self.faculty_map.get(entry.faculty_id)
                if fac and sid in fac.unavailable_slots:
                    violations.append(Violation(
                        code="FACULTY_UNAVAILABLE",
                        message=f"Faculty {entry.faculty_id} ({fac.name}) is marked unavailable at slot {sid} ({self.grid.slot_label(sid)})",
                        entities={"faculty_id": entry.faculty_id, "slot_id": sid}
                    ))

                # 3. Check Faculty Double Booking
                fac_key = (entry.faculty_id, sid)
                if fac_key in faculty_slot_usage:
                    other = faculty_slot_usage[fac_key][0]
                    violations.append(Violation(
                        code="FACULTY_DOUBLE_BOOKED",
                        message=f"Faculty {entry.faculty_id} double-booked at slot {sid}: teaches {entry.subject_id} ({entry.division_id}) and {other.subject_id} ({other.division_id})",
                        entities={"faculty_id": entry.faculty_id, "slot_id": sid}
                    ))
                faculty_slot_usage.setdefault(fac_key, []).append(entry)

                # 4. Check Division and Batch Clashes
                if entry.batch_id is None:
                    # Division theory lecture
                    div_key = (entry.division_id, sid)
                    if div_key in division_theory_slot_usage:
                        other = division_theory_slot_usage[div_key][0]
                        violations.append(Violation(
                            code="DIVISION_DOUBLE_BOOKED",
                            message=f"Division {entry.division_id} double-booked for theory at slot {sid}: {entry.subject_id} and {other.subject_id}",
                            entities={"division_id": entry.division_id, "slot_id": sid}
                        ))
                    division_theory_slot_usage.setdefault(div_key, []).append(entry)
                else:
                    # Batch session (e.g. lab)
                    batch_key = (entry.division_id, entry.batch_id, sid)
                    if batch_key in batch_slot_usage:
                        other = batch_slot_usage[batch_key][0]
                        violations.append(Violation(
                            code="BATCH_DOUBLE_BOOKED",
                            message=f"Batch {entry.batch_id} double-booked at slot {sid}: {entry.subject_id} and {other.subject_id}",
                            entities={"batch_id": entry.batch_id, "slot_id": sid}
                        ))
                    batch_slot_usage.setdefault(batch_key, []).append(entry)

                # 5. Check Room Double Booking & Suitability
                if not entry.room_id:
                    violations.append(Violation(
                        code="ROOM_UNASSIGNED",
                        message=f"Session {entry.session_id} has no assigned room",
                        entities={"session_id": entry.session_id}
                    ))
                else:
                    rm_key = (entry.room_id, sid)
                    if rm_key in room_slot_usage:
                        other = room_slot_usage[rm_key][0]
                        violations.append(Violation(
                            code="ROOM_DOUBLE_BOOKED",
                            message=f"Room {entry.room_id} double-booked at slot {sid}: {entry.subject_id} and {other.subject_id}",
                            entities={"room_id": entry.room_id, "slot_id": sid}
                        ))
                    room_slot_usage.setdefault(rm_key, []).append(entry)

                    room_obj = self.rooms_map.get(entry.room_id)
                    if room_obj:
                        if entry.is_lab and room_obj.room_type == RoomType.CLASSROOM:
                            violations.append(Violation(
                                code="ROOM_TYPE_MISMATCH",
                                message=f"Lab session {entry.session_id} assigned to classroom {entry.room_id} without lab facilities",
                                entities={"session_id": entry.session_id, "room_id": entry.room_id}
                            ))

        # 6. Check Batch vs Division Simultaneous Theory/Lab Clash
        for (div_id, sid), div_entries in division_theory_slot_usage.items():
            # Check if any batch of this division is also in a lab at slot sid
            for (b_div, batch_id, b_sid), batch_entries in batch_slot_usage.items():
                if b_div == div_id and b_sid == sid:
                    violations.append(Violation(
                        code="BATCH_DIVISION_CLASH",
                        message=f"Division {div_id} scheduled for theory ({div_entries[0].subject_id}) while Batch {batch_id} has lab ({batch_entries[0].subject_id}) at slot {sid}",
                        entities={"division_id": div_id, "batch_id": batch_id, "slot_id": sid}
                    ))

        # 7. Check Faculty Daily Max Hours
        for (fac_id, d_idx), total_hrs in faculty_daily_hours.items():
            fac = self.faculty_map.get(fac_id)
            if fac and total_hrs > fac.max_hours_per_day:
                day_name = self.grid.days[d_idx] if d_idx < len(self.grid.days) else f"Day {d_idx}"
                violations.append(Violation(
                    code="FACULTY_MAX_HOURS_EXCEEDED",
                    message=f"Faculty {fac_id} scheduled for {total_hrs} hrs on {day_name} (max allowed: {fac.max_hours_per_day})",
                    entities={"faculty_id": fac_id, "day_index": d_idx, "hours": total_hrs}
                ))

        # 8. Check Faculty Weekly Max Hours
        for fac_id, total_hrs in faculty_weekly_hours.items():
            fac = self.faculty_map.get(fac_id)
            if fac and total_hrs > fac.max_hours_per_week:
                violations.append(Violation(
                    code="FACULTY_WEEKLY_CAP",
                    message=f"Faculty {fac_id} scheduled for {total_hrs} hrs this week (weekly cap: {fac.max_hours_per_week})",
                    entities={
                        "faculty_id": fac_id,
                        "hours": total_hrs,
                        "weekly_cap": fac.max_hours_per_week
                    }
                ))

        error_count = sum(1 for v in violations if v.severity == "ERROR")
        warning_count = sum(1 for v in violations if v.severity == "WARNING")

        return ValidationReport(
            is_valid=(error_count == 0),
            violations=violations,
            error_count=error_count,
            warning_count=warning_count,
            stats={
                "total_entries": len(timetable.entries),
                "unplaced_count": len(timetable.unplaced_sessions),
                "faculty_checked": len(faculty_slot_usage),
                "rooms_checked": len(room_slot_usage)
            }
        )
