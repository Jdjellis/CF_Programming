# cfprog — CrossFit Programming & Autoregulation System

Personal training-support system for a CrossFit competitor. Turns the weekly box
programming + a personal focus block into a daily, readiness-adjusted,
load-calculated plan, and tracks progress against strength-ratio standards.

See [`PROJECT_SPEC.md`](PROJECT_SPEC.md) for the full, authoritative context
(athlete profile, training policy, data model, phased build plan).

> **Core principle:** the model supplies *judgment*; code supplies *arithmetic*.
> Never mix the two. All load/plate math is deterministic, unit-tested code —
> the model never does it at runtime (spec Section 8).

## Status — Phase 1 complete · Phase 2 generation complete

| Deliverable | State |
|---|---|
| Repo scaffold (`src/` layout, `pyproject.toml`, tests) | ✅ |
| `skills/programming-policy/SKILL.md` (versioned policy from spec §3) | ✅ |
| Deterministic load/plate calculator (%/rep-max/RPE → kg → plates) | ✅ |
| Maxes read behind an interface (Sheet source of truth, fixture-backed) | ✅ |
| Logging layer (`LogStore` → SQLite) + analytics core | ✅ |
| **Gym-availability layer** (general weekly schedule + week/day overrides) | ✅ |
| **Weekly generator** — consumes availability + class plan; tiering + deconfliction + loads + daily-adjust + Markdown | ✅ |

Still pending in Phase 2: Slack PDF ingestion (feeds the class plan) and the
Calendar / Slack DM output adapters. Phase 3 (analytics surface) not started.

## Layout

```
src/cfprog/
  models.py       # dataclasses: Plate, PlateInventory, Target, Loadout, ...
  targets.py      # %/rep-max/RPE -> fraction of 1RM (rep-max table from spec)
  plates.py       # deterministic plate solver (the priority deliverable)
  maxes.py        # MaxesProvider interface + fixture + Sheets stub
  calculator.py   # ties it together: lift + target + max -> weight + loadout
  availability.py # general weekly schedule + week/day overrides -> resolved week
  cli.py          # `cfprog-calc` demo / one-off lookups
  availcli.py     # `cfprog-avail` renders the resolved weekly availability
  logstore.py     # LogStore interface + SQLite store (sets, RPE, readiness)
  analytics.py    # estimated 1RM, tonnage, ratio-gap analysis
  classplan.py    # ClassPlanProvider interface + fixture (the week's class plan)
  focus.py        # focus-block config + current-focus (skill + strength emphasis)
  references.py   # parser for the references/ program & drill library
  generator.py    # weekly generator: tier + deconflict + load + daily-adjust
  render.py       # WeeklyPlan -> Markdown (renderer kept separate from generation)
  weekcli.py      # `cfprog-week` generate / render / daily-adjust
data/
  maxes.fixture.json        # mirrors the Sheet top section (stand-in until auth)
  plate_inventory.json      # confirmed bar + plate inventory
  availability.template.json          # your usual weekly schedule (general availability)
  availability.overrides.example.json # sample week-to-week / day-to-day overrides
  classplan.fixture.json    # the week's class plan (stand-in until Slack ingestion)
  focus_blocks.fixture.json # focus-block configuration
references/                 # program & drill library (squat block, rehab, ring-MU)
examples/                   # rendered weekly plan + daily-adjust output
skills/programming-policy/SKILL.md   # versioned training policy
tests/                   # unit tests for every piece of arithmetic + the generator
```

## Setup

```bash
pip install -e ".[dev]"
pytest -q
```

## Calculator

Three target forms, all resolved against the current 1RM (read from the Sheet
top section; fixture-backed until Sheets auth is wired):

- **`%1RM`** — e.g. front squat at 85%.
- **rep-max** — e.g. clean at a 3RM target (via the spec's rep-max→% table).
- **RPE + reps** — e.g. strict press at RPE 8 for 5. Mapped deterministically:
  `reps-in-reserve = 10 − RPE`, `effective_reps = reps + RIR`, then the rep-max
  table. So 5 @ RPE 8 → 7RM → 83%.

Output is the working weight **and** the exact plate loadout per side for the
configured inventory, rounding to the nearest *loadable* weight and reporting the
delta when an exact match isn't possible.

```bash
cfprog-calc --demo
cfprog-calc front_squat --percent 85
cfprog-calc clean --rep-max 3
cfprog-calc strict_press --rpe 8 --reps 5
```

## Gym availability

Your *usual* weekly schedule lives in `data/availability.template.json` — each
day offers one or more **options** (an ordered set of class slots), and options
carry context flags so the resolver picks the right one. Week-to-week and
day-to-day changes are layered on top as **overrides**; they never edit the
template.

```bash
cfprog-avail                                   # usual week
cfprog-avail --flags sessions_hard             # hard week → Monday AM+PM double
cfprog-avail --day-flags tuesday=pm            # train Tuesday evening instead
cfprog-avail --rest wednesday --unavailable thursday
cfprog-avail --choose saturday=sat-wl-only     # WL focus → drop the 7am CrossFit
cfprog-avail --overrides data/availability.overrides.example.json
```

The weekly generator (`cfprog-week`, below) consumes this resolved availability
as its day spine — availability says *which days/sessions*, the class plan says
*what's in them*.

**Context flags** (toggle per-week or per-day): `sessions_hard` (Mon AM+PM
double), `pm` (swap a morning day to its all-PM option), and `wl_priority` /
`needs_double` / `wl_heavy` (the three-way Saturday logic).

**Resolution is deterministic:** for a trainable day the chosen option is the
*most specific eligible* one — eligible = every `requires` flag active and no
`excludes` flag active; most specific = most `requires` satisfied (ties broken
by listed order). An explicit `--choose` wins outright; if nothing is eligible
the day resolves to `needs_choice` rather than guessing. Override precedence:
`unavailable` → `rest` → `choose` → `flags`. This layer is the
`available training days` input the weekly generator (Phase 2) consumes; it does
**no** load math and invents **no** stimulus.

### Configured equipment

20 kg bar; pairs of 25 / 20 / 15 / 10 / 5 / 2.5 / 1.25 kg + 0.5 kg micro plates,
effectively unlimited supply (see `data/plate_inventory.json`). The solver still
models per-denomination counts, so it generalises to a limited set and will
report when a weight isn't reachable.

## Weekly generator

Runs Sunday and turns the week's class plan + a personal focus block into a
tiered, deconflicted, load-calculated plan (spec §5a). It **applies** the policy
in `SKILL.md` — it does not re-improvise it — and it never does load arithmetic
itself (every weight comes from the calculator). The generator is **pure given
its inputs** and unit-tested: tiering, placement/deconfliction, and load
resolution are all deterministic rules.

The **day spine comes from the gym-availability layer** (`cfprog.availability`):
availability resolves *which days/sessions* you train (rest days, AM+PM doubles,
the Saturday CF+WL combo), and the class plan is joined on by date to supply
*what's in* each day. Pass `--no-availability` to build the spine from the class
plan alone.

```bash
cfprog-week                      # generate + print the week's Markdown plan
cfprog-week --flags sessions_hard  # base availability flags (e.g. a hard week)
cfprog-week --out plan.md        # also write it to a file
cfprog-week --adjust Thu amber   # re-emit one day for a morning's readiness
cfprog-week --adjust Mon red
```

What the Sunday deliverable gives you (see `examples/`):

1. **Push / cruise / skip** — every session tiered: **PUSH** (PROTECT
   front-squat / strict-press strength), **CRUISE** (class metcons — the relief
   valve), **SKILL** (the focus block; first to cut on a red day).
2. **A schedule** — day-by-day, focus-block work placed around class stimuli with
   interference resolved: no same-stimulus on consecutive days; strength before
   conditioning. Where the class already covers a PROTECT lift that week (e.g.
   heavy front squats), the heavy stimulus is **deferred to class** and the
   personal work becomes low-CNS **accessory** (quad / knee) appended to a
   non-clashing class day — no competing barbell front squat. A lift the class
   under-supplies (strict press) stays a protected session on the freshest day.
3. **Calculated loads** — working weight + per-side plate loadout for every
   strength prescription, via the calculator.

**Priority / triage** (SKILL.md v1.1): strength is priority #1 — under time or
energy pressure work is shed from the bottom up (skill → accessory → class →
protected strength).

**Current focus** (SKILL.md v1.2): each focus block carries a structured *current
focus* — a name + cues plus an optional `reference` into the `references/`
program/drill library (rendered as a one-click link). The generator pulls *this
week's* drills straight from the referenced program for the current program week
(a visible **wk X/Y** marker that auto-advances), so you refine a structured
program (e.g. a 12-week squat block) by editing the program, not by re-typing
drills each week. Link-only references (purchased PDFs) carry an explicit
`this_week` list instead; a plain-string emphasis still works. Loads are
unaffected — kilos still come from the calculator.

The class plan is supplied through a `ClassPlanProvider` (fixture / manual entry
in `data/classplan.fixture.json`) — the same interface pattern as `MaxesProvider`
— so Slack PDF ingestion drops in later without touching the generator. The
Markdown renderer is one of several swappable output adapters; the plan itself is
a structured object (`WeeklyPlan`), so Calendar / Slack DM adapters can be added
without changing generation.

**Daily-adjust** (callable each morning) takes a day's readiness and re-emits
that day adjusted, reusing the same calculator: AMBER keeps each piece's top set
and trims back-off volume; RED drops loaded PROTECT/CRUISE work to skill / active
recovery while SKILL work survives.

## Source of truth

Current 1RMs live in the **Google Sheet top section**
(ID `1Q1RlKE9LfTpUYSAqwFWnknJ_g9ftTal1P4eeMBnqY_A`) and are read through
`MaxesProvider`. Until Sheets auth is wired, `FixtureMaxesProvider` loads a local
fixture that mirrors the Sheet. Do **not** hardcode maxes elsewhere, and do
**not** touch the deprecated training blocks in the workbook.
