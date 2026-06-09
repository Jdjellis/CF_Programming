# cfprog — CrossFit Programming & Autoregulation System

Personal training-support system for a CrossFit competitor. Turns the weekly box
programming + a personal focus block into a daily, readiness-adjusted,
load-calculated plan, and tracks progress against strength-ratio standards.

See [`PROJECT_SPEC.md`](PROJECT_SPEC.md) for the full, authoritative context
(athlete profile, training policy, data model, phased build plan).

> **Core principle:** the model supplies *judgment*; code supplies *arithmetic*.
> Never mix the two. All load/plate math is deterministic, unit-tested code —
> the model never does it at runtime (spec Section 8).

## Status — Phase 1 complete

| Deliverable | State |
|---|---|
| Repo scaffold (`src/` layout, `pyproject.toml`, tests) | ✅ |
| `skills/programming-policy/SKILL.md` (versioned policy from spec §3) | ✅ |
| Deterministic load/plate calculator (%/rep-max/RPE → kg → plates) | ✅ |
| Maxes read behind an interface (Sheet source of truth, fixture-backed) | ✅ |

Phases 2 (Slack ingestion + weekly generator) and 3 (analytics + writeback)
are **not** started.

## Layout

```
src/cfprog/
  models.py       # dataclasses: Plate, PlateInventory, Target, Loadout, ...
  targets.py      # %/rep-max/RPE -> fraction of 1RM (rep-max table from spec)
  plates.py       # deterministic plate solver (the priority deliverable)
  maxes.py        # MaxesProvider interface + fixture + Sheets stub
  calculator.py   # ties it together: lift + target + max -> weight + loadout
  cli.py          # `cfprog-calc` demo / one-off lookups
data/
  maxes.fixture.json     # mirrors the Sheet top section (stand-in until auth)
  plate_inventory.json   # confirmed bar + plate inventory
skills/programming-policy/SKILL.md   # versioned training policy
tests/                   # unit tests for every piece of arithmetic
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

### Configured equipment

20 kg bar; pairs of 25 / 20 / 15 / 10 / 5 / 2.5 / 1.25 kg + 0.5 kg micro plates,
effectively unlimited supply (see `data/plate_inventory.json`). The solver still
models per-denomination counts, so it generalises to a limited set and will
report when a weight isn't reachable.

## Source of truth

Current 1RMs live in the **Google Sheet top section**
(ID `1Q1RlKE9LfTpUYSAqwFWnknJ_g9ftTal1P4eeMBnqY_A`) and are read through
`MaxesProvider`. Until Sheets auth is wired, `FixtureMaxesProvider` loads a local
fixture that mirrors the Sheet. Do **not** hardcode maxes elsewhere, and do
**not** touch the deprecated training blocks in the workbook.
