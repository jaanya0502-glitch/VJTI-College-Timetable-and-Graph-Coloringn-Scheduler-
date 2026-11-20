"""CSV and printable HTML export helpers for timetable results."""

import csv
import html
from typing import Dict, List
from engine.models import Timetable, TimetableEntry
from engine.slots import SlotGrid

def export_entries_to_csv(timetable: Timetable, filepath: str) -> None:
    """Exports timetable entries as a tabular CSV."""
    with open(filepath, mode="w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow([
            "Session ID", "Assignment ID", "Day", "Period", "Slot ID",
            "Division", "Batch", "Subject", "Faculty", "Room", "Is Lab"
        ])
        for e in sorted(timetable.entries, key=lambda x: (x.slot_id, x.division_id)):
            writer.writerow([
                e.session_id, e.assignment_id, e.day, e.period, e.slot_id,
                e.division_id, e.batch_id or "Whole Div", e.subject_id,
                e.faculty_id, e.room_id or "Unassigned", e.is_lab
            ])


def export_division_grid_csv(timetable: Timetable, grid: SlotGrid, division_id: str, filepath: str) -> None:
    """Exports a 2D Day x Period schedule for a specific division to CSV."""
    matrix = {day: ["" for _ in range(grid.periods_per_day)] for day in grid.days}
    
    for e in timetable.entries:
        if e.division_id == division_id:
            text = f"{e.subject_id} ({e.faculty_id})"
            if e.batch_id:
                text += f" [{e.batch_id}]"
            if e.room_id:
                text += f" @{e.room_id}"
            
            for s_id in e.slot_ids:
                s = grid.get_slot(s_id)
                if s:
                    if matrix[s.day_name][s.period_index]:
                        matrix[s.day_name][s.period_index] += " / " + text
                    else:
                        matrix[s.day_name][s.period_index] = text

    with open(filepath, mode="w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        header = ["Day"] + [f"P{i+1} ({t[0]}-{t[1]})" for i, t in enumerate(grid.period_times)]
        writer.writerow(header)
        for day in grid.days:
            writer.writerow([day] + matrix[day])


def export_to_html(timetable: Timetable, grid: SlotGrid, filepath: str, title: str = "College Timetable") -> str:
    """
    Exports full interactive and printable HTML timetable view grouped by division and faculty.
    """
    divisions = sorted(list(set(e.division_id for e in timetable.entries)))
    # Pre-build division maps: div -> day -> period -> list of entry descriptions
    div_tables = {}
    for div in divisions:
        grid_data = {day: [[] for _ in range(grid.periods_per_day)] for day in grid.days}
        for e in timetable.entries:
            if e.division_id == div:
                for s_id in e.slot_ids:
                    s = grid.get_slot(s_id)
                    if s:
                        batch_tag = f"<span class='badge batch'>{html.escape(e.batch_id)}</span>" if e.batch_id else ""
                        room_tag = f"<span class='badge room'>{html.escape(e.room_id)}</span>" if e.room_id else ""
                        lab_tag = "<span class='badge lab'>LAB</span>" if e.is_lab else ""
                        desc = f"<div class='session-box {'is-lab' if e.is_lab else ''}'><strong>{html.escape(e.subject_id)}</strong><br><small>{html.escape(e.faculty_id)}</small><br>{batch_tag} {room_tag} {lab_tag}</div>"
                        grid_data[s.day_name][s.period_index].append(desc)
        div_tables[div] = grid_data

    html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{html.escape(title)}</title>
<style>
  body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif; margin: 20px; background: #f8fafc; color: #1e293b; }}
  h1, h2, h3 {{ color: #0f172a; margin-bottom: 8px; }}
  .card {{ background: white; border-radius: 8px; padding: 20px; margin-bottom: 24px; box-shadow: 0 1px 3px rgba(0,0,0,0.1); }}
  table {{ width: 100%; border-collapse: collapse; margin-top: 12px; font-size: 13px; }}
  th, td {{ border: 1px solid #e2e8f0; padding: 8px; text-align: center; vertical-align: top; }}
  th {{ background: #f1f5f9; font-weight: 600; }}
  .lunch-header {{ background: #fef3c7; color: #92400e; font-weight: bold; width: 40px; }}
  .session-box {{ background: #eff6ff; border-left: 3px solid #3b82f6; padding: 6px; margin: 2px 0; border-radius: 4px; text-align: left; font-size: 12px; }}
  .session-box.is-lab {{ background: #f0fdf4; border-left: 3px solid #10b981; }}
  .badge {{ display: inline-block; padding: 2px 5px; font-size: 10px; border-radius: 3px; font-weight: 600; margin-top: 2px; }}
  .badge.batch {{ background: #e0e7ff; color: #3730a3; }}
  .badge.room {{ background: #fef3c7; color: #92400e; }}
  .badge.lab {{ background: #dcfce7; color: #166534; }}
  .meta-stats {{ display: flex; gap: 16px; margin-bottom: 16px; }}
  .stat-chip {{ background: #f1f5f9; padding: 8px 14px; border-radius: 6px; font-size: 13px; }}
  @media print {{ body {{ background: white; }} .card {{ box-shadow: none; page-break-after: always; }} }}
</style>
</head>
<body>
  <h1>{html.escape(title)}</h1>
  <div class="meta-stats">
    <div class="stat-chip"><strong>Total Scheduled Sessions:</strong> {len(timetable.entries)}</div>
    <div class="stat-chip"><strong>Unplaced Sessions:</strong> {len(timetable.unplaced_sessions)}</div>
  </div>
"""

    for div, grid_data in div_tables.items():
        html_content += f"""
  <div class="card">
    <h2>Division: {div}</h2>
    <table>
      <thead>
        <tr>
          <th>Day</th>
"""
        for i, (st, et) in enumerate(grid.period_times):
            html_content += f"<th>P{i+1}<br><small>{st}-{et}</small></th>"
            if i == grid.lunch_after_period:
                html_content += "<th class='lunch-header'>LUNCH</th>"
        html_content += "</tr></thead><tbody>"

        for day in grid.days:
            html_content += f"<tr><td><strong>{day}</strong></td>"
            for i in range(grid.periods_per_day):
                cell_content = "".join(grid_data[day][i]) or "<span style='color:#cbd5e1'>-</span>"
                html_content += f"<td>{cell_content}</td>"
                if i == grid.lunch_after_period:
                    html_content += "<td class='lunch-header'><small>Break</small></td>"
            html_content += "</tr>"

        html_content += """
      </tbody>
    </table>
  </div>
"""

    html_content += "</body></html>"

    with open(filepath, "w", encoding="utf-8") as f:
        f.write(html_content)

    return html_content
