"""HTTP API and local web app for the college timetable scheduler."""

import csv
import importlib
import importlib.util
import json
import os
import sys
from dataclasses import replace
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from io import StringIO
from typing import Any, Dict, Optional
from urllib.parse import urlparse

PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
DATA_PATH = os.path.join(PROJECT_ROOT, "data", "sample_college.json")
UI_DIR = os.path.join(PROJECT_ROOT, "ui")
IO_PACKAGE = "_college_io"

if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)


def _load_io_package():
    if IO_PACKAGE not in sys.modules:
        package_path = os.path.join(PROJECT_ROOT, "io")
        spec = importlib.util.spec_from_file_location(
            IO_PACKAGE,
            os.path.join(package_path, "__init__.py"),
            submodule_search_locations=[package_path],
        )
        if spec is None or spec.loader is None:
            raise ImportError("Unable to load the project's CSV and JSON utilities")
        package = importlib.util.module_from_spec(spec)
        sys.modules[IO_PACKAGE] = package
        spec.loader.exec_module(package)
    return importlib.import_module(IO_PACKAGE)


_io = _load_io_package()
deserialize_college_data = _io.deserialize_college_data
serialize_college_data = _io.serialize_college_data
serialize_timetable = _io.serialize_timetable
deserialize_timetable = _io.deserialize_timetable
load_json = _io.load_json
save_json = _io.save_json
load_assignments_from_csv = _io.load_assignments_from_csv
load_rooms_from_csv = _io.load_rooms_from_csv
export_entries_to_csv = _io.export_entries_to_csv
export_to_html = _io.export_to_html

from engine.colouring import TimetableColorer
from engine.graph import ConflictGraph
from engine.models import Timetable, TimetableEntry
from engine.precheck import FeasibilityChecker
from engine.rooms import RoomAllocator
from engine.sessions import expand_assignments_to_sessions
from engine.slots import SlotGrid
from engine.validator import IndependentValidator
from engine.workload import compute_workload_analytics


class TimetableAPIService:
    """Load college data, generate a DSATUR timetable, and report checks."""

    def __init__(self, data_path: str = DATA_PATH):
        self.data_path = data_path
        self.current_timetable: Optional[Timetable] = None
        self.last_generation: Optional[Dict[str, Any]] = None
        self.reload_data()

    def reload_data(self) -> None:
        self.set_college_data(load_json(self.data_path))

    def set_college_data(self, data: Dict[str, Any]) -> None:
        if not isinstance(data, dict):
            raise ValueError("College data must be a JSON object")
        (
            self.years,
            self.divisions,
            self.batches,
            self.subjects,
            self.faculty,
            self.rooms,
            self.assignments,
        ) = deserialize_college_data(data)
        self.raw_data = serialize_college_data(
            self.years,
            self.divisions,
            self.batches,
            self.subjects,
            self.faculty,
            self.rooms,
            self.assignments,
        )
        self._refresh_services()
        self.current_timetable = None
        self.last_generation = None

    def _refresh_services(self) -> None:
        self.grid = SlotGrid()
        self.faculty_map = {member.id: member for member in self.faculty}
        self.division_map = {division.id: division for division in self.divisions}
        self.validator = IndependentValidator(self.grid, self.rooms, self.faculty)
        self.room_allocator = RoomAllocator(self.rooms)
        self.checker = FeasibilityChecker(self.grid, self.rooms, self.faculty)

    def generate(self, options: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        sessions = expand_assignments_to_sessions(self.assignments)
        graph = ConflictGraph(sessions)
        result = TimetableColorer(
            graph=graph,
            grid=self.grid,
            faculty_map=self.faculty_map,
            max_available_slots=self.grid.total_slots,
            rooms=self.rooms,
        ).solve_dsatur()

        room_assignments, unassigned_rooms = self.room_allocator.assign_rooms_for_timetable(
            result.slot_allocations, graph.nodes
        )
        entries = []
        for session_id, start_slot in result.assignments.items():
            node = graph.nodes[session_id]
            slot = self.grid.get_slot(start_slot)
            entries.append(TimetableEntry(
                assignment_id=node.assignment_id,
                session_id=node.id,
                slot_id=start_slot,
                slot_ids=result.slot_allocations[session_id],
                day=slot.day_name if slot else "Unknown",
                period=slot.period_index if slot else 0,
                faculty_id=node.faculty_id,
                division_id=node.division_id,
                subject_id=node.subject_id,
                batch_id=node.batch_id,
                room_id=room_assignments.get(session_id),
                is_lab=node.is_lab,
            ))

        timetable = Timetable(
            entries=entries,
            unplaced_sessions=result.unallocated,
            metadata={
                "algorithm": "DSATUR",
                "runtime_ms": result.runtime_ms,
                "iterations": result.iterations,
                "colours_used": result.chromatic_number,
            },
        )
        validation = self.validator.validate(timetable)
        graph_data = graph.to_visualization_dict()
        response = {
            "success": validation.is_valid and not result.unallocated,
            "validation": validation.to_dict(),
            "timetable": serialize_timetable(timetable),
            "graph_visualization": graph_data,
            "stats": {
                "algorithm": "DSATUR",
                "runtime_ms": result.runtime_ms,
                "total_sessions": len(sessions),
                "total_conflicts": graph.num_edges(),
                "slots_used": result.chromatic_number,
                "total_placed": len(entries),
                "unplaced_count": len(result.unallocated),
                "unassigned_rooms": unassigned_rooms,
            },
        }
        self.current_timetable = timetable
        self.last_generation = response
        return response

    def get_faculty_hours(self) -> Dict[str, Any]:
        timetable = self.current_timetable
        if timetable is None:
            timetable = deserialize_timetable(self.generate()["timetable"])
        stats = {
            member.id: {
                "id": member.id,
                "name": member.name,
                "weekly_cap": member.max_hours_per_week,
                "assigned_hours": 0,
                "theory_hours": 0,
                "lab_hours": 0,
                "grades_taught": set(),
            }
            for member in self.faculty
        }
        for entry in timetable.entries:
            faculty_stats = stats.get(entry.faculty_id)
            if not faculty_stats:
                continue
            hours = len(entry.slot_ids)
            faculty_stats["assigned_hours"] += hours
            faculty_stats["lab_hours" if entry.is_lab else "theory_hours"] += hours
            division = self.division_map.get(entry.division_id)
            if division:
                faculty_stats["grades_taught"].add(division.year_id)
        return {
            "faculty": [
                {
                    **member,
                    "grades_taught": sorted(member["grades_taught"]),
                    "over_cap": member["assigned_hours"] > member["weekly_cap"],
                }
                for member in stats.values()
            ]
        }

    def get_data_summary(self) -> Dict[str, int]:
        return {
            "total_grades": len({year.id for year in self.years}),
            "divisions": len(self.divisions),
            "faculty": len(self.faculty),
            "rooms": len(self.rooms),
            "sessions": len(expand_assignments_to_sessions(self.assignments)),
        }

    def get_workload(self) -> Dict[str, Any]:
        timetable = self.current_timetable
        if timetable is None:
            timetable = deserialize_timetable(self.generate()["timetable"])
        return compute_workload_analytics(
            timetable=timetable,
            grid=self.grid,
            faculty_list=self.faculty,
            divisions=self.divisions,
            years=self.years,
        )

    def validate_schedule(self, timetable_data: Dict[str, Any]) -> Dict[str, Any]:
        return self.validator.validate(deserialize_timetable(timetable_data)).to_dict()

    def upload(self, filename: str, content: str) -> Dict[str, Any]:
        if filename.lower().endswith(".json"):
            self.set_college_data(json.loads(content))
        elif filename.lower() == "faculty_loads.csv":
            assignments = load_assignments_from_csv(StringIO(content))
            if not assignments:
                raise ValueError("The faculty load CSV contains no assignments")
            cap_by_faculty = {}
            for row in csv.DictReader(StringIO(content)):
                cap = row.get("faculty_weekly_cap", "").strip()
                if cap:
                    cap_by_faculty[row["faculty_id"].strip()] = int(cap)
            self.assignments = assignments
            self.faculty = [
                replace(member, max_hours_per_week=cap_by_faculty[member.id])
                if member.id in cap_by_faculty else member
                for member in self.faculty
            ]
            self._update_raw_data()
            self._refresh_services()
            self.current_timetable = None
        elif filename.lower() == "rooms.csv":
            rooms = load_rooms_from_csv(StringIO(content))
            if not rooms:
                raise ValueError("The rooms CSV contains no rooms")
            self.rooms = rooms
            self._update_raw_data()
            self._refresh_services()
            self.current_timetable = None
        else:
            raise ValueError("Upload sample_college.json, faculty_loads.csv, or rooms.csv")
        return {"summary": self.get_data_summary(), "generation": self.generate()}

    def _update_raw_data(self) -> None:
        self.raw_data = serialize_college_data(
            self.years,
            self.divisions,
            self.batches,
            self.subjects,
            self.faculty,
            self.rooms,
            self.assignments,
        )


SERVICE = TimetableAPIService()


class TimetableRequestHandler(BaseHTTPRequestHandler):
    def _send_json(self, status: int, data: Any) -> None:
        payload = json.dumps(data).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def _serve_file(self, filename: str, content_type: str) -> None:
        filepath = os.path.join(UI_DIR, filename)
        try:
            with open(filepath, "rb") as file:
                content = file.read()
        except FileNotFoundError:
            self.send_error(404, "File Not Found")
            return
        self.send_response(200)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(content)))
        self.end_headers()
        self.wfile.write(content)

    def _read_json(self) -> Dict[str, Any]:
        length = int(self.headers.get("Content-Length", "0"))
        raw_body = self.rfile.read(length).decode("utf-8")
        data = json.loads(raw_body or "{}")
        if not isinstance(data, dict):
            raise ValueError("Request body must be a JSON object")
        return data

    def do_GET(self) -> None:
        path = urlparse(self.path).path
        if path in ("/", "/index.html"):
            self._serve_file("index.html", "text/html; charset=utf-8")
        elif path == "/app.js":
            self._serve_file("app.js", "application/javascript; charset=utf-8")
        elif path == "/styles.css":
            self._serve_file("styles.css", "text/css; charset=utf-8")
        elif path == "/health":
            self._send_json(200, {"status": "ok", "service": "College Timetable Scheduler"})
        elif path == "/api/sample":
            self._send_json(200, SERVICE.raw_data)
        elif path == "/api/export/college.json":
            self._send_json(200, SERVICE.raw_data)
        elif path == "/api/data":
            self._send_json(200, SERVICE.get_data_summary())
        elif path == "/api/faculty-hours":
            self._send_json(200, SERVICE.get_faculty_hours())
        elif path == "/api/workload":
            self._send_json(200, SERVICE.get_workload())
        elif path == "/api/graph":
            generation = SERVICE.last_generation or SERVICE.generate()
            self._send_json(200, {
                "stats": generation["stats"],
                "graph_visualization": generation["graph_visualization"],
                "validation": generation["validation"],
            })
        else:
            self.send_error(404, f"Endpoint not found: {path}")

    def do_POST(self) -> None:
        path = urlparse(self.path).path
        try:
            request_data = self._read_json()
        except (json.JSONDecodeError, UnicodeDecodeError, ValueError) as error:
            self._send_json(400, {"error": str(error)})
            return
        try:
            if path == "/api/generate":
                self._send_json(200, SERVICE.generate(request_data))
            elif path == "/api/validate":
                self._send_json(200, SERVICE.validate_schedule(request_data.get("timetable", {})))
            elif path == "/api/upload":
                filename = request_data.get("filename")
                content = request_data.get("content")
                if not isinstance(filename, str) or not isinstance(content, str):
                    raise ValueError("Upload requires a filename and text content")
                self._send_json(200, SERVICE.upload(filename, content))
            elif path == "/api/sample/reload":
                SERVICE.reload_data()
                self._send_json(200, {
                    "summary": SERVICE.get_data_summary(),
                    "generation": SERVICE.generate(),
                })
            else:
                self.send_error(404, f"Endpoint not found: {path}")
        except (ValueError, KeyError, TypeError, json.JSONDecodeError) as error:
            self._send_json(400, {"error": str(error)})
        except Exception as error:
            self._send_json(500, {"error": str(error)})

    def log_message(self, format: str, *args: Any) -> None:
        """Keep local server logs concise while retaining request visibility."""
        super().log_message(format, *args)


def run_server(port: int = 8000) -> None:
    server = ThreadingHTTPServer(("", port), TimetableRequestHandler)
    print(f"College Timetable Scheduler running at http://localhost:{port}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down server.")
    finally:
        server.server_close()


if __name__ == "__main__":
    run_server(int(sys.argv[1]) if len(sys.argv) > 1 else 8000)
