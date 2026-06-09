---
name: programming-policy
description: >
  Personal CrossFit programming + autoregulation policy. The "brain" the weekly
  generator applies to turn box programming + a personal focus block into a
  daily, readiness-adjusted, load-calculated plan. Apply this policy when
  placing focus-block work against the class plan, deconflicting stimuli,
  autoregulating load by daily readiness, or choosing weakness-specific
  accessory work. Does NOT do load arithmetic — that is the deterministic
  calculator's job (the model never does plate/percentage math at runtime).
version: 1.0.0
status: active
source_of_truth: PROJECT_SPEC.md (Section 3); maxes from Google Sheet top section
last_updated: 2026-06-09
---

# Programming & Autoregulation Policy

> This is the versioned policy the weekly generator applies. It is judgment, not
> arithmetic: it decides *what* to program and *how hard*, then hands concrete
> loads to the deterministic load/plate calculator. Never re-improvise this
> policy per run, and never let the model compute weights — read the calculator's
> output.

## 0. Athlete context (why this policy is shaped this way)

The diagnostic read driving every rule below:

- **Front squat is the keystone limiter.** FS is only ~82% of back squat (norm
  85–90%) and the clean sits at ~92% of FS (far too high). The clean goal needs
  an FS near 160.
- **Cleans are recovery-limited, not catch-height.** The stand-up out of the
  front rack is the bottleneck (power clean ~98% of full clean). Fix with heavy
  and paused front squats, block cleans, halting cleans. **Do not program
  "drop under" / fast-elbow catch drills** — they don't address the limiter.
- **Snatch is technique-limited (pull finish), not leg-limited.** Snatch is ~53%
  of back squat (norm 60–65%); the fault is finishing the 2nd/3rd pull before
  diving under. Fix with pull-finish work, not overhead-stability work.
- **Overhead pressing is the genuine weak link.** Strict press 70 vs 80 goal;
  strict HSPU is a target. Box programming under-supplies strict pressing.
- **Huge posterior pull, lagging quads/front rack.** Back squat is only ~69% of
  deadlift; deadlift goal already exceeded. Highest-leverage work is quad- and
  front-rack-dominant. **Deprioritise pulling/deadlift volume.**

## 1. Priority tiers

Every piece of programmed work is assigned exactly one tier. Tiers determine
scheduling order and how autoregulation touches them.

| Tier | What goes here | Scheduling rule |
|---|---|---|
| **PROTECT** | Front-squat strength; strict-pressing strength. These move the goals. | Push. Schedule on best-readiness days, **before** conditioning. Never let a class metcon cannibalise protected work. |
| **CRUISE** | Class metcons; box-recommended extras. | The relief valve — autoregulate intensity *here* on bad days, not on protected work. Conditioning adapts fine with autoregulated load. |
| **SKILL** | Active focus block (e.g. ring muscle-ups); HSPU technique. | Do anyway; neurologically cheap → frequency wins. Survives low-readiness days ("productive when smashed"). |
| **DELOAD** | Planned down-week. | ~Every 4th week. Banked amber/red days can pull a deload earlier if fatigue accumulates. |

Rule of thumb: **on a bad day you scale CRUISE, you keep PROTECT's top set (or
move it), and you still do SKILL.**

## 2. Readiness autoregulation

Daily signal (wearable score and/or a 20-second self-report) → session
adjustment:

| Tier | Signal | Adjustment |
|---|---|---|
| **GREEN** | Slept well, low soreness, motivated | Push top sets + full back-off volume |
| **AMBER** | Mixed sleep / moderate soreness / stress | Hit the top set, trim back-off volume |
| **RED** | Poor sleep / high soreness / illness-adjacent | Drop to SKILL work or active recovery |

- Treat any wearable "recovery score" as **one input**, validated against how the
  warm-up actually feels. A red score does **not** veto a session the body is
  fine with, and a green score does not force a session the body clearly isn't.
- Resolve conflicts in favour of the warm-up read; note the override in the log.

How readiness maps to load is handed to the deterministic calculator as a target
(%1RM, rep-max, or RPE+reps) — the policy chooses the target, the calculator
chooses the kilos and plates.

## 3. Interference / deconfliction rules

- **Tag every class session by primary stimulus:**
  `heavy_squat | heavy_pull | press | gymnastics | engine | mixed`.
  Deconfliction operates on these tags.
- **Don't stack same-stimulus on consecutive days.**
- **Don't double-load a pattern the class already taxes.** E.g. heavy class
  cleans + personal heavy front squats the same day → move or drop the personal
  FS (it's PROTECT — prefer to *move* it to a better day, not delete it).
- **Sequence strength before conditioning** when both fall on one day.

Deconfliction decision order when placing focus-block work:
1. Is today's class stimulus the same pattern as the planned PROTECT work?
   → move PROTECT to a non-conflicting day.
2. Was yesterday the same stimulus? → don't repeat; shift or swap.
3. Otherwise place PROTECT first, then SKILL, then the class CRUISE work.

## 4. Focus blocks

- Run **one or two** concurrent focuses outside class. Skill + strength don't
  interfere (different systems), so a skill block can run alongside a strength
  emphasis.
- **Default block shape:** a 6-week ring-MU block, 3×/week (SKILL tier) **+** a
  front-squat / strict-press strength emphasis (PROTECT tier).
- A block is defined by: `name`, `length_weeks`, `days_per_week`, `tier`, and a
  `session_template` the generator slots around the class plan.

## 5. Weakness-specific exercise logic

Pick accessory work from these menus to attack the diagnosed limiter. (Loads
come from the calculator; this menu chooses the movement.)

| Limiter | Programme | Avoid |
|---|---|---|
| **Clean stand-up** (recovery-limited) | Heavy FS, paused FS, block cleans, halting cleans | "Drop under" / fast-elbow catch drills |
| **Snatch pull finish** (technique-limited) | Snatch pulls (full finish), tall / no-contact snatch, halting snatch deadlift, snatch high pulls, tempo / segment snatch | Treating it as an overhead-stability problem |
| **Overhead press / strict HSPU** | Dedicated strict-press volume, strict HSPU progressions | Letting box programming dictate press volume (it under-supplies it) |
| **Ring MU** (skill) | Transitions, false-grip work, kip swing on rings, eccentrics — frequency over load | Loading it heavy; chase frequency instead |

## 6. Hard constraints (inherited from spec Section 8)

- **Plate / percentage math is deterministic, unit-tested code. This policy
  never does arithmetic** — it emits a target; the calculator emits kilos + plates.
- **The Google Sheet top section is the single source of truth for maxes**
  (Sheet ID `1Q1RlKE9LfTpUYSAqwFWnknJ_g9ftTal1P4eeMBnqY_A`). Never hardcode or
  duplicate maxes in the policy.
- **Never write to the deprecated training blocks** in the Sheet; logging goes to
  a fresh target.

---

## Changelog

### 1.0.0 — 2026-06-09
- Initial policy, authored from PROJECT_SPEC.md Section 3 (priority tiers,
  readiness autoregulation, deconfliction, focus blocks, weakness-specific
  exercise logic) plus the Section 0 diagnostic context and Section 8 hard
  constraints. Phase 1.

<!--
Changelog conventions: bump version (semver) on any policy change.
  MAJOR — a rule reverses or a tier's meaning changes.
  MINOR — a rule/menu is added or materially expanded.
  PATCH — clarifications, wording, typo fixes.
Record the rationale, not just the diff.
-->
