# College timetable data schema

The scheduler accepts a complete JSON college snapshot or separate CSV files for faculty assignments and rooms. IDs referenced by assignments must exist in the uploaded JSON dataset.

## JSON snapshot

The root object contains `years`, `divisions`, `batches`, `subjects`, `faculty`, `rooms`, and `assignments` arrays.

- A year uses `id`, `name`, and `semester`; supported sample grades are FY, SY, TY, and LY.
- A division uses `id`, `name`, `year_id`, and `student_count`.
- A batch uses `id`, `name`, `division_id`, and `student_count`.
- A subject uses `id`, `code`, `name`, `year_id`, `is_lab`, `weekly_hours`, and `credits`.
- Faculty records include `id`, `name`, `department`, `designation`, `max_hours_per_day`, `max_hours_per_week`, and optional `unavailable_slots`.
- Rooms include `id`, `name`, `room_type`, `capacity`, and optional `building` and `floor`.
- Assignments include `id`, `subject_id`, `faculty_id`, `division_id`, `batch_id`, `weekly_hours`, `is_lab`, `room_type_required`, and `student_count`.

## CSV files

`faculty_loads.csv` contains one row per assignment with these headers:

```csv
assignment_id,subject_id,faculty_id,division_id,batch_id,weekly_hours,is_lab,room_type,student_count,faculty_weekly_cap
```

Batch IDs are blank for a whole-division lecture. A lab assignment should normally have `weekly_hours=2`, `is_lab=true`, and a batch ID. Faculty caps are repeated per faculty assignment so a load-sheet upload can update weekly limits.

`rooms.csv` uses:

```csv
room_id,name,room_type,capacity,building,floor
```

Supported room types are `CLASSROOM`, `SEMINAR_HALL`, `COMPUTER_LAB`, and `ELECTRONICS_LAB`.

## Scheduling rules

The week has Monday–Friday and six one-hour periods per day. Lunch follows Period 3. Two-period labs must occupy consecutive periods without crossing lunch or the day boundary. The validator checks faculty availability and weekly/daily caps, division and batch clashes, and room assignment, capacity, type, and double booking.
