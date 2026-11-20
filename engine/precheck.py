"""
engine/precheck.py
Pre-run feasibility check and chromatic lower-bound analyzer.
Part of Shraddha's deliverables.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Set, Optional, Any
from .models import Faculty, Room, RoomType, Assignment
from .graph import ConflictGraph
from .slots import SlotGrid


@dataclass
class PrecheckIssue:
    issue_type: str        # "ERROR" or "WARNING"
    category: str          # "FACULTY_OVERLOAD", "LAB_SHORTAGE", "ROOM_SHORTAGE", "BOUND_EXCEEDED"
    message: str
    details: Dict[str, Any] = field(default_factory=dict)


@dataclass
class PrecheckReport:
    is_feasible: bool
    issues: List[PrecheckIssue] = field(default_factory=list)
    chromatic_lower_bound: int = 0
    total_slots_available: int = 0
    lower_bound_explanation: str = ""
    stats: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "is_feasible": self.is_feasible,
            "issues": [
                {
                    "issue_type": i.issue_type,
                    "category": i.category,
                    "message": i.message,
                    "details": i.details
                }
                for i in self.issues
            ],
            "chromatic_lower_bound": self.chromatic_lower_bound,
            "total_slots_available": self.total_slots_available,
            "lower_bound_explanation": self.lower_bound_explanation,
            "stats": self.stats
        }


class FeasibilityChecker:
    def __init__(self, grid: SlotGrid, rooms: List[Room], faculty: List[Faculty]):
        self.grid = grid
        self.rooms = rooms
        self.faculty_map = {f.id: f for f in faculty}

    def check(self, assignments: List[Assignment], graph: Optional[ConflictGraph] = None) -> PrecheckReport:
        issues: List[PrecheckIssue] = []
        total_slots = self.grid.total_slots

        # 1. Faculty Workload vs Limits
        faculty_hours: Dict[str, int] = {}
        for asg in assignments:
            faculty_hours[asg.faculty_id] = faculty_hours.get(asg.faculty_id, 0) + asg.weekly_hours

        for fid, total_hrs in faculty_hours.items():
            fac = self.faculty_map.get(fid)
            if not fac:
                issues.append(PrecheckIssue(
                    issue_type="WARNING",
                    category="FACULTY_UNKNOWN",
                    message=f"Faculty {fid} in assignment is not registered in faculty database",
                    details={"faculty_id": fid}
                ))
                continue

            # Check weekly max limit
            if total_hrs > fac.max_hours_per_week:
                issues.append(PrecheckIssue(
                    issue_type="ERROR",
                    category="FACULTY_OVERLOAD",
                    message=f"Faculty {fac.name} ({fid}) assigned {total_hrs} weekly hours, exceeding max limit of {fac.max_hours_per_week} hrs",
                    details={"faculty_id": fid, "assigned_hours": total_hrs, "limit": fac.max_hours_per_week}
                ))

            # Check available slots minus unavailable slots
            available_slots_for_fac = total_slots - len(fac.unavailable_slots)
            if total_hrs > available_slots_for_fac:
                issues.append(PrecheckIssue(
                    issue_type="ERROR",
                    category="FACULTY_SLOT_STARVATION",
                    message=f"Faculty {fac.name} has {total_hrs} hrs assigned but only {available_slots_for_fac} slots available after leaves",
                    details={"faculty_id": fid, "assigned_hours": total_hrs, "available_slots": available_slots_for_fac}
                ))

        # 2. Lab Room Capacity Shortage
        total_lab_hours = sum(asg.weekly_hours for asg in assignments if asg.is_lab)
        lab_rooms = [r for r in self.rooms if r.room_type in (RoomType.COMPUTER_LAB, RoomType.ELECTRONICS_LAB)]
        max_lab_capacity_hours = len(lab_rooms) * total_slots

        if total_lab_hours > max_lab_capacity_hours:
            issues.append(PrecheckIssue(
                issue_type="ERROR",
                category="LAB_SHORTAGE",
                message=f"Total lab hours ({total_lab_hours} hrs) exceed total available lab capacity ({max_lab_capacity_hours} hrs across {len(lab_rooms)} labs)",
                details={"total_lab_hours": total_lab_hours, "capacity_hours": max_lab_capacity_hours}
            ))

        # 3. Classroom Capacity Shortage
        total_theory_hours = sum(asg.weekly_hours for asg in assignments if not asg.is_lab)
        classrooms = [r for r in self.rooms if r.room_type in (RoomType.CLASSROOM, RoomType.SEMINAR_HALL)]
        max_theory_capacity_hours = len(classrooms) * total_slots

        if total_theory_hours > max_theory_capacity_hours:
            issues.append(PrecheckIssue(
                issue_type="ERROR",
                category="ROOM_SHORTAGE",
                message=f"Total theory hours ({total_theory_hours} hrs) exceed available classroom capacity ({max_theory_capacity_hours} hrs across {len(classrooms)} classrooms)",
                details={"total_theory_hours": total_theory_hours, "capacity_hours": max_theory_capacity_hours}
            ))

        # 4. Chromatic Lower Bound Calculation
        chromatic_lb = 0
        explanation_lines = []

        # Bound by faculty
        max_fac_id = max(faculty_hours.keys(), key=lambda k: faculty_hours[k], default="")
        max_fac_hrs = faculty_hours.get(max_fac_id, 0)
        chromatic_lb = max(chromatic_lb, max_fac_hrs)
        if max_fac_id:
            explanation_lines.append(f"Faculty bound: Faculty {max_fac_id} has {max_fac_hrs} hours (requires >= {max_fac_hrs} slots).")

        # Bound by division
        div_hours: Dict[str, int] = {}
        for asg in assignments:
            if not asg.is_lab or asg.batch_id is None:
                div_hours[asg.division_id] = div_hours.get(asg.division_id, 0) + asg.weekly_hours
        max_div_id = max(div_hours.keys(), key=lambda k: div_hours[k], default="")
        max_div_hrs = div_hours.get(max_div_id, 0)
        chromatic_lb = max(chromatic_lb, max_div_hrs)
        if max_div_id:
            explanation_lines.append(f"Division bound: Division {max_div_id} has {max_div_hrs} theory hours (requires >= {max_div_hrs} slots).")

        # Bound by conflict graph clique if provided
        if graph:
            graph_lb = graph.chromatic_lower_bound()
            if graph_lb > chromatic_lb:
                chromatic_lb = graph_lb
                explanation_lines.append(f"Graph clique bound: Maximum clique in conflict graph omega(G) = {graph_lb}.")

        if chromatic_lb > total_slots:
            issues.append(PrecheckIssue(
                issue_type="ERROR",
                category="BOUND_EXCEEDED",
                message=f"Chromatic lower bound ({chromatic_lb}) exceeds total available slots ({total_slots}). Timetable is mathematically infeasible without increasing periods or days.",
                details={"chromatic_lower_bound": chromatic_lb, "total_slots": total_slots}
            ))

        has_errors = any(i.issue_type == "ERROR" for i in issues)
        explanation = " ".join(explanation_lines) or "Feasible with standard parameters."

        return PrecheckReport(
            is_feasible=(not has_errors),
            issues=issues,
            chromatic_lower_bound=chromatic_lb,
            total_slots_available=total_slots,
            lower_bound_explanation=explanation,
            stats={
                "total_assignments": len(assignments),
                "total_weekly_hours": sum(a.weekly_hours for a in assignments),
                "total_lab_hours": total_lab_hours,
                "total_theory_hours": total_theory_hours,
                "num_classrooms": len(classrooms),
                "num_labs": len(lab_rooms)
            }
        )
