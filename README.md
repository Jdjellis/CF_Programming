# CF_Programming — a personal CrossFit coaching skill

A chat-first training assistant for a CrossFit competitor. You talk to it (in
Claude / CoWork); it turns your gym's weekly **class programming** plus your
personal **limiter-focused blocks** into a simple, tiered, load-calculated weekly
plan, adjusts mid-week when you're under-recovered, and keeps a minimal log of your
rep-maxes.

> **Core principle:** the model supplies *judgment*; code supplies *arithmetic*.
> The assistant reasons out *what* to do (push/cruise/skip, how to deconflict your
> work against class, how to autoregulate). A small deterministic calculator does
> all the load/plate math — the model never computes a weight in its head.

This repo **is** the skill: [`skills/crossfit-coach/`](skills/crossfit-coach/).

## How to use it

Open a chat with the `crossfit-coach` skill available and:

- **Plan the week** — paste this week's class programming and ask "what's my week?"
  You get what to push/cruise/skip, a day-by-day schedule with your focus work
  placed around class, and calculated loads for every strength piece.
- **Adjust mid-week** — "I'm beaten up from yesterday's squats, today's front
  squats will be rough" → it re-tiers the day / the rest of the week.
- **Log progress** — "front-squat triple at 122 today" → it records the set and
  tells you your estimated 1RM and how the block is trending.

## Layout

```
skills/crossfit-coach/
  SKILL.md                  # orchestration: how the assistant plans / adjusts / logs
  references/
    policy.md               # the judgment brain: tiers, autoregulation, deconfliction, menus
    athlete-profile.md      # the diagnostic (the limiters), goals, lift-ratio table
    availability.md         # the usual training week (the day spine)
    focus-blocks.md         # current personal blocks + which week each is in
    drills/                 # program & drill library (squat block, ring-MU, knee rehab)
    examples/               # canonical output formats (weekly plan, daily adjust)
  scripts/
    calc.py                 # deterministic %/rep-max/RPE -> kg -> plate loadout
    estimate_1rm.py         # estimate a 1RM from a performed set (xRM)
    log_xrm.py              # minimal rep-max training log (add / list)
    cfprog/                 # the vendored arithmetic core (pure stdlib, no install)
    data/                   # maxes fixture, plate inventory, the xRM log
    tests/                  # unit tests for the arithmetic (the part that must stay exact)
```

## The calculator (the one thing that must be code)

Three target forms, all resolved against the current 1RM (from the maxes fixture,
mirroring the source-of-truth Google Sheet):

```bash
python3 skills/crossfit-coach/scripts/calc.py front_squat --percent 85
python3 skills/crossfit-coach/scripts/calc.py clean --rep-max 3
python3 skills/crossfit-coach/scripts/calc.py strict_press --rpe 8 --reps 5
```

It outputs the working weight **and** the exact per-side plate loadout for the
configured inventory (20 kg bar + 25/20/15/10/5/2.5/1.25/0.5 kg plates), rounding to
the nearest *loadable* weight and reporting the delta. RPE maps to a rep-max via
reps-in-reserve, then to %1RM through the spec's rep-max table — one table shared by
the calculator and the 1RM estimator.

## Training log

```bash
python3 skills/crossfit-coach/scripts/log_xrm.py add --lift front_squat --weight 122 --reps 3
python3 skills/crossfit-coach/scripts/log_xrm.py list --lift front_squat
python3 skills/crossfit-coach/scripts/estimate_1rm.py --lift front_squat --weight 122 --reps 3
```

The log (`scripts/data/xrm_log.json`) tracks rep-maxes for the goal-driving lifts so
progress and estimated 1RMs are visible within a block. This is intentionally minimal
in v1; it can grow later.

## Tests

```bash
python3 -m pip install pytest
python3 -m pytest        # exercises the calculator, rep-max table, plate solver, estimator
```

## Background & design history

[`PROJECT_SPEC.md`](PROJECT_SPEC.md) holds the full athlete profile, the training
policy rationale, and the design history — including the earlier deterministic
weekly-generator implementation that this chat-first skill replaced (recoverable at
the `pre-chat-migration` git tag).
