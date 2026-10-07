# References — program & drill library

These Markdown files are the **source of truth for a focus block's drills**. A
focus block in `../focus-blocks.md` points at one of these by path and states the
week it's in; the assistant reads *this week's* drills straight from here, so you
refine the program by editing the program — not by hand-typing drills each week.

See `../policy.md` §4–§5 for how this fits the policy.

## Format

Plain Markdown, parsed with no external dependencies. Two shapes:

### Periodised program (week-by-week)

```markdown
# Squat 12-week block

> Optional summary / how loads resolve.

## Week 1
Cue: One-line focus for the week.
- Back squat — 5x5 @ 70%
- Paused front squat (3s) — 3x3 @ 70%

## Week 2
...
```

- A `## Week N` heading defines week `N`. The highest week number is the program
  length (the `wk X/Y` marker).
- A `Cue:` line (optionally `> Cue:`) sets that week's cue.
- `- ` / `* ` bullets are the week's drills.
- The assistant reads the week stated for the block in `../focus-blocks.md` (bump
  it as the weeks pass, or infer it from the date / training log).

### Flat drill menu (non-periodised — rehab, mobility)

```markdown
# Knee / tendon rehab

## Drills
- Spanish squat (banded) — 3x20–30s holds
- ATG split squat — 3x8/leg
```

- Any non-`Week` heading's bullets form a single menu used every week.
- Flat-menu focuses carry **no** week marker.

## Loads

Where a drill names a lift + a percentage, the actual kilos are **not** written
here — the assistant resolves them through the deterministic calculator
(`../../scripts/calc.py`). Drill text here is descriptive.

## PDFs / purchased programs

A program may live in a non-Markdown file (e.g. a purchased PDF) the assistant
can't read. In that case, paste the relevant week's drills into chat (or summarise
them in a Markdown file here) so the assistant can list them.
