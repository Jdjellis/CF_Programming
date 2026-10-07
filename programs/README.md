# programs/

One file per personal program the coach tracks, named `<start-date>-<name>.md`
(the athlete's own start date, e.g. `2026-10-13-rowing-12wk.md`), so repeat
blocks never collide. Finished programs stay here with `status: done`.
`polp.md` is the exception: the POLP workbook tracks its own position.

The coach reads these as plain markdown (no parser) and commits every change
straight to `main`.

## Format

```markdown
---
name: Rowing 12-wk
status: active            # active | done
started: 2026-10-13       # the athlete's own start, not the channel's
source: Endurance channel PDF, Sep 2026 (original in the Project Library)
current: W1 S1            # the next session to do
sessions_per_week: 2
---

## Sessions

### W1 S1
<session text, verbatim from the source>

### W1 S2
...

## Log
- 2026-10-19 — W1 S1, S2 done. "Felt easy." → current: W2 S1
```

- `current` always names the **next** session to do.
- `## Log` is append-only: one line per check-in or mid-week report.
- A program the coach designs (e.g. a pressing block) uses the same format;
  `source:` says "Designed with the coach, <date>" and loads are written as
  calc.py targets (`--percent`, `--rep-max`, `--rpe`), never as kg.
