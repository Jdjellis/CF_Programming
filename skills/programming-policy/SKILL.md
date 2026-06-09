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
version: 1.2.0
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
| **PROTECT** | Front-squat strength; strict-pressing strength. These move the goals. **Priority #1.** | Push. Schedule on best-readiness / freshest days, **before** conditioning. Never let a class metcon — or skill work — cannibalise protected strength. |
| **CRUISE** | Class metcons; box-recommended extras. | The relief valve — autoregulate intensity *here* on bad days, not on protected work. **Prefer training in class**: the class session is high-value, not just filler. |
| **ACCESSORY** | Low-CNS supporting work — quad development (split squats, zombie squats), knee/tendon rehab (Spanish squats). | Appended to a non-clashing class day (never the rest day). Used as the *substitute* for a PROTECT lift the class already covers (see §3). Flex — drop before strength if time/energy is short. |
| **SKILL** | Active focus block (e.g. ring muscle-ups); HSPU technique. | Do anyway; neurologically cheap → frequency wins. Survives low-readiness days ("productive when smashed"). Flex — but **strength outranks skill**: under time/energy pressure, skill is the first thing cut, never the protected strength. |
| **DELOAD** | Planned down-week. | ~Every 4th week. Banked amber/red days can pull a deload earlier if fatigue accumulates. |

**Priority / triage order** (what survives a time-or-energy squeeze, highest
first): **1) PROTECT strength top sets → 2) class session (CRUISE) → 3) supporting
accessory → 4) skill frequency.** Strength is priority #1 and is never dropped for
skill; shed from the bottom up.

Rule of thumb: **on a bad day you scale CRUISE, you keep PROTECT's top set (or
move it), and skill is the first flex item to fall — not the strength.**

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

**Defer to class where it already covers a lift.** The athlete prefers training
in class. Where the class programming already supplies a PROTECT pattern that week
(e.g. heavy front squats programmed across the week), **defer the heavy stimulus
to class** — do *not* schedule a competing independent barbell version of that
lift. Replace the personal heavy work with **supporting accessory** (quad
development, knee/tendon rehab) that the class does *not* supply, appended to a
non-clashing class day (keep the rest day genuinely rest). A PROTECT lift the
class does *not* cover that week (e.g. strict pressing — box under-supplies it)
stays a protected independent strength session, placed on the freshest available
day.

Deconfliction decision order when placing focus-block work:
1. Does the class already cover this PROTECT lift this week? → defer the heavy
   stimulus to class; substitute supporting accessory (low-CNS) on a non-clashing
   class day. No competing barbell version of the lift.
2. Else, is today's class stimulus the same pattern as the planned PROTECT work?
   → move PROTECT to a non-conflicting, fresh day.
3. Was yesterday the same stimulus? → don't repeat; shift or swap.
4. Otherwise place PROTECT first (on the freshest, lowest class-barbell-load day),
   then ACCESSORY/SKILL, then the class CRUISE work.

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
| **Quad / knee support** (when class covers the squat) | Bulgarian split squats, zombie front squats (quad / upright-torso bias), Spanish-squat holds (knee/tendon health) — low-CNS, appended to a class day | A second heavy barbell front squat the same week the class squats heavy |

### Current focus (per-block, reference-backed)

The specific drills within a menu (e.g. *which* ring-MU progression, *which* knee
rehab) are the focus block's **current focus** — a structured `emphasis` on the
template, not a hand-typed line each week:

- **`name`** + optional **`cues`** — what to prioritise and how.
- **`reference`** — a path into the `references/` program/drill library (Markdown,
  rendered as a one-click link). The generator pulls *this week's* drills straight
  from that file, so you refine the program by editing the program, not the config.
- **`program_week` / `program_length`** — a visible **wk X/Y** progress marker. The
  week defaults to the block's `current_week` and **auto-advances** as it
  increments; an explicit `program_week` lets a focus track its own counter (start
  mid-program). Non-periodised references (a flat rehab/mobility menu) carry no
  week marker.
- **`this_week`** — an optional explicit drill list that overrides the reference
  (required for link-only references such as a purchased PDF program, which can't
  be parsed). A plain string `emphasis` still works (treated as `cues`).

Loads are **not** affected: where a drill names a lift + a percentage, the kilos
still resolve through the calculator via the template's strength pieces — the
reference text is descriptive. Multiple concurrent focuses each point at their own
reference and track their own program week (§4).

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

### 1.2.0 — 2026-06-09
- **Current focus, reference-backed (§5).** The per-week `emphasis` is now a
  structured *current focus*: a name + cues, an optional `reference` into a new
  `references/` program/drill library, and a `program_week`/`program_length`
  progress marker that auto-advances with the block week. When a reference is
  given and `this_week` is omitted, the generator pulls the week's drills straight
  from the program (single source of truth); link-only references (e.g. purchased
  PDFs) require an explicit `this_week`. A plain-string emphasis still works.
- Rationale: the athlete follows structured multi-week programs (e.g. a 12-week
  squat block) and wants to prioritise *specific* drills with links to the full
  program, rather than re-typing an emphasis line each week. No change to load
  arithmetic — the calculator still owns the kilos.

### 1.1.0 — 2026-06-09
- **Strength is priority #1 over skill.** Added an explicit triage order
  (PROTECT → CRUISE → ACCESSORY → SKILL); under time/energy pressure skill is the
  first flex item cut, never the protected strength (§1).
- **Defer to class where it already covers a lift.** Where the class already
  programmes a PROTECT pattern that week (e.g. heavy front squats), defer the
  heavy stimulus to class instead of duplicating it independently; substitute
  low-CNS supporting **ACCESSORY** work (quad development, knee/tendon rehab) on a
  non-clashing class day, keeping the rest day rest. A lift the class does *not*
  cover (strict press) stays a protected independent session on the freshest day
  (§1, §3). Added the ACCESSORY tier and the quad/knee support menu (§5).
- Noted that per-week drill selection lives in the focus block's `emphasis` field
  (refine the focus without editing the policy).
- Rationale: athlete strongly prefers training in class and wants strength
  protected above skill; avoids redundant squat volume when the box already
  supplies it. Rules only — no change to load arithmetic (still the calculator's).

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
