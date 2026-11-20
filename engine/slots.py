"""
engine/slots.py
Day x Period grid generator, handling lunch exclusions and 2-period lab block rules.
Part of Chakshu's deliverables.
"""

from typing import List, Dict, Optional, Tuple
from .models import TimeSlot

DEFAULT_DAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"]
DEFAULT_PERIOD_TIMES = [
    ("08:30", "09:30"), # Period 0
    ("09:30", "10:30"), # Period 1
    ("10:30", "11:30"), # Period 2
    # Lunch break 11:30 - 12:15
    ("12:15", "13:15"), # Period 3
    ("13:15", "14:15"), # Period 4
    ("14:15", "15:15"), # Period 5
]
DEFAULT_LUNCH_AFTER_PERIOD = 2  # Lunch occurs after Period 2 (before Period 3)


class SlotGrid:
    def __init__(
        self,
        days: Optional[List[str]] = None,
        period_times: Optional[List[Tuple[str, str]]] = None,
        lunch_after_period: int = DEFAULT_LUNCH_AFTER_PERIOD
    ):
        self.days = days or DEFAULT_DAYS
        self.period_times = period_times or DEFAULT_PERIOD_TIMES
        self.periods_per_day = len(self.period_times)
        self.lunch_after_period = lunch_after_period
        self.total_slots = len(self.days) * self.periods_per_day
        self._slots: Dict[int, TimeSlot] = {}
        self._build_grid()

    def _build_grid(self):
        slot_id = 0
        for day_idx, day_name in enumerate(self.days):
            for p_idx, (start, end) in enumerate(self.period_times):
                # A 2-period lab starting at p_idx occupies p_idx and p_idx + 1.
                # It cannot cross lunch: p_idx cannot be lunch_after_period.
                # It cannot cross day boundary: p_idx + 1 < periods_per_day.
                can_start_lab = (
                    p_idx != self.lunch_after_period and 
                    (p_idx + 1) < self.periods_per_day
                )
                ts = TimeSlot(
                    id=slot_id,
                    day_index=day_idx,
                    day_name=day_name,
                    period_index=p_idx,
                    start_time=start,
                    end_time=end,
                    is_lunch=False,
                    is_lab_start=can_start_lab
                )
                self._slots[slot_id] = ts
                slot_id += 1

    def get_slot(self, slot_id: int) -> Optional[TimeSlot]:
        return self._slots.get(slot_id)

    def all_slots(self) -> List[TimeSlot]:
        return list(self._slots.values())

    def get_day_slots(self, day_index: int) -> List[TimeSlot]:
        start = day_index * self.periods_per_day
        end = start + self.periods_per_day
        return [self._slots[i] for i in range(start, end) if i in self._slots]

    def is_valid_lab_start(self, slot_id: int) -> bool:
        slot = self.get_slot(slot_id)
        return bool(slot and slot.is_lab_start)

    def get_lab_consecutive_slots(self, slot_id: int) -> List[int]:
        """
        Returns [slot_id, slot_id + 1] if slot_id is a valid lab start, else empty list.
        """
        if not self.is_valid_lab_start(slot_id):
            return []
        return [slot_id, slot_id + 1]

    def is_consecutive_same_day(self, slot_a: int, slot_b: int) -> bool:
        sa = self.get_slot(slot_a)
        sb = self.get_slot(slot_b)
        if not sa or not sb:
            return False
        return sa.day_index == sb.day_index and abs(sa.period_index - sb.period_index) == 1

    def slot_label(self, slot_id: int) -> str:
        s = self.get_slot(slot_id)
        if not s:
            return f"Slot #{slot_id}"
        return f"{s.day_name} P{s.period_index + 1} ({s.start_time}-{s.end_time})"

    def to_dict_list(self) -> List[Dict]:
        return [
            {
                "id": s.id,
                "day_index": s.day_index,
                "day_name": s.day_name,
                "period_index": s.period_index,
                "start_time": s.start_time,
                "end_time": s.end_time,
                "is_lab_start": s.is_lab_start,
                "label": self.slot_label(s.id)
            }
            for s in self.all_slots()
        ]
