# College Timetable Scheduler

A timetable generator for a four-year engineering college (FY, SY, TY, LY). It models scheduling as a **graph colouring** problem, assigns time slots with the **DSATUR** heuristic, allocates rooms, and then verifies the result with an **independent validator**. A small web interface lets you generate, inspect, upload data for, and export timetables.

The project is written in pure Python 3 and uses **only the standard library**. There is nothing to install.

---

## Features

- **Clash-free scheduling** for faculty, divisions, batches and rooms.
- **Theory lectures and two-period batch labs.** Labs occupy consecutive periods on the same day and never cross the lunch break.
- **Faculty constraints:** unavailable slots, daily hour limits and weekly hour caps.
- **Room allocation** by room type and capacity, using best-fit assignment.
- **Independent validation** of every generated timetable, with named violation codes and readable messages.
- **Feasibility pre-check** that reports a lower bound on the number of slots required.
- **Workload analytics:** faculty hours, free days, theory vs lab hours, and a Day x Period heatmap.
- **Web UI** with timetable views, faculty hours, graph and validation checks, and data upload.
- **Import and export:** CSV and JSON upload; CSV, HTML and print export.

---

## Quick start

Requirements: Python 3.9 or newer.

```bash
python3 api.py 8000
```

Open <http://localhost:8000> in a browser. The sample college loads automatically and a timetable is generated on start-up.

---

## How it works

The scheduler runs as a pipeline. Each stage has its own module.

```
college data  ->  feasibility check  ->  sessions  ->  conflict graph
                                                            |
        validation  <-  room allocation  <-  DSATUR colouring
```

1. **Load data.** Years, divisions, batches, subjects, faculty, rooms and assignments are read from JSON (or CSV).
2. **Pre-check.** Faculty load, availability, room demand and a chromatic lower bound are examined before solving.
3. **Expand into sessions.** Each assignment becomes atomic sessions: a 4-hour theory subject becomes four one-hour sessions, and a 2-hour lab becomes one two-period block.
4. **Build the conflict graph.** Each session is a vertex. An edge joins two sessions that cannot run at the same time.
5. **Colour the graph.** Time slots are the colours. DSATUR repeatedly picks the most constrained session and gives it the earliest slot that satisfies every hard rule.
6. **Allocate rooms.** Sessions are assigned to the smallest free room of the correct type and capacity.
7. **Validate.** A separate checker re-derives every rule from the finished timetable and reports any violation.

### Conflict edges

| Edge type | Meaning |
|---|---|
| Faculty | The same teacher appears in both sessions |
| Division | The same division has two whole-class sessions |
| Batch / division | A batch is in lab while its whole division is in a lecture |
| Batch / batch | The same batch has two sessions |

Different batches of one division do not conflict with each other, because their labs run in parallel.

### Hard constraints enforced by the solver

- No two conflicting sessions share a slot.
- Labs start only at valid positions and occupy two consecutive periods.
- A faculty member is never scheduled in an unavailable slot or beyond their daily limit.
- A division has at most six periods per day.
- Room supply is never exceeded in any slot.

If no valid slot exists for a session, it is reported as **unplaced**. It is never forced into a clash.

### Time grid

Monday to Friday, six one-hour periods per day (30 slots), with lunch after the third period.

---

## Project structure

```
.
├── api.py                  HTTP server and request handling
├── data/
│   ├── sample_college.json     Complete sample dataset
│   ├── faculty_loads.csv       Sample assignments
│   ├── rooms.csv               Sample rooms
│   └── sample_timetable.html   Sample exported timetable
├── docs/
│   └── schema.md           Data schema
├── engine/
│   ├── models.py           Dataclasses and enums
│   ├── slots.py            Day x Period grid and lab rules
│   ├── sessions.py         Assignment -> session expansion
│   ├── graph.py            Conflict graph and lower bound
│   ├── precheck.py         Feasibility pre-check
│   ├── colouring.py        DSATUR colouring solver
│   ├── rooms.py            Best-fit room allocation
│   ├── validator.py        Independent timetable validator
│   └── workload.py         Workload analytics
├── io/
│   ├── json_store.py       Save and load the college as JSON
│   ├── loaders.py          CSV importers
│   └── exporters.py        CSV and HTML exporters
├── tests/                  Unit tests (unittest)
└── ui/                     Web interface (HTML, CSS, JavaScript)
```

---

## Using the web interface

| Tab | What it does |
|---|---|
| **Timetable** | Generate a timetable and view it by division, faculty or room. Export as CSV or HTML, or print. |
| **Faculty Hours** | Weekly hours per faculty member against their caps, with overloaded faculty flagged. |
| **Graph & Checks** | Explanation of the colouring approach, solver statistics and validation results. |
| **Upload / Data** | View dataset counts, upload CSV or JSON, reload the sample, or download the college as JSON. |

CSV uploads replace the corresponding assignments or rooms. JSON uploads replace the whole in-memory dataset. Every upload regenerates the timetable immediately. The sample dataset can be restored at any time.

---

## Data files

- `data/sample_college.json` is the complete dataset. See `docs/schema.md` for field definitions.
- `data/faculty_loads.csv` has one row per theory or batch-lab assignment:

  ```
  assignment_id, subject_id, faculty_id, division_id, batch_id,
  weekly_hours, is_lab, room_type, student_count, faculty_weekly_cap
  ```

  Include `faculty_weekly_cap` to update a faculty member's weekly cap on import.

- `data/rooms.csv` lists rooms:

  ```
  room_id, name, room_type, capacity, building, floor
  ```

  Room types: `CLASSROOM`, `SEMINAR_HALL`, `COMPUTER_LAB`, `ELECTRONICS_LAB`.

The bundled sample covers 4 years, 4 divisions, 12 batches, 23 subjects, 18 faculty and 10 rooms.

---

## API

| Method | Endpoint | Description |
|---|---|---|
| GET | `/health` | Health check |
| GET | `/api/sample` | Sample dataset |
| GET | `/api/data` | Current dataset summary |
| GET | `/api/export/college.json` | Download the current dataset |
| GET | `/api/faculty-hours` | Weekly hours per faculty member |
| GET | `/api/workload` | Workload analytics and heatmap |
| GET | `/api/graph` | Conflict graph and metrics |
| POST | `/api/generate` | Generate and validate a timetable |
| POST | `/api/upload` | Upload data: `{ "filename": "...", "content": "..." }` |
| POST | `/api/sample/reload` | Restore the sample dataset |
| POST | `/api/validate` | Validate a supplied timetable object |

---

## Results on the sample data

| Metric | Value |
|---|---|
| Sessions | 69 |
| Conflict edges | 781 |
| Slots used (of 30) | 23 |
| Unplaced sessions | 0 |
| Validation violations | 0 |
| Solve time | under 10 ms |

---

## Testing

```bash
python3 tests/run_tests.py
```

This uses only `unittest` and needs no extra packages. If you have `pytest` installed, `pytest -v` also works.

---

## Design notes and limitations

- DSATUR is a **heuristic**. Minimum graph colouring is NP-hard, so the result is valid and fast but not guaranteed to use the fewest possible slots.
- Placement is **greedy with no backtracking**. A session that cannot be placed is reported rather than causing earlier placements to be rearranged.
- Room allocation is **greedy best-fit** and is likewise not guaranteed to find a room for every session when a perfect arrangement exists.
- The validator re-checks clashes, lab shape, faculty availability and hour limits, and room double-booking from the finished timetable. Room capacity is enforced during allocation rather than in the validator.
- The built-in HTTP server is intended for local use and demonstration, not production deployment.