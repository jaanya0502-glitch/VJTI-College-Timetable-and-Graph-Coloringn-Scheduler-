"""
engine/workload.py
Workload analytics and Day x Period college utilization heatmap.
Part of Shraddha's deliverables.
"""

from typing import Dict, List, Set, Optional, Any, Tuple
from .models import Timetable, TimetableEntry, Faculty, Division, Year
from .slots import SlotGrid


def compute_workload_analytics(
    timetable: Timetable,
    grid: SlotGrid,
    faculty_list: List[Faculty],
    divisions: List[Division],
    years: List[Year]
) -> Dict[str, Any]:
    """
    Computes comprehensive workload statistics:
    1. Faculty workload (total hours, max/day, distribution).
    2. Year & Division workload (FY/SY/TY theory vs lab hours).
    3. Day x Period utilization heatmap.
    """
    fac_map = {f.id: f for f in faculty_list}
    div_map = {d.id: d for d in divisions}
    year_map = {y.id: y for y in years}

    # 1. Faculty Workload
    faculty_stats: Dict[str, Dict[str, Any]] = {}
    for f in faculty_list:
        faculty_stats[f.id] = {
            "name": f.name,
            "department": f.department,
            "designation": f.designation,
            "max_allowed_week": f.max_hours_per_week,
            "max_allowed_day": f.max_hours_per_day,
            "assigned_hours": 0,
            "daily_hours": [0 for _ in range(len(grid.days))],
            "free_days": 0
        }

    for e in timetable.entries:
        duration = len(e.slot_ids)
        if e.faculty_id in faculty_stats:
            faculty_stats[e.faculty_id]["assigned_hours"] += duration
            first_slot = grid.get_slot(e.slot_id)
            if first_slot:
                d = first_slot.day_index
                faculty_stats[e.faculty_id]["daily_hours"][d] += duration

    for f_id, data in faculty_stats.items():
        data["free_days"] = sum(1 for h in data["daily_hours"] if h == 0)
        data["peak_day_hours"] = max(data["daily_hours"], default=0)

    # 2. Division & Year Workload
    division_stats: Dict[str, Dict[str, Any]] = {}
    for d in divisions:
        division_stats[d.id] = {
            "name": d.name,
            "year_id": d.year_id,
            "theory_hours": 0,
            "lab_hours": 0,
            "total_hours": 0,
            "daily_hours": [0 for _ in range(len(grid.days))]
        }

    for e in timetable.entries:
        dur = len(e.slot_ids)
        if e.division_id in division_stats:
            d_stat = division_stats[e.division_id]
            if e.is_lab:
                d_stat["lab_hours"] += dur
            else:
                d_stat["theory_hours"] += dur
            d_stat["total_hours"] += dur

            first_slot = grid.get_slot(e.slot_id)
            if first_slot:
                d = first_slot.day_index
                d_stat["daily_hours"][d] += dur

    year_stats: Dict[str, Dict[str, int]] = {}
    for d_id, d_stat in division_stats.items():
        y_id = d_stat["year_id"]
        if y_id not in year_stats:
            year_stats[y_id] = {"theory_hours": 0, "lab_hours": 0, "total_hours": 0}
        year_stats[y_id]["theory_hours"] += d_stat["theory_hours"]
        year_stats[y_id]["lab_hours"] += d_stat["lab_hours"]
        year_stats[y_id]["total_hours"] += d_stat["total_hours"]

    # 3. Day x Period Utilization Heatmap
    heatmap_matrix = [[0 for _ in range(grid.periods_per_day)] for _ in range(len(grid.days))]
    total_divisions = max(len(divisions), 1)

    for e in timetable.entries:
        for sid in e.slot_ids:
            s_obj = grid.get_slot(sid)
            if s_obj:
                heatmap_matrix[s_obj.day_index][s_obj.period_index] += 1

    heatmap_data = []
    max_active = 0
    for d_idx, day_name in enumerate(grid.days):
        for p_idx in range(grid.periods_per_day):
            count = heatmap_matrix[d_idx][p_idx]
            max_active = max(max_active, count)
            # Utilization percentage based on division occupancy
            util_pct = min(round((count / total_divisions) * 100, 1), 100.0)
            heatmap_data.append({
                "day_index": d_idx,
                "day_name": day_name,
                "period_index": p_idx,
                "time_slot": f"{grid.period_times[p_idx][0]}-{grid.period_times[p_idx][1]}",
                "active_sessions": count,
                "utilization_pct": util_pct
            })

    return {
        "faculty_workload": faculty_stats,
        "division_workload": division_stats,
        "year_workload": year_stats,
        "heatmap": heatmap_data,
        "summary": {
            "total_placed_sessions": len(timetable.entries),
            "peak_concurrent_sessions": max_active,
            "average_faculty_workload": round(
                sum(f["assigned_hours"] for f in faculty_stats.values()) / max(len(faculty_stats), 1), 1
            )
        }
    }
