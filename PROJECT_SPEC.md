# CrossFit Programming & Autoregulation System — Project Spec

> Personal training-support system for a CrossFit competitor. Ingests weekly box
> programming, deconflicts a personal focus block against it, autoregulates load
> by daily readiness, converts prescriptions to real kg + plate math, logs
> actuals, and tracks progress against strength standards.

---

## 1. Purpose

One sentence: **turn the weekly Claremont programming + my own focus block into a
daily, readiness-adjusted, load-calculated plan, and track progress against
strength-ratio standards over time.**

The value is in the *policy* (where to push vs cruise, how to deconflict, how to
autoregulate) plus *deterministic load math*. The model supplies judgment; code
supplies arithmetic. Never mix the two.

---

## 2. Athlete profile

### Current 1RMs (source of truth = the Sheet, top section)

| Lift | 1RM (kg) | Year |
|---|---|---|
| Deadlift | 240 | 2025 |
| Back Squat | 165 | 2025 |
| Front Squat | 135 | 2025 |
| Overhead Squat | 100 | 2020 |
| Bench Press | 120 | 2022 |
| Strict Press | 70 | 2022 |
| Push Press | 100 | 2025 |
| Push Jerk | 105 | 2022 |
| Split Jerk | 124 | 2025 |
| Clean | 124 | 2025 |
| Power Clean | 122 | 2025 |
| Snatch | 88 | 2025 |
| Power Snatch | 82.5 | 2025 |
| Clean & Jerk | 124 | 2025 |

### Goals

- Strength: Front Squat 160, Back Squat 200, Clean 140, C&J 130, Snatch 100,
  Strict Press 80, Push Press 110, Push Jerk 115, Power Clean 130, Power Snatch 90.
- Benchmarks: Isabel <3:00, DT <6:00, Amanda <7:00, Fran <3:00, Diane <4:00,
  Grace <2:00, plus unbroken ring muscle-ups.
- (Deadlift goal of 220 already exceeded at 240 — deprioritise pulling.)

### Diagnostic read (this is *why* the policy is shaped the way it is)

- **Front squat is the keystone limiter.** FS (135) is only ~82% of BS (165),
  under the 85–90% norm. Clean (124) is ~92% of FS — far too high; a healthy
  clean sits well below the front squat. The 140 clean needs an FS near 160.
- **Cleans are recovery-limited, not catch-height.** Power clean is ~98% of full
  clean *because the front-squat stand-up is the bottleneck*, not because of
  catching high. Fix = heavy + paused front squats, cleans from blocks / halting
  cleans to overload the stand-up. Do **not** program "drop under" drills.
- **Snatch is technique-limited (pull finish), not leg-limited.** 88 on a 165
  back squat is ~53% (norm 60–65%). The fault is finishing the 2nd/3rd pull
  before diving under. Fix = snatch pulls with a complete finish, tall/no-contact
  work, halting snatch deadlifts, high pulls, tempo/segment snatches. Not an
  overhead-stability problem.
- **Overhead pressing is the genuinely weak link.** Strict press 70 vs 80 goal;
  strict HSPU is a target. Box programming under-supplies strict pressing volume.
- **Huge posterior pull, lagging quads/front rack.** BS is only ~69% of DL.
  Highest-leverage strength work is quad- and front-rack-dominant.

---

## 3. Training policy (→ becomes the versioned SKILL.md)

> This section is the source content for `skills/programming-policy/SKILL.md`.
> Formalise it there with a version header and changelog. Everything below is the
> "brain" the weekly generator applies.

### 3.1 Priority tiers

- **PROTECT (push; schedule on best-readiness days, do before conditioning):**
  front-squat strength and strict-pressing strength. These move the goals; never
  let a class metcon cannibalise them.
- **CRUISE (autoregulate):** class metcons and box-recommended extras. This is
  the relief valve — scale intensity *here* on bad days, not on the protected
  work. Conditioning adapts fine with autoregulated load.
- **SKILL (do anyway; cheap):** the active focus block (e.g. ring muscle-ups) and
  HSPU technique. Neurologically low-cost → frequency wins. Survives low-readiness
  days; this is the "productive when smashed" option.
- **DELOAD:** planned down-week ~every 4th week; let banked amber/red days pull a
  deload earlier if fatigue accumulates.

### 3.2 Readiness autoregulation

Daily signal → session adjustment:

| Tier | Signal (wearable or 20-sec self-report) | Adjustment |
|---|---|---|
| GREEN | Slept well, low soreness, motivated | Push top sets + full back-off volume |
| AMBER | Mixed sleep / moderate soreness / stress | Hit top set, trim back-off volume |
| RED | Poor sleep / high soreness / illness-adjacent | Drop to skill work or active recovery |

Treat any wearable "recovery score" as **one input**, validated against how
warm-ups actually feel. Do not let a red score veto a session the body is fine
with, or vice versa.

### 3.3 Interference / deconfliction rules

- Don't stack same-stimulus on consecutive days, and don't double-load the same
  pattern the class already taxes (e.g. heavy class cleans + personal heavy FS
  same day → move or drop the personal FS).
- Sequence strength before conditioning when both fall on one day.
- Tag every class session by primary stimulus: `heavy_squat | heavy_pull |
  press | gymnastics | engine | mixed`. Deconfliction operates on these tags.

### 3.4 Focus blocks

- Run **one or two** concurrent focuses outside class. Skill + strength don't
  interfere (different systems), so a skill block can run alongside a strength
  emphasis.
- Default block shape: e.g. **6-week ring-MU block, 3×/week** (skill tier) +
  **front-squat/strict-press strength emphasis** (protect tier).
- A block has: name, length (weeks), days/week, tier, and a session template the
  generator slots around the class plan.

### 3.5 Weakness-specific exercise logic

- **Clean stand-up:** heavy FS, paused FS, block cleans, halting cleans.
- **Snatch pull finish:** snatch pulls (full finish), tall/no-contact snatch,
  halting snatch DL, snatch high pulls, tempo/segment snatch.
- **Overhead press / strict HSPU:** dedicated strict-press volume, strict HSPU
  progressions.
- **Ring MU (skill):** transitions, false-grip work, kip swing on rings,
  eccentrics — frequency over load.

---

## 4. Data model & sources

| Source | Role | Notes |
|---|---|---|
| **Google Sheet (top section)** | **Source of truth** for maxes + standards | PRs, %-of-1RM table, rep-max→% table, lift-ratio standards. Sheet ID: `1Q1RlKE9LfTpUYSAqwFWnknJ_g9ftTal1P4eeMBnqY_A` |
| **Slack PDF** | **Sole weekly programming input** | Posted Sunday night to the Claremont channel `GKAQQ7PGE` (workspace `crossfitclaremont`). Class WODs + recommended extras. |
| **Log (new Sheet tab or store)** | Logged actuals + RPE | Write here; do **not** touch the old training blocks (deprecated). |
| **Wearable (optional)** | Readiness + sleep feed | Future. Structured feed in lieu of self-report. |

### Reference tables (mirror the Sheet; Sheet stays live source)

**Rep-max → %1RM:** 1RM 100 · 2RM 95 · 3RM 93 · 4RM 90 · 5RM 87 · 6RM 85 ·
7RM 83 · 8RM 80 · 9RM 77 · 10RM 75

**Lift-ratio standards (for gap analysis):**

| Lift | of Lift | Target % |
|---|---|---|
| Snatch | Back Squat | 60–65 |
| Clean & Jerk | Back Squat | 80–85 |
| Clean & Jerk | Front Squat | 85–90 |
| Snatch | Clean & Jerk | 80–85 |
| Front Squat | Back Squat | 85–93 |
| Power Snatch | Snatch | 80–85 |
| Power Clean | Clean | 80–90 |
| Clean | Deadlift | 70–75 |
| Strict Press | Push Press | 70–75 |
| Push Press | Jerk | 75–85 |
| Overhead Squat | Back Squat | 65–70 |

---

## 5. Weekly flow (the build target)

```
Sunday night
  └─ Slack PDF drops
       └─ INGESTION: parse class WODs + extras, tag each by stimulus
            └─ DECONFLICTION: place focus-block work, flag interference
                 └─ daily READINESS input adjusts load/volume (green/amber/red)
                      └─ LOAD CALC: %/RPE → kg → plate math (from current maxes)
                           └─ OUTPUT: weekly plan + daily adjustments
                                └─ LOG actuals + RPE
                                     └─ WRITEBACK to Sheet → ANALYTICS update
```

---

## 6. System architecture

- **Claude Code = home base.** Builds and owns the durable assets and scheduled
  jobs.
- **CoWork = weekly runtime.** The judgment loop ("here's how I'm feeling, adjust
  the week") with Drive/Calendar connectors, no code. Shares the same Sheet +
  SKILL.md.

### Components

| Component | Home | Notes |
|---|---|---|
| `skills/programming-policy/SKILL.md` | Code | Versioned policy (Section 3). |
| Load/plate calculator | Code | **Deterministic. Never LLM arithmetic.** Unit-tested. |
| Slack ingestion | Code | Pull latest PDF from channel; parse + tag. |
| Sheets read/write | Code | Read maxes/standards; write log. |
| Weekly generator | Code + policy | Applies SKILL.md to ingested plan. |
| Analytics suite | Code | Reads Sheet; thin viz layer (Streamlit or React). |
| Scheduled job | Code | Cron / GitHub Action, fires Sunday night. |

---

## 7. Build sequence (phased)

**Phase 1 — foundation (useful day one, no external deps):**
1. Repo scaffold.
2. `skills/programming-policy/SKILL.md` from Section 3.
3. Deterministic **load/plate calculator**: %/RPE/rep-max → kg → exact plate
   loadout per side, from current maxes. Unit-tested against known cases.

**Phase 2 — ingestion + generation:**
4. Slack PDF ingestion + stimulus tagging.
5. Weekly generator: deconfliction + readiness adjustment + load prescriptions.
6. Output format (doc / calendar / Slack DM — TBD).

**Phase 3 — analytics + writeback:**
7. Log writeback to Sheet.
8. Analytics: PR trend lines, estimated 1RM from logged sets, automated
   ratio-gap analysis vs standards, tonnage/volume, readiness-vs-performance
   correlation (once wearable feeds it).

---

## 8. Non-negotiables

- **Plate math is deterministic code, unit-tested. The model never does
  arithmetic.** This is the single most important constraint.
- **Sheet top section is the single source of truth for maxes** — read it, never
  duplicate or hardcode maxes elsewhere.
- **Policy lives in the versioned SKILL.md** — the generator applies it; it isn't
  re-improvised per run.
- **Do not write to the deprecated training blocks** in the Sheet; create a fresh
  log target.

---

## 9. Open inputs (fill before building the dependent parts)

- [ ] **Plate inventory + bar weight** — required for the calculator's plate
  rounding. (e.g. bar 20 kg; pairs of 25/20/15/10/5/2.5/1.25 — confirm what you
  own and any micro/fractional plates.)
- [ ] **Slack access method** — connector vs bot token. Channel is known:
  `GKAQQ7PGE` (workspace `crossfitclaremont`,
  https://crossfitclaremont.slack.com/archives/GKAQQ7PGE).
- [ ] **Log write target** — new Sheet tab name, or separate store.
- [ ] **Output channel** — doc, Google Calendar events, or Slack DM.
- [ ] **Wearable** — device + API, or stay on self-report (optional/future).

---

## 10. Tech suggestions (non-binding)

Python for calculator + ingestion + Sheets I/O (Google Sheets API). PDF parsing
via `pdfplumber`/`pymupdf`. Dashboard: Streamlit (fast) or a React app reading
the Sheet. Schedule via cron or a GitHub Action.
