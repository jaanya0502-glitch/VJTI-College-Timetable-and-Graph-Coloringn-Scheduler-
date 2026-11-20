"use strict";

const DAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"];
const PERIODS_PER_DAY = 6;

let collegeData = null;
let timetableData = null;
let generationData = null;

document.addEventListener("DOMContentLoaded", initialize);

async function initialize() {
  bindEvents();
  try {
    await refreshCollegeData();
    await generateTimetable();
  } catch (error) {
    showNotice(error.message, true);
    setClashStatus(null);
  }
}

function bindEvents() {
  document.querySelectorAll(".tab-button").forEach(button => {
    button.addEventListener("click", () => selectTab(button.dataset.tab));
  });
  document.getElementById("generate-button").addEventListener("click", generateTimetable);
  document.getElementById("grade-filter").addEventListener("change", updateTargetOptions);
  document.getElementById("view-mode").addEventListener("change", updateTargetOptions);
  document.getElementById("target-filter").addEventListener("change", renderTimetable);
  document.getElementById("export-csv").addEventListener("click", exportCSV);
  document.getElementById("export-html").addEventListener("click", exportHTML);
  document.getElementById("print-timetable").addEventListener("click", () => window.print());
  document.getElementById("upload-button").addEventListener("click", uploadData);
  document.getElementById("load-sample-button").addEventListener("click", loadSampleData);
  document.getElementById("export-data-button").addEventListener("click", exportCollegeJSON);
}

async function apiRequest(path, options = {}) {
  const response = await fetch(path, options);
  const data = await response.json();
  if (!response.ok) {
    throw new Error(data.error || `Request failed (${response.status})`);
  }
  return data;
}

async function refreshCollegeData() {
  const [data, summary] = await Promise.all([
    apiRequest("/api/sample"),
    apiRequest("/api/data")
  ]);
  collegeData = data;
  renderSummary(summary);
  updateTargetOptions();
}

async function generateTimetable() {
  const button = document.getElementById("generate-button");
  button.disabled = true;
  showNotice("Generating a timetable with DSATUR…");
  try {
    generationData = await apiRequest("/api/generate", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({})
    });
    timetableData = generationData.timetable;
    renderTimetable();
    renderGraphChecks();
    setClashStatus(generationData);
    await refreshFacultyHours();
    await refreshSummary();
    if (generationData.success) {
      showNotice("Timetable generated and independently checked.");
    } else {
      showNotice("Timetable generated with items requiring attention. Review Graph & Checks.", true);
    }
  } catch (error) {
    setClashStatus(null);
    showNotice(`Timetable generation failed: ${error.message}`, true);
  } finally {
    button.disabled = false;
  }
}

function selectTab(tabId) {
  document.querySelectorAll(".tab-button").forEach(button => {
    const active = button.dataset.tab === tabId;
    button.classList.toggle("active", active);
    button.setAttribute("aria-selected", String(active));
  });
  document.querySelectorAll(".tab-panel").forEach(panel => {
    const active = panel.id === tabId;
    panel.classList.toggle("active", active);
    panel.hidden = !active;
  });
  if (tabId === "faculty-tab") refreshFacultyHours().catch(error => showNotice(error.message, true));
}

function updateTargetOptions() {
  if (!collegeData) return;
  const grade = document.getElementById("grade-filter").value;
  const mode = document.getElementById("view-mode").value;
  const label = document.getElementById("target-label");
  const select = document.getElementById("target-filter");
  const previous = select.value;
  const options = [];

  if (mode === "division") {
    label.textContent = "Division";
    collegeData.divisions
      .filter(division => division.year_id === grade)
      .forEach(division => options.push([division.id, `${division.id} · ${division.name}`]));
  } else if (mode === "faculty") {
    label.textContent = "Faculty";
    collegeData.faculty.forEach(faculty => options.push([faculty.id, `${faculty.name} (${faculty.id})`]));
  } else {
    label.textContent = "Room";
    collegeData.rooms.forEach(room => options.push([room.id, `${room.name} (${room.id})`]));
  }

  select.replaceChildren();
  options.forEach(([value, text]) => {
    const option = document.createElement("option");
    option.value = value;
    option.textContent = text;
    select.append(option);
  });
  if (options.some(([value]) => value === previous)) select.value = previous;
  renderTimetable();
}

function getVisibleEntries() {
  if (!timetableData || !collegeData) return [];
  const grade = document.getElementById("grade-filter").value;
  const mode = document.getElementById("view-mode").value;
  const target = document.getElementById("target-filter").value;
  const divisions = new Map(collegeData.divisions.map(division => [division.id, division]));
  return timetableData.entries.filter(entry => {
    const division = divisions.get(entry.division_id);
    if (!division || division.year_id !== grade) return false;
    if (mode === "division") return entry.division_id === target;
    if (mode === "faculty") return entry.faculty_id === target;
    return entry.room_id === target;
  });
}

function renderTimetable() {
  const tbody = document.getElementById("timetable-body");
  if (!tbody) return;
  tbody.replaceChildren();
  const matrix = DAYS.map(() => Array.from({ length: PERIODS_PER_DAY }, () => []));
  const visibleEntries = getVisibleEntries();

  visibleEntries.forEach(entry => {
    (entry.slot_ids || [entry.slot_id]).forEach(slotId => {
      const dayIndex = Math.floor(slotId / PERIODS_PER_DAY);
      const periodIndex = slotId % PERIODS_PER_DAY;
      if (matrix[dayIndex] && matrix[dayIndex][periodIndex]) {
        matrix[dayIndex][periodIndex].push({ entry, continuation: slotId !== entry.slot_id });
      }
    });
  });

  DAYS.forEach((day, dayIndex) => {
    const row = document.createElement("tr");
    const dayCell = document.createElement("td");
    dayCell.textContent = day;
    row.append(dayCell);

    matrix[dayIndex].forEach((sessions, periodIndex) => {
      const cell = document.createElement("td");
      if (sessions.length === 0) {
        cell.className = "empty-cell";
        cell.textContent = "—";
      } else {
        sessions.forEach(({ entry, continuation }) => {
          cell.append(createSessionCard(entry, continuation));
        });
      }
      row.append(cell);

      if (periodIndex === 2) {
        const lunch = document.createElement("td");
        lunch.className = "lunch-cell";
        lunch.textContent = "LUNCH BREAK";
        lunch.setAttribute("aria-label", "Lunch break");
        row.append(lunch);
      }
    });
    tbody.append(row);
  });
}

function createSessionCard(entry, continuation) {
  const card = document.createElement("div");
  card.className = `session-card${entry.is_lab ? " lab" : ""}${continuation ? " continuation" : ""}`;
  if (continuation) {
    card.textContent = "LAB CONTINUES";
    return card;
  }

  const faculty = collegeData.faculty.find(member => member.id === entry.faculty_id);
  const subject = document.createElement("div");
  subject.className = "session-subject";
  subject.textContent = entry.subject_id;
  card.append(subject);

  const details = document.createElement("div");
  details.className = "session-detail";
  details.textContent = `${faculty ? faculty.name : entry.faculty_id} · ${entry.division_id}`;
  card.append(details);

  const tags = document.createElement("div");
  tags.className = "session-tags";
  if (entry.room_id) addTag(tags, entry.room_id);
  if (entry.batch_id) addTag(tags, entry.batch_id);
  if (entry.is_lab) addTag(tags, "2-PERIOD LAB");
  card.append(tags);
  return card;
}

function addTag(parent, text) {
  const tag = document.createElement("span");
  tag.className = "session-tag";
  tag.textContent = text;
  parent.append(tag);
}

async function refreshFacultyHours() {
  const data = await apiRequest("/api/faculty-hours");
  const tbody = document.getElementById("faculty-hours-body");
  tbody.replaceChildren();
  data.faculty.forEach(faculty => {
    const row = document.createElement("tr");
    const nameCell = document.createElement("td");
    const nameButton = document.createElement("button");
    nameButton.type = "button";
    nameButton.className = "faculty-link";
    nameButton.textContent = faculty.name;
    nameButton.addEventListener("click", () => openFacultyTimetable(faculty));
    nameCell.append(nameButton);

    const hoursCell = document.createElement("td");
    hoursCell.className = "hours-cell";
    const hours = document.createElement("div");
    hours.className = "hours-value";
    hours.innerHTML = `<span>${faculty.assigned_hours} hrs assigned</span><span>${faculty.weekly_cap} hrs cap</span>`;
    const track = document.createElement("div");
    track.className = "progress-track";
    const fill = document.createElement("div");
    fill.className = `progress-fill${faculty.over_cap ? " over" : ""}`;
    fill.style.width = `${Math.min(faculty.weekly_cap ? faculty.assigned_hours / faculty.weekly_cap * 100 : 0, 100)}%`;
    track.append(fill);
    hoursCell.append(hours, track);

    const theoryCell = document.createElement("td");
    theoryCell.textContent = `${faculty.theory_hours} hrs`;
    const labCell = document.createElement("td");
    labCell.textContent = `${faculty.lab_hours} hrs`;
    const gradesCell = document.createElement("td");
    gradesCell.textContent = faculty.grades_taught.length ? faculty.grades_taught.join(", ") : "—";
    const statusCell = document.createElement("td");
    const badge = document.createElement("span");
    badge.className = `check-status${faculty.over_cap ? " error" : ""}`;
    badge.textContent = faculty.over_cap ? "Over Cap" : "OK";
    statusCell.append(badge);
    row.append(nameCell, hoursCell, theoryCell, labCell, gradesCell, statusCell);
    tbody.append(row);
  });
}

function openFacultyTimetable(faculty) {
  const grade = faculty.grades_taught[0] || "FY";
  document.getElementById("grade-filter").value = grade;
  document.getElementById("view-mode").value = "faculty";
  updateTargetOptions();
  document.getElementById("target-filter").value = faculty.id;
  renderTimetable();
  selectTab("timetable-tab");
}

async function refreshSummary() {
  renderSummary(await apiRequest("/api/data"));
}

function renderSummary(summary) {
  document.getElementById("summary-grades").textContent = summary.total_grades;
  document.getElementById("summary-divisions").textContent = summary.divisions;
  document.getElementById("summary-faculty").textContent = summary.faculty;
  document.getElementById("summary-rooms").textContent = summary.rooms;
  document.getElementById("summary-sessions").textContent = summary.sessions;
}

function renderGraphChecks() {
  if (!generationData) return;
  const stats = generationData.stats;
  document.getElementById("metric-nodes").textContent = stats.total_sessions;
  document.getElementById("metric-edges").textContent = stats.total_conflicts;
  document.getElementById("metric-colours").textContent = stats.slots_used;
  document.getElementById("metric-algorithm").textContent = "DSATUR";

  const codes = generationData.validation.violations.map(violation => violation.code);
  const groups = [
    ["Faculty Clashes", ["FACULTY_DOUBLE_BOOKED", "FACULTY_UNAVAILABLE"]],
    ["Class/Batch Clashes", ["DIVISION_DOUBLE_BOOKED", "BATCH_DOUBLE_BOOKED", "BATCH_DIVISION_CLASH"]],
    ["Room Clashes", ["ROOM_DOUBLE_BOOKED", "ROOM_TYPE_MISMATCH", "ROOM_UNASSIGNED"]],
    ["Faculty Cap Violations", ["FACULTY_MAX_HOURS_EXCEEDED", "FACULTY_WEEKLY_CAP"]]
  ];
  const checklist = document.getElementById("checklist");
  checklist.replaceChildren();
  groups.forEach(([label, relevantCodes]) => {
    const count = codes.filter(code => relevantCodes.includes(code)).length;
    const row = document.createElement("li");
    const text = document.createElement("span");
    text.textContent = `${count} ${label}`;
    const status = document.createElement("span");
    status.className = `check-status${count ? " error" : ""}`;
    status.textContent = count ? "Review" : "OK";
    row.append(text, status);
    checklist.append(row);
  });
}

function setClashStatus(generation) {
  const badge = document.getElementById("clash-status");
  const errorCount = generation ? generation.validation.error_count : null;
  const unplaced = generation ? generation.stats.unplaced_count : null;
  const clean = errorCount === 0 && unplaced === 0;
  badge.classList.toggle("error", !clean);
  badge.textContent = clean ? "0 Clashes Verified" : generation ? `${errorCount} Issues Found` : "Timetable unavailable";
}

async function uploadData() {
  const input = document.getElementById("data-file");
  const file = input.files[0];
  if (!file) {
    showNotice("Choose one of the supported college data files first.", true);
    return;
  }
  try {
    const content = await file.text();
    const result = await apiRequest("/api/upload", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ filename: file.name, content })
    });
    generationData = result.generation;
    timetableData = generationData.timetable;
    await refreshCollegeData();
    renderTimetable();
    renderGraphChecks();
    setClashStatus(generationData);
    await refreshFacultyHours();
    showNotice(`${file.name} imported; the timetable has been regenerated.`);
  } catch (error) {
    showNotice(`Import failed: ${error.message}`, true);
  }
}

async function loadSampleData() {
  try {
    const result = await apiRequest("/api/sample/reload", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({})
    });
    generationData = result.generation;
    timetableData = generationData.timetable;
    await refreshCollegeData();
    renderTimetable();
    renderGraphChecks();
    setClashStatus(generationData);
    await refreshFacultyHours();
    showNotice("Sample college data loaded and timetable regenerated.");
  } catch (error) {
    showNotice(`Could not load sample data: ${error.message}`, true);
  }
}

async function exportCollegeJSON() {
  try {
    const data = await apiRequest("/api/export/college.json");
    downloadFile("college-data.json", JSON.stringify(data, null, 2), "application/json;charset=utf-8");
  } catch (error) {
    showNotice(`Could not export college data: ${error.message}`, true);
  }
}

function exportCSV() {
  const headings = ["Day", "Period", "Subject", "Teacher", "Room", "Division", "Batch", "Session Type"];
  const rows = getVisibleEntries().map(entry => {
    const period = entry.slot_id % PERIODS_PER_DAY;
    const day = DAYS[Math.floor(entry.slot_id / PERIODS_PER_DAY)];
    const faculty = collegeData.faculty.find(member => member.id === entry.faculty_id);
    return [day, `P${period + 1}`, entry.subject_id, faculty ? faculty.name : entry.faculty_id,
      entry.room_id || "", entry.division_id, entry.batch_id || "Whole division",
      entry.is_lab ? "2-period lab" : "Theory"];
  });
  const content = [headings, ...rows].map(row => row.map(csvEscape).join(",")).join("\r\n");
  downloadFile("timetable.csv", content, "text/csv;charset=utf-8");
}

function exportHTML() {
  const entries = getVisibleEntries();
  const rows = entries.map(entry => {
    const period = entry.slot_id % PERIODS_PER_DAY;
    const day = DAYS[Math.floor(entry.slot_id / PERIODS_PER_DAY)];
    const faculty = collegeData.faculty.find(member => member.id === entry.faculty_id);
    return `<tr><td>${escapeHTML(day)}</td><td>P${period + 1}</td><td>${escapeHTML(entry.subject_id)}</td><td>${escapeHTML(faculty ? faculty.name : entry.faculty_id)}</td><td>${escapeHTML(entry.room_id || "")}</td><td>${escapeHTML(entry.division_id)}</td><td>${escapeHTML(entry.batch_id || "Whole division")}</td><td>${entry.is_lab ? "2-period lab" : "Theory"}</td></tr>`;
  }).join("");
  const html = `<!doctype html><html lang="en"><meta charset="utf-8"><title>College Timetable</title><style>body{font:14px Arial,sans-serif;margin:32px;color:#172b4d}table{width:100%;border-collapse:collapse}th,td{padding:9px;border:1px solid #dce3eb;text-align:left}th{background:#f2f6fa}h1{font-size:24px}</style><h1>College Timetable · ${escapeHTML(document.getElementById("grade-filter").value)}</h1><table><thead><tr><th>Day</th><th>Period</th><th>Subject</th><th>Teacher</th><th>Room</th><th>Division</th><th>Batch</th><th>Session Type</th></tr></thead><tbody>${rows}</tbody></table></html>`;
  downloadFile("timetable.html", html, "text/html;charset=utf-8");
}

function csvEscape(value) {
  return `"${String(value).replaceAll('"', '""')}"`;
}

function escapeHTML(value) {
  return String(value).replace(/[&<>"']/g, character => ({
    "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;"
  })[character]);
}

function downloadFile(filename, content, type) {
  const url = URL.createObjectURL(new Blob([content], { type }));
  const link = document.createElement("a");
  link.href = url;
  link.download = filename;
  link.click();
  URL.revokeObjectURL(url);
}

function showNotice(message, isError = false) {
  const notice = document.getElementById("notice");
  notice.textContent = message;
  notice.classList.toggle("error", isError);
  notice.hidden = false;
}
