---
name: POLP (Jason's POLP Program)
status: active
workbook_file_id: 1hjiWJ5HDh--huMb31r1pXeySRun7pdar
lifts: back_squat, front_squat, bench_press, deadlift, press
---

# POLP

The gym runs POLP inside class time ("Bench Press — POLP programming"). The
athlete logs each session in the workbook; the workbook does all load math.

- Read the workbook with the Google Drive connector (`read_file_content` on
  `workbook_file_id`). One tab per lift; each tab is one table, one row per week.
- **Next session for a lift** = the first row whose `S1 reps` is blank. Use that
  row's `Sets × Reps`, `B1 kg`, `B2 kg`, `S1 kg`, `S2 kg`, `S3 kg` **verbatim**
  (the workbook rounds to 1 kg; never re-derive them with calc.py).
- **Last result** = the row above it: `Result` (PASS/FAIL), `Fails at this
  weight`, `Action`, `Notes`.
- Deadlift ramps (sets climb to the top set); the other lifts are sets across.
- A cycle ends with a deload row and a 1RM test row. After a test the athlete
  starts a fresh workbook copy: ask for the new file ID and update this file.

## Notes
- 2026-10-07 — Press wk1 note in workbook: "This was way too hard..."; Setup
  notes shoulder niggles on the press 1RM. Factor into any extra pressing.
