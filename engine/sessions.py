"""
engine/sessions.py
Expands teaching assignments into schedulable atomic session nodes.
Part of Nia's deliverables.
"""

from typing import List
from .models import Assignment, SessionNode, RoomType


def expand_assignments_to_sessions(assignments: List[Assignment]) -> List[SessionNode]:
    """
    Expands assignments into atomic session nodes:
    - A 1-hour theory assignment of weekly_hours=N generates N nodes with duration_periods=1.
    - A 2-hour lab assignment generates (weekly_hours // 2) nodes with duration_periods=2.
      (If weekly_hours is odd for lab, remainder 1-hour lab node is generated).
    """
    sessions: List[SessionNode] = []

    for asg in assignments:
        if asg.is_lab:
            # 2-hour lab blocks
            lab_blocks = asg.weekly_hours // 2
            for b in range(lab_blocks):
                node_id = f"{asg.id}_lab_b{b}"
                sessions.append(
                    SessionNode(
                        id=node_id,
                        assignment_id=asg.id,
                        subject_id=asg.subject_id,
                        faculty_id=asg.faculty_id,
                        division_id=asg.division_id,
                        batch_id=asg.batch_id,
                        duration_periods=2,
                        is_lab=True,
                        room_type_required=asg.room_type_required or RoomType.COMPUTER_LAB,
                        student_count=asg.student_count,
                    )
                )
            # Handle any leftover 1-hour lab block
            rem = asg.weekly_hours % 2
            if rem > 0:
                node_id = f"{asg.id}_lab_rem"
                sessions.append(
                    SessionNode(
                        id=node_id,
                        assignment_id=asg.id,
                        subject_id=asg.subject_id,
                        faculty_id=asg.faculty_id,
                        division_id=asg.division_id,
                        batch_id=asg.batch_id,
                        duration_periods=1,
                        is_lab=True,
                        room_type_required=asg.room_type_required or RoomType.COMPUTER_LAB,
                        student_count=asg.student_count,
                    )
                )
        else:
            # Theory sessions: 1-hour nodes
            for h in range(asg.weekly_hours):
                node_id = f"{asg.id}_th_h{h}"
                sessions.append(
                    SessionNode(
                        id=node_id,
                        assignment_id=asg.id,
                        subject_id=asg.subject_id,
                        faculty_id=asg.faculty_id,
                        division_id=asg.division_id,
                        batch_id=asg.batch_id,
                        duration_periods=1,
                        is_lab=False,
                        room_type_required=asg.room_type_required or RoomType.CLASSROOM,
                        student_count=asg.student_count,
                    )
                )

    return sessions
