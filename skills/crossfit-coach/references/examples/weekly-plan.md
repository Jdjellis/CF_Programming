# Weekly plan — output format

The weekly plan ships as **two parts**: a short chat reply (push/cruise/skip + the
priority order) and a **generated HTML file** with the full week. Keep the chat
reply skimmable — the detail lives in the HTML.

The gym streams class programming as **Performance** or **Fitness** (the athlete does
**Performance**) and also publishes **Comp** extras; dedicated **Weightlifting** sits
alongside. Use those names — never "CrossFit".

## 1. Chat reply (keep it this short)

> **Week of 8–14 Jun** — Front Squat/Strict Press wk3/6 · Ring MU wk3/6. No readiness
> logged — adjust each morning.
>
> - **Push (PROTECT):** Wed/Sun front-squat top sets; strict-press volume.
> - **Cruise (Performance):** Mon WL+chipper · Tue WOD · Wed WL · Thu gym · Sat WL+Perf
> - **Flex:** Tue Comp extras · Thu Comp class · Ring MU
>
> Triage when squeezed: PROTECT top sets → Performance class → accessory → skill.
> 📄 Full week + loads: `weekly-plan.html`

## 2. Generate the HTML

The model produces a compact JSON spec, then renders it:

```bash
python3 skills/crossfit-coach/scripts/render_week.py plan.json -o weekly-plan.html
# or stream it:  python3 .../render_week.py - -o weekly-plan.html < plan.json
```

See **`weekly-plan.json`** (the input) and **`weekly-plan.html`** (the result) in
this folder for the canonical shapes.

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
    "mon": { "am": { "type": "WL" }, "pm": { "type": "Perf" } },
    "thu": { "pm": { "type": "WOD + Comp" } },
    "sat": { "am": { "type": "Perf + WL" } },
    "fri": { "am": { "type": "Rest" } }
  },
  "days": [
    { "day": "Mon", "date": "8 Jun",
      "streams": [
        { "label": "Weightlifting",
          "text": "(0 - 18 min)\nA. Back Squat: 6s x 2r x 87.5%\n...verbatim...",
          "loads": [
            { "lift": "Back Squat", "scheme": "6 x 2 @ 87.5%",
              "load": "144.5 kg (87.5% of 165) — /side 2×25+10+1.25+2×0.5" }
          ] },
        { "label": "Performance", "text": "B. For time:\n50 Deadlifts\n...verbatim..." }
      ] },
    { "day": "Fri", "date": "12 Jun", "rest_note": "REST DAY" }
  ]
}
```

- **`summary`** → the Week Summary grid (columns Mon–Sun, rows AM/PM). `type` is a
  stream label/abbreviation — `WL | Perf | Comp | Fitness | Rest`, or a combo like
  `"Performance + WL"`; the renderer colour-codes by keyword. Omit a slot for an empty
  cell. `effort` (`Low | Med | High`) is an **optional** sub-tag — add it if you want
  the effort shown, omit it otherwise.
- **`days[].streams[]`** → the per-day workouts, one block per stream. `label` is the
  stream heading (drives the colour accent). `text` is the verbatim programming;
  `loads` is the optional list of calculated weights shown underneath.
- A day with no `streams` (just a `rest_note`) renders as a rest day. An optional
  `note` on a day prints a small italic line under the heading (e.g. "gym programs
  this for Sat — done Sun this week").
