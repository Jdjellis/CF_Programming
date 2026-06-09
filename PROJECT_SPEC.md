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
>
> **Policy evolves in SKILL.md (versioned), not here.** Refinements since this
> section was written live in the SKILL.md changelog. Current: **v1.1** —
> (a) strength is priority #1 over skill, with an explicit triage order
> (PROTECT → CRUISE → ACCESSORY → SKILL); (b) where the class already covers a
> PROTECT lift that week (e.g. heavy front squats), defer the heavy stimulus to
> class and substitute low-CNS supporting **accessory** work (quad / knee) on a
> non-clashing class day rather than duplicating the lift. See SKILL.md §1, §3, §5.

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
| **Google Sheet (top section)** | **Read-only snapshot of current XRMs** (source of truth for *maxes*) | PRs, %-of-1RM table, rep-max→% table, lift-ratio standards. Read via `MaxesProvider`. Sheet ID: `1Q1RlKE9LfTpUYSAqwFWnknJ_g9ftTal1P4eeMBnqY_A`. **Not** the analytics database — see below. |
| **SQLite store** (`data/cfprog.db`) | **Database for all recorded lifts, RPE, and readiness** | The thing analytics queries. Sits behind the `LogStore` interface (swappable for Postgres/hosted later). The Sheet stays a snapshot; logged actuals live here, never written back to the deprecated Sheet blocks. |
| **Slack PDF** | **Sole weekly programming input** | Posted Sunday night to the Claremont channel `GKAQQ7PGE` (workspace `crossfitclaremont`). Class WODs + recommended extras. Until Slack is wired, the class plan is supplied through a `ClassPlanProvider` interface (fixture/manual entry), mirroring how maxes are stubbed. |
| **Wearable (optional)** | Readiness + sleep feed | Future. Structured feed in lieu of self-report; lands in the readiness table of the SQLite store. |

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
  └─ Slack PDF drops  (until wired: class plan via ClassPlanProvider fixture)
       └─ INGESTION: parse class WODs + extras, tag each by stimulus
            └─ WEEKLY GENERATOR (applies SKILL.md):
                 ├─ TIER each session: PUSH (protect) / CRUISE / SKILL-or-SKIP
                 ├─ DECONFLICT: place focus-block work, flag interference
                 └─ LOAD CALC: %/RPE → kg → plate math (from current maxes)
                      └─ OUTPUT: the Sunday weekly plan (schedule + tiers + loads)
                           └─ daily READINESS (from log) adjusts each session
                                └─ LOG actuals + RPE → SQLite → ANALYTICS update
```

---

## 5a. Weekly generator — contract (Phase 2 build target)

The generator runs **Sunday** and produces a plan for the week ahead. It is the
glue between the policy (`SKILL.md`), the log (readiness + history), the maxes
(Sheet), and the deterministic calculator. **It applies the policy; it does not
re-improvise it, and it never does load arithmetic itself** — loads come from
the calculator.

### The Sunday deliverable must tell me three things

1. **What to push, cruise, or skip** — every session tagged with its tier:
   - **PUSH** = PROTECT work (front-squat / strict-press strength). Do it, on the
     best-readiness day, before conditioning.
   - **CRUISE** = class metcons / extras. Autoregulate intensity here.
   - **SKILL / SKIP-ELIGIBLE** = focus-block skill work; do it if able, first to
     go on a red day.
2. **A schedule for the week** — a day-by-day plan (which sessions, in what
   order), with focus-block work placed and interference flagged/resolved per the
   deconfliction rules.
3. **Calculated loads for each session** — for every strength prescription, the
   working weight **and** the per-side plate loadout, from the calculator.

### Inputs

- **Class plan** for the week: per session → day, primary stimulus tag
  (`heavy_squat | heavy_pull | press | gymnastics | engine | mixed`), movements,
  and any prescribed % / rep / RPE targets. From Slack later; from a
  `ClassPlanProvider` (fixture/manual) for now.
- **Focus block(s)**: name, length (weeks), days/week, tier, session template
  (Section 3.4). Configured, not hardcoded.
- **Maxes**: via `MaxesProvider` (Sheet snapshot).
- **Readiness**: latest known from the `LogStore`; future days default to a
  planned tier (assume GREEN for top-set planning) with the daily-adjustment
  table applied at session time.
- **Athlete config**: available training days, deload cadence (~every 4th week;
  banked amber/red can pull it earlier). Available training days come from the
  **gym-availability layer** (`cfprog.availability`): a general weekly schedule
  (`data/availability.template.json`) of per-day options + context flags, with
  week-to-week / day-to-day overrides resolved deterministically into the week's
  actual sessions. ✅ done — see Section 5b.

### Process (policy, then arithmetic)

1. Tag each piece of work with a tier.
2. Place focus-block sessions across the week, deconflicting against class
   stimulus: no same-stimulus on consecutive days; don't double-load a pattern
   the class already taxes (move/drop the PROTECT clash — prefer *move*);
   sequence strength before conditioning on shared days.
3. Resolve each strength target to kg + plates via the calculator.
4. Emit the plan, plus a per-day readiness-adjustment guide (green/amber/red →
   what changes).

### Output

- **Start with a Markdown weekly plan** (written to a file / printed). Google
  Calendar events and Slack DM are later, swappable output adapters — keep the
  plan a structured object so renderers can vary.
- A **daily adjust** step (callable each morning) takes the day's readiness and
  re-emits that day's sessions adjusted (trim back-off on amber; drop to
  SKILL/recovery on red), reusing the same calculator.

### Scheduling

Fires Sunday night via cron / GitHub Action (Phase 2 wiring). The generator
itself is pure given its inputs, so it's testable without the scheduler.

---

## 5b. Gym-availability layer (✅ done)

The generator needs to know **which sessions I can actually do each day** before
it tiers, deconflicts, or loads anything. That is the availability layer
(`cfprog.availability`), separate from the class plan (the day's WODs): it
answers *when / what class*, never *the day's stimulus or load*.

### Two inputs, composed at resolve time

1. **General availability** — the usual weekly schedule, in
   `data/availability.template.json`, behind an `AvailabilityProvider` (same
   pattern as `MaxesProvider`; swappable for a calendar feed later). Each day
   offers one or more **options** (an ordered list of class slots). Options carry
   `requires` / `excludes` **context flags** so the right one is picked
   automatically.
2. **Overrides** — week-to-week or day-to-day changes layered on top, never
   editing the template: `rest`, `unavailable`, `choose` (force an option),
   `flags` (set context), `extra_sessions` (ad-hoc open gym). `WeekOverrides`
   loads from a weekday- or date-keyed JSON file.

### Context flags (current schedule)

`sessions_hard` (Mon AM+PM double), `pm` (swap a morning day to its all-PM
option), and `wl_priority` / `needs_double` / `wl_heavy` (the three-way Saturday
logic: 7am CF + 8am WL by default → 8am WL only when WL is the priority → 8am WL
+ 9:30am CF only when a double is needed and WL is heavy).

### Resolution (deterministic, total)

For a trainable day the chosen option is the **most specific eligible** one:
eligible = every `requires` flag active and no `excludes` flag active; most
specific = most `requires` satisfied (ties broken by listed order). An explicit
`choose` wins outright. Override precedence: `unavailable` → `rest` → `choose` →
`flags`. If nothing is eligible the day is `NEEDS_CHOICE` (it never guesses).
`resolve_week` returns a Monday-first `ResolvedWeek`; `render_week_markdown`
prints it. CLI: `cfprog-avail` (see README). The weekly generator (§5a) consumes
this resolved week as its day spine.

### What it does *not* do

No load arithmetic and no stimulus tagging — availability only says which class
slots are on. Stimulus tags and loads still come from the class plan and the
deterministic calculator (Section 8 holds).

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
| `skills/programming-policy/SKILL.md` | Code | Versioned policy (Section 3). ✅ done |
| Load/plate calculator | Code | **Deterministic. Never LLM arithmetic.** Unit-tested. ✅ done |
| Logging layer (`LogStore` → SQLite) | Code | Recorded lifts + RPE + readiness; analytics DB. ✅ done |
| Analytics (estimated 1RM, tonnage, ratio gaps) | Code | Deterministic core done; viz layer (Streamlit/React) later |
| Slack ingestion | Code | Pull latest PDF from channel; parse + tag. (blocked on Slack access) |
| Sheets read | Code | Read maxes/standards via `MaxesProvider` (stubbed to fixture until auth). |
| Gym-availability layer (`cfprog.availability`) | Code | General weekly schedule + week/day overrides → resolved week. Feeds "available training days" to the generator. ✅ done |
| Weekly generator | Code + policy | Applies SKILL.md to the class plan + resolved availability → tiers + schedule + loads. ✅ generation done (consumes the availability layer for the day spine + multi-session days; deconfliction placement + Markdown render + daily-adjust; Slack ingestion / Calendar+Slack adapters still pending) |
| Scheduled job | Code | Cron / GitHub Action, fires Sunday night. |

---

## 7. Build sequence (phased)

**Phase 1 — foundation (useful day one, no external deps): ✅ DONE**
1. Repo scaffold. ✅
2. `skills/programming-policy/SKILL.md` from Section 3. ✅
3. Deterministic **load/plate calculator**: %/RPE/rep-max → kg → exact plate
   loadout per side, from current maxes. Unit-tested against known cases. ✅
3a. (added) **Logging layer + analytics core**: SQLite `LogStore` for recorded
   lifts/RPE/readiness; deterministic estimated-1RM, tonnage, and ratio-gap
   analysis. The Sheet is now a read-only XRM snapshot. ✅

**Phase 2 — generation (current), then ingestion:**
4. **Weekly generator** ✅ DONE (generation only): applies `SKILL.md` to a class
   plan → tiers each session (push/cruise/skip), builds the weekly schedule with
   deconfliction placement, and calculates loads per session via the calculator.
   Plus a daily readiness-adjust step and a Markdown renderer (kept separate from
   generation). Driven by a `ClassPlanProvider` (fixture/manual) until Slack
   lands. See Section 5a for the contract. No external deps. Modules:
   `cfprog.classplan`, `cfprog.focus`, `cfprog.generator`, `cfprog.render`,
   `cfprog.weekcli` (`cfprog-week`). Fixtures: `data/classplan.fixture.json`,
   `data/focus_blocks.fixture.json`.
5. Slack PDF ingestion + stimulus tagging (feeds the generator; blocked on Slack
   access method).
6. Output adapters (Markdown first; Google Calendar / Slack DM later).
7. Scheduled job (cron / GitHub Action) firing Sunday night.

**Phase 3 — analytics surface + automation:**
8. Viz layer over the analytics core (PR trend lines, tonnage, ratio gaps,
   readiness-vs-performance correlation once the wearable feeds it).

---

## 8. Non-negotiables

- **Plate math is deterministic code, unit-tested. The model never does
  arithmetic.** This is the single most important constraint.
- **Sheet top section is the single source of truth for maxes** — read it, never
  duplicate or hardcode maxes elsewhere.
- **Policy lives in the versioned SKILL.md** — the generator applies it; it isn't
  re-improvised per run.
- **Logged actuals live in the SQLite store, never in the Sheet.** The Sheet is a
  read-only XRM snapshot; do not write to it (and never touch the deprecated
  training blocks). Recorded lifts/RPE/readiness go to `data/cfprog.db` via
  `LogStore`.

---

## 9. Open inputs (fill before building the dependent parts)

- [x] **Plate inventory + bar weight** — RESOLVED. 20 kg bar; pairs of
  25/20/15/10/5/2.5/1.25 kg + 0.5 kg micro, effectively unlimited supply. See
  `data/plate_inventory.json`.
- [x] **Log write target** — RESOLVED. SQLite store (`data/cfprog.db`) behind the
  `LogStore` interface. Sheet stays a read-only XRM snapshot.
- [x] **Gym availability (general + flexibility)** — RESOLVED. General weekly
  schedule captured in `data/availability.template.json` (per-day options +
  context flags); week-to-week / day-to-day changes layered as overrides and
  resolved deterministically by `cfprog.availability`. See Section 5b.
- [x] **Class-plan input (interim)** — RESOLVED. `ClassPlanProvider` interface
  with a JSON fixture/manual-entry file (`data/classplan.fixture.json`): per
  session → day, date, primary `stimulus` + `also_taxes`, movements, and strength
  pieces (lift + sets/reps + percent|rpe|rep_max target). Mirrors `MaxesProvider`.
  Distinct from availability above: availability is *which class*, the class plan
  is *what's in it* — the generator joins them by date.
- [ ] **Slack access method** — connector vs bot token. Channel is known:
  `GKAQQ7PGE` (workspace `crossfitclaremont`,
  https://crossfitclaremont.slack.com/archives/GKAQQ7PGE).
- [ ] **Output channel** — Markdown first (decided); Google Calendar events or
  Slack DM later, as swappable adapters.
- [x] **Focus block(s) config** — RESOLVED (spec default). Configured in
  `data/focus_blocks.fixture.json`: 6-wk ring-MU block 3×/wk (SKILL) +
  front-squat/strict-press strength emphasis 2×/wk (PROTECT). Athlete trains
  Mon–Sat; deload cadence ~every 4th block week (this week is normal).
- [ ] **Wearable** — device + API, or stay on self-report (optional/future).

---

## 10. Tech suggestions (non-binding)

Python for calculator + ingestion + Sheets I/O (Google Sheets API). PDF parsing
via `pdfplumber`/`pymupdf`. Dashboard: Streamlit (fast) or a React app reading
the Sheet. Schedule via cron or a GitHub Action.
