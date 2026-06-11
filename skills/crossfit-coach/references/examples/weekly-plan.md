# Weekly plan — output format

The weekly plan is produced in **two stages**: first **propose the week in chat** (the
AM/PM schedule + the prioritisation decisions) and get the athlete's confirmation;
**then** calculate loads and generate the HTML file. Don't compute loads or render the
file until the schedule is confirmed.

The gym streams class programming as **Performance** or **Fitness** (the athlete does
**Performance**) and also publishes **Comp** extras; dedicated **Weightlifting** sits
alongside. Use those names — never "CrossFit".

## 1. Propose the week in chat (then wait for confirmation)

Reply with the proposed schedule as a quick table — including the fitted individual
work — plus the prioritisation decisions, and ask before going further:

> **Week of 8–14 Jun** — Front Squat/Strict Press wk3/6 · Ring MU wk3/6.
>
> | | Mon | Tue | Wed | Thu | Fri | Sat | Sun |
> |---|---|---|---|---|---|---|---|
> | **AM** | WL · +Ring MU | — | WL · +Ring MU | +Strict Press | Rest | Perf+WL · +Ring MU | Rest |
> | **PM** | Perf | Perf · +Quad/knee | — | WOD+Comp | — | — | — |
>
> **Priority decisions**
> - Front-squat strength deferred to class (squats heavy Mon/Wed/Sat) → quad/knee on Tue instead.
> - Strict press kept independent (box under-supplies pressing) → Thu AM, clear of Tue's Push Press.
> - Ring MU Mon/Wed/Sat for frequency; first to flex if a day is squeezed.
>
> Want me to adjust anything, or shall I calculate loads and generate the schedule?

## 2. Generate the HTML (after confirmation)

Build the JSON spec and render it, naming the file `Gym Schedule - <Monday's date>`:

```bash
python3 skills/crossfit-coach/scripts/render_week.py plan.json -o "Gym Schedule - 2026-06-08.html"
# or stream it:  python3 .../render_week.py - -o "Gym Schedule - 2026-06-08.html" < plan.json
```

See **`weekly-plan.json`** (the input) and **`weekly-plan.html`** (the rendered result,
named `weekly-plan` here as the canonical example) in this folder for the shapes.

### Two hard rules for the spec

1. **Workout text is copied *verbatim* from the gym's programming.** Paste it into
   each stream's `text` exactly as written (line breaks and all) — don't paraphrase,
   summarise, or "tidy" it. The renderer reproduces it as-is.
2. **Every load comes from `calc.py`, pasted verbatim** into a `loads` entry — never a
   hand-typed kg. For weightlifting (any `%`-of-1RM prescription, including Push
   Press), the calculated working weights render underneath the workout.

### Spec shape (abbreviated)

```json
{
  "week_of": "8–14 Jun 2026",
  "source": "Claremont Competitors Programming — Week 8",
  "focus": ["Front Squat / Strict Press — wk 3/6", "..."],
  "summary": {
    "mon": { "am": { "type": "WL", "add": "Ring MU" }, "pm": { "type": "Perf" } },
    "thu": { "am": { "add": "Strict Press" }, "pm": { "type": "WOD + Comp" } },
    "sat": { "am": { "type": "Perf + WL", "add": "Ring MU" } },
    "fri": { "am": { "type": "Rest" } }
  },
  "decisions": [
    "Front-squat strength deferred to class (squats heavy Mon/Wed/Sat); quad/knee support on Tue instead.",
    "Strict press kept as the protected independent lift — Thu AM, clear of Tue's Push Press.",
    "Ring MU placed Mon/Wed/Sat for frequency; first to flex under time pressure."
  ],
  "days": [
    { "day": "Mon", "date": "8 Jun",
      "streams": [
        { "label": "Weightlifting",
          "text": "(0 - 18 min)\nA. Back Squat: 6s x 2r x 87.5%\n...verbatim...",
          "loads": [
            { "lift": "Back Squat", "scheme": "6 x 2 @ 87.5%",
              "load": "144.5 kg (87.5% of 165) — /side 2×25+10+1.25+2×0.5" }
          ] },
        { "label": "Performance", "text": "B. For time:\n50 Deadlifts\n...verbatim..." },
        { "label": "Ring MU", "accent": "lim",
          "text": "False-grip ring pull-ups: 4 x 4\n...the athlete's own work..." }
      ] },
    { "day": "Fri", "date": "12 Jun", "rest_note": "REST DAY" }
  ]
}
```

- **`summary`** → the Week Summary grid (columns Mon–Sun, rows AM/PM). `type` is the
  class stream — `WL | Perf | Comp | Fitness | WOD | Rest`, or a combo like
  `"Performance + WL"`; the renderer colour-codes by keyword. **`add`** is the fitted
  individual work for that slot (strict press, ring MU, quad/knee), shown as a distinct
  pink chip — a cell can have `type` and/or `add`. Omit a slot for an empty cell.
  `effort` (`Low | Med | High`) is an **optional** sub-tag.
- **`decisions`** → a list of the prioritisation choices you made fitting the personal
  work in (what was placed, deferred, or dropped, and why). Rendered as a highlighted
  callout under the grid. Echo the same points in the chat reply.
- **`days[].streams[]`** → the per-day workouts, one block per stream. `label` is the
  stream heading; `text` is the **verbatim** class programming with `loads` underneath.
  The athlete's own blocks set `"accent": "lim"` (colours them pink, tags them
  "individual") and carry the block's drills + any `loads`.
- A day with no `streams` (just a `rest_note`) renders as a rest day. An optional
  `note` on a day prints a small italic line under the heading.
