# Weekly plan — output format

The weekly plan ships as **two parts**: a short chat reply (push/cruise/skip + the
priority order) and a **generated HTML file** with the full week. Keep the chat
reply skimmable — the detail lives in the HTML.

## 1. Chat reply (keep it this short)

> **Week of 8 Jun** — Front Squat/Strict Press wk3/6 · Ring MU wk3/6. No readiness
> logged — future days planned GREEN, adjust each morning.
>
> - **Push (PROTECT):** Thu — Strict Press strength _(box under-supplies pressing)_
> - **Cruise (class):** Mon WL · Tue engine · Wed WL · Thu gym · Sat WL
> - **Flex (skill/support):** Ring MU Mon/Wed/Sat · quad-knee Tue
> - **This week:** FS strength paused — class covers heavy squat (Mon/Wed/Sat), so
>   Tue gets low-CNS quad/knee support, no competing barbell FS.
>
> Triage when squeezed: PROTECT top sets → class → accessory → skill.
> 📄 Full week + loads: `weekly-plan.html`

## 2. Generate the HTML

The model produces a compact JSON spec (judgment + the calculator's load lines
pasted verbatim — **never** hand-typed kg), then renders it:

```bash
python3 skills/crossfit-coach/scripts/render_week.py plan.json -o weekly-plan.html
# or stream it:  python3 .../render_week.py - -o weekly-plan.html < plan.json
```

See **`weekly-plan.json`** (the input) and **`weekly-plan.html`** (the result) in
this folder for the canonical shapes.

### Spec shape (abbreviated)

```json
{
  "week_of": "2026-06-08",
  "source": "Claremont Competitors Programming — Week 8",
  "focus": ["Front Squat / Strict Press — wk 3/6 · PROTECT", "..."],
  "summary": {
    "mon": { "pm": { "type": "Weightlifting", "effort": "High" } },
    "tue": { "am": { "type": "CrossFit", "effort": "Med" },
             "pm": { "type": "Limiter", "effort": "Low" } },
    "fri": { "am": { "type": "Rest" } }
  },
  "days": [
    { "day": "Mon", "date": "2026-06-08", "class": "heavy_squat",
      "sessions": [
        { "tier": "CRUISE", "title": "Weightlifting + Performance",
          "items": [
            { "name": "Back Squat", "scheme": "6×2 @ 87.5%",
              "load": "144.5 kg (88% of 165) — /side 2×25+10+1.25+2×0.5" }
          ] } ] },
    { "day": "Fri", "date": "2026-06-12", "rest_note": "REST — open gym if wanted" }
  ]
}
```

- **`summary`** → the Week Summary grid (columns Mon–Sun, rows AM/PM). `type` is one
  of `CrossFit | Weightlifting | Comp | Limiter | Rest`; `effort` is `Low | Med |
  High`. Omit a slot for an empty cell; omit `effort` on a Rest cell.
- **`days[].sessions[]`** → the per-day workouts. `tier` is `PROTECT | CRUISE |
  ACCESSORY | SKILL` (drives the colour accent). Each item carries a `scheme` and a
  pre-calculated `load` line (from `calc.py`), or a free-text `detail` for metcons.
- A day with no `sessions` (just a `rest_note`) renders as a rest day.

Loads are deterministic — every kg in a `load` string comes from `scripts/calc.py`,
pasted verbatim. The renderer does no math; it only lays the plan out.
