# References — program & drill library

These Markdown files are the **source of truth for a focus block's drills**. A
focus block's *current focus* (`emphasis` in `data/focus_blocks.fixture.json`)
points at one of these by path; the weekly generator pulls *this week's* drills
straight from here, so you refine the program by editing the program — not by
hand-typing drills into the config each week.

See `skills/programming-policy/SKILL.md` §5 for how this fits the policy, and
`src/cfprog/references.py` for the parser.

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

- A `## Week N` heading defines week `N`. The program length is the highest week
  number, which drives the `wk X/Y` progress marker.
- A `Cue:` line (optionally `> Cue:`) sets that week's cue.
- `- ` / `* ` bullets are the week's drills.
- The generator reads the week given by the focus's `program_week` (or, if
  unset, the block's `current_week`) — so the focus **auto-advances** each week.

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

Where a drill names a lift + a percentage, the actual kilos are **not** computed
here — they resolve through the deterministic `LoadCalculator` via the focus
template's `strength` pieces (spec §8). Drill text here is descriptive.

## PDFs / purchased programs

A reference may be a non-Markdown file (e.g. a purchased PDF). Those are
**link-only** — the parser can't read them, so the focus must carry an explicit
`this_week` drill list in config; the renderer still links the file.
