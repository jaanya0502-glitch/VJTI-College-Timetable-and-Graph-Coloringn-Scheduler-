"""
engine/colouring.py
Graph colouring algorithms for timetable scheduling:

"""

import time
import random
from dataclasses import dataclass, field
from typing import Dict, List, Set, Optional, Tuple, Any
from .models import SessionNode, Faculty
from .graph import ConflictGraph
from .slots import SlotGrid


@dataclass
class ColouringResult:
    algorithm: str
    assignments: Dict[str, int]                 # node_id -> start slot_id
    slot_allocations: Dict[str, List[int]]       # node_id -> [slot_id] or [s, s+1]
    unallocated: List[SessionNode] = field(default_factory=list)
    chromatic_number: int = 0
    runtime_ms: float = 0.0
    iterations: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)


class TimetableColorer:
    def __init__(
        self,
        graph: ConflictGraph,
        grid: SlotGrid,
        faculty_map: Optional[Dict[str, Faculty]] = None,
        max_available_slots: Optional[int] = None,
        rooms: Optional[List[Any]] = None
    ):
        self.graph = graph
        self.grid = grid
        self.faculty_map = faculty_map or {}
        self.max_slots = max_available_slots or grid.total_slots
        self.rooms = rooms or []
        
        # Calculate room capacities per room type
        self.room_capacities: Dict[Any, int] = {}
        if self.rooms:
            for r in self.rooms:
                rtype = r.room_type if hasattr(r, 'room_type') else 'CLASSROOM'
                if hasattr(rtype, 'value'):
                    rtype = rtype.value
                self.room_capacities[rtype] = self.room_capacities.get(rtype, 0) + 1
                # Classrooms can also host standard lectures
                if rtype in ('CLASSROOM', 'SEMINAR_HALL'):
                    self.room_capacities['THEORY'] = self.room_capacities.get('THEORY', 0) + 1
        else:
            self.room_capacities = {}

    def _is_slot_valid(
        self,
        node: SessionNode,
        slot_id: int,
        allocations: Dict[str, List[int]],
        faculty_daily_hours: Dict[Tuple[str, int], int],
        division_daily_hours: Dict[Tuple[str, int], int]
    ) -> bool:
        """
        Verifies all hard constraints for placing node at slot_id:
        1. Lab validity: 2-period lab must start at a valid lab slot and stay within limits.
        2. Neighbor clash: neither slot_id nor slot_id+1 can clash with any neighbor.
        3. Faculty unavailability.
        4. Faculty daily workload cap.
        5. Division daily workload cap.
        """
        # Determine occupied slots
        if node.is_lab and node.duration_periods == 2:
            if not self.grid.is_valid_lab_start(slot_id):
                return False
            slots_needed = [slot_id, slot_id + 1]
        else:
            slots_needed = [slot_id]

        # Check slot upper bound
        if max(slots_needed) >= self.max_slots:
            return False

        # Check room capacity limits per slot
        if self.room_capacities:
            for s in slots_needed:
                if node.is_lab:
                    rtype = node.room_type_required
                    if hasattr(rtype, 'value'):
                        rtype = rtype.value
                    max_allowed = self.room_capacities.get(rtype, self.room_capacities.get('COMPUTER_LAB', 999))
                    curr_labs = sum(
                        1 for nid, slist in allocations.items() 
                        if s in slist and self.graph.nodes[nid].is_lab and (
                            str(getattr(self.graph.nodes[nid].room_type_required, 'value', self.graph.nodes[nid].room_type_required)) == str(rtype)
                        )
                    )
                    if curr_labs >= max_allowed:
                        return False
                else:
                    max_allowed = self.room_capacities.get('THEORY', 999)
                    curr_theory = sum(1 for nid, slist in allocations.items() if s in slist and not self.graph.nodes[nid].is_lab)
                    if curr_theory >= max_allowed:
                        return False

        # Faculty constraints
        fac = self.faculty_map.get(node.faculty_id)
        if fac:
            # Check unavailability
            for s in slots_needed:
                if s in fac.unavailable_slots:
                    return False

            # Check daily hour cap
            slot_obj = self.grid.get_slot(slot_id)
            if slot_obj:
                day_idx = slot_obj.day_index
                current_day_hrs = faculty_daily_hours.get((node.faculty_id, day_idx), 0)
                if current_day_hrs + node.duration_periods > fac.max_hours_per_day:
                    return False

        # Division daily workload cap (typically at most 6 hours/day)
        slot_obj = self.grid.get_slot(slot_id)
        if slot_obj:
            day_idx = slot_obj.day_index
            div_day_hrs = division_daily_hours.get((node.division_id, day_idx), 0)
            if div_day_hrs + node.duration_periods > self.grid.periods_per_day:
                return False

        # Conflict graph check: ensure none of the node's neighbors occupy any of slots_needed
        for nbr_id in self.graph.neighbors(node.id):
            if nbr_id in allocations:
                nbr_slots = allocations[nbr_id]
                for s in slots_needed:
                    if s in nbr_slots:
                        return False

        return True

    def solve_dsatur(self) -> ColouringResult:
        """
        DSATUR (Degree of Saturation) Graph Colouring:
        Chooses vertex with highest saturation degree, ties broken by uncolored degree.
        """
        start_time = time.perf_counter()
        allocations: Dict[str, List[int]] = {}
        primary_assignments: Dict[str, int] = {}
        unallocated: List[SessionNode] = []

        faculty_daily_hours: Dict[Tuple[str, int], int] = {}
        division_daily_hours: Dict[Tuple[str, int], int] = {}

        # Saturation sets: node_id -> set of distinct colors (slots) used by colored neighbors
        saturation: Dict[str, Set[int]] = {nid: set() for nid in self.graph.nodes}
        uncolored: Set[str] = set(self.graph.nodes.keys())
        iterations = 0

        while uncolored:
            iterations += 1
            # 1. Select vertex with maximum saturation degree
            # Tie-break 1: maximum degree in uncolored subgraph
            # Tie-break 2: maximum overall degree
            best_nid = None
            max_sat = -1
            max_uncolored_deg = -1
            max_overall_deg = -1

            for nid in uncolored:
                sat_deg = len(saturation[nid])
                uncolored_deg = sum(1 for nbr in self.graph.neighbors(nid) if nbr in uncolored)
                overall_deg = self.graph.degree(nid)

                if (sat_deg > max_sat or
                    (sat_deg == max_sat and uncolored_deg > max_uncolored_deg) or
                    (sat_deg == max_sat and uncolored_deg == max_uncolored_deg and overall_deg > max_overall_deg)):
                    best_nid = nid
                    max_sat = sat_deg
                    max_uncolored_deg = uncolored_deg
                    max_overall_deg = overall_deg

            chosen_node = self.graph.nodes[best_nid]

            # Assign the earliest available slot; hard constraints take priority.
            assigned_slot = None
            for slot_candidate in range(self.max_slots):
                if self._is_slot_valid(chosen_node, slot_candidate, allocations, faculty_daily_hours, division_daily_hours):
                    assigned_slot = slot_candidate
                    break

            if assigned_slot is not None:
                slots_needed = [assigned_slot, assigned_slot + 1] if chosen_node.is_lab and chosen_node.duration_periods == 2 else [assigned_slot]
                allocations[chosen_node.id] = slots_needed
                primary_assignments[chosen_node.id] = assigned_slot
                uncolored.remove(chosen_node.id)

                s_obj = self.grid.get_slot(assigned_slot)
                if s_obj:
                    day_idx = s_obj.day_index
                    faculty_daily_hours[(chosen_node.faculty_id, day_idx)] = faculty_daily_hours.get((chosen_node.faculty_id, day_idx), 0) + chosen_node.duration_periods
                    division_daily_hours[(chosen_node.division_id, day_idx)] = division_daily_hours.get((chosen_node.division_id, day_idx), 0) + chosen_node.duration_periods

                # Update saturation of uncolored neighbors
                for nbr_id in self.graph.neighbors(chosen_node.id):
                    for s in slots_needed:
                        saturation[nbr_id].add(s)
            else:
                # Could not allocate within available slots
                unallocated.append(chosen_node)
                uncolored.remove(chosen_node.id)

        all_used_slots = set()
        for slist in allocations.values():
            all_used_slots.update(slist)

        runtime = (time.perf_counter() - start_time) * 1000.0

        return ColouringResult(
            algorithm="DSATUR",
            assignments=primary_assignments,
            slot_allocations=allocations,
            unallocated=unallocated,
            chromatic_number=len(all_used_slots),
            runtime_ms=round(runtime, 2),
            iterations=iterations,
            metadata={"total_sessions": len(self.graph.nodes), "placed_sessions": len(primary_assignments)}
        )

    def solve_welsh_powell(self) -> ColouringResult:
        """
        Welsh-Powell Algorithm:
        Sorts nodes by degree descending, colors greedily.
        """
        start_time = time.perf_counter()
        allocations: Dict[str, List[int]] = {}
        primary_assignments: Dict[str, int] = {}
        unallocated: List[SessionNode] = []

        faculty_daily_hours: Dict[Tuple[str, int], int] = {}
        division_daily_hours: Dict[Tuple[str, int], int] = {}

        # Sort vertices by overall degree descending
        sorted_nodes = sorted(
            self.graph.nodes.values(),
            key=lambda n: self.graph.degree(n.id),
            reverse=True
        )

        iterations = 0
        for node in sorted_nodes:
            iterations += 1
            assigned_slot = None
            for slot_candidate in range(self.max_slots):
                if self._is_slot_valid(node, slot_candidate, allocations, faculty_daily_hours, division_daily_hours):
                    assigned_slot = slot_candidate
                    break

            if assigned_slot is not None:
                slots_needed = [assigned_slot, assigned_slot + 1] if node.is_lab and node.duration_periods == 2 else [assigned_slot]
                allocations[node.id] = slots_needed
                primary_assignments[node.id] = assigned_slot

                s_obj = self.grid.get_slot(assigned_slot)
                if s_obj:
                    day_idx = s_obj.day_index
                    faculty_daily_hours[(node.faculty_id, day_idx)] = faculty_daily_hours.get((node.faculty_id, day_idx), 0) + node.duration_periods
                    division_daily_hours[(node.division_id, day_idx)] = division_daily_hours.get((node.division_id, day_idx), 0) + node.duration_periods
            else:
                unallocated.append(node)

        all_used_slots = set()
        for slist in allocations.values():
            all_used_slots.update(slist)

        runtime = (time.perf_counter() - start_time) * 1000.0

        return ColouringResult(
            algorithm="Welsh-Powell",
            assignments=primary_assignments,
            slot_allocations=allocations,
            unallocated=unallocated,
            chromatic_number=len(all_used_slots),
            runtime_ms=round(runtime, 2),
            iterations=iterations,
            metadata={"total_sessions": len(self.graph.nodes), "placed_sessions": len(primary_assignments)}
        )

    def solve_random_greedy(self, seed: Optional[int] = 42) -> ColouringResult:
        """
        Random Greedy Baseline:
        Random vertex permutation order with greedy color assignment.
        """
        start_time = time.perf_counter()
        allocations: Dict[str, List[int]] = {}
        primary_assignments: Dict[str, int] = {}
        unallocated: List[SessionNode] = []

        faculty_daily_hours: Dict[Tuple[str, int], int] = {}
        division_daily_hours: Dict[Tuple[str, int], int] = {}

        nodes = list(self.graph.nodes.values())
        rng = random.Random(seed)
        rng.shuffle(nodes)

        iterations = 0
        for node in nodes:
            iterations += 1
            assigned_slot = None
            for slot_candidate in range(self.max_slots):
                if self._is_slot_valid(node, slot_candidate, allocations, faculty_daily_hours, division_daily_hours):
                    assigned_slot = slot_candidate
                    break

            if assigned_slot is not None:
                slots_needed = [assigned_slot, assigned_slot + 1] if node.is_lab and node.duration_periods == 2 else [assigned_slot]
                allocations[node.id] = slots_needed
                primary_assignments[node.id] = assigned_slot

                s_obj = self.grid.get_slot(assigned_slot)
                if s_obj:
                    day_idx = s_obj.day_index
                    faculty_daily_hours[(node.faculty_id, day_idx)] = faculty_daily_hours.get((node.faculty_id, day_idx), 0) + node.duration_periods
                    division_daily_hours[(node.division_id, day_idx)] = division_daily_hours.get((node.division_id, day_idx), 0) + node.duration_periods
            else:
                unallocated.append(node)

        all_used_slots = set()
        for slist in allocations.values():
            all_used_slots.update(slist)

        runtime = (time.perf_counter() - start_time) * 1000.0

        return ColouringResult(
            algorithm="Random Greedy",
            assignments=primary_assignments,
            slot_allocations=allocations,
            unallocated=unallocated,
            chromatic_number=len(all_used_slots),
            runtime_ms=round(runtime, 2),
            iterations=iterations,
            metadata={"total_sessions": len(self.graph.nodes), "placed_sessions": len(primary_assignments)}
        )


def dsatur_colour(
    graph: ConflictGraph,
    grid: SlotGrid,
    faculty_map: Optional[Dict[str, Faculty]] = None,
    max_available_slots: Optional[int] = None,
    rooms: Optional[List[Any]] = None
) -> ColouringResult:
    """Helper that runs DSATUR graph colouring."""
    colorer = TimetableColorer(graph, grid, faculty_map, max_available_slots, rooms)
    return colorer.solve_dsatur()
