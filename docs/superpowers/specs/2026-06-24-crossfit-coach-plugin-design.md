# CrossFit Coach — Design Spec (v2: two-surface)

**Date:** 2026-06-24
**Status:** Draft for review
**Supersedes:** the single repo-resident `skills/crossfit-coach` skill (re-platformed, not rewritten)

## 1. Context & goal

The existing `crossfit-coach` skill turns the gym's pasted class programming + personal
focus work into a tiered, load-calculated weekly plan, adjusts it mid-week, and keeps a
training log. It is chat-first: the model supplies judgment, a deterministic script
supplies every load (the prime directive — never do load math in the model).

**Goal:** make this usable from the phone at the gym, **independent of the athlete's Mac**,
with durable state + progress analytics in **Supabase**. The design splits across **two
surfaces** along the natural seam between heavy planning and light gym-side interaction:

- **Cowork (the planning workbench)** — the weekly generation ritual. Manual, on-demand:
  the athlete triggers it and pastes the week's programming from the gym's Slack. Heavy
  judgment; local scripts run the math; no hosting.
- **Claude chat app (the gym remote)** — phone-side, light: view history, query the plan,
  log sets. Connector-only; **no server to host**.

Both surfaces are the *same coaching brain* presented two ways, unified by two shared
sources of truth (§3).

## 2. Non-goals (out of scope for v1)

- Warm-up / mobility prescriptions; bodyweight / sleep / nutrition tracking; calendar
  integration; a standalone hosted analytics dashboard.
- General adherence / planned-vs-performed tracking. **Exception:** adherence to the
  *current focus block* is in scope (§7) — permissive about general drift, protective of
  the one focus.
- Autonomous scheduling / Routines (the trigger is manual).
- **A hosted compute server.** The chat side is deliberately *view + log*; precise
  re-calculated loads stay in Cowork. (If precise in-chat adjustments are wanted later,
  add a thin MCP over `cfprog` — see §11.)

## 3. Architecture — two surfaces, two shared sources of truth

```
        COWORK (planning workbench)                 CHAT APP (gym remote, phone)
        Claude Code plugin                          Claude Project
        ─ planner skill + scripts                   ─ instructions (view/log/query)
        ─ references/ (files)                       ─ knowledge (trimmed references)
        ─ local cfprog math                         ─ scoped Supabase connector
                 │                                            │
                 └───────────────┬────────────────────────────┘
                                 ▼
                    ┌────────────────────────────┐
                    │  SUPABASE  (shared state)   │  ← single source of truth: state
                    │  + analytics views + RLS    │
                    └────────────────────────────┘
                    cfprog (shared math library)    ← single source of truth: math
```

**Shared source of truth #1 — Supabase (state):** maxes, exercise log, focus pointer,
archived plans, analytics views. Both surfaces read/write it, so they cannot disagree.

**Shared source of truth #2 — `cfprog` (math):** already a library; `calc.py`/`estimate`
are thin CLIs over it (Cowork runs them). The e1RM model is mirrored as a Supabase computed
column so the chat gets estimates without running Python — kept honest by a parity test
(§6).

**Information-architecture principle:** static knowledge → references/knowledge; mutable
state → Supabase; judgment → instructions; arithmetic → `cfprog`, never the model.

## 4. The two surfaces

### Cowork plugin (planning)
| Component | Role |
|-----------|------|
| `skills/crossfit-planner/` | weekly plan (tier class work, fit personal work, deconflict + triage), readiness autoregulation, **focus stewardship**, proactive flags, render HTML |
| `scripts/` (`calc.py`, `render_week.py`, `cfprog/…`) | deterministic math + rendering (unchanged logic) |
| `references/` | policy, athlete-profile, availability, focus-blocks pointer, drills/ |
| `.mcp.json` → Supabase MCP | full state access for planning (hydrate maxes, write plan + state) |

A second skill, `crossfit-log`, can stay in the plugin for logging from Cowork too — but
the **primary** logging/viewing surface for v1 is the chat Project. Daily-adjust lives in
`crossfit-planner` (it is "re-run part of the plan").

### Chat Project (gym remote)
| Component | Role |
|-----------|------|
| Custom instructions | lightweight: how to log a set, query the plan, present history as an Artifact, give qualitative readiness advice, and defer exact re-loads to Cowork |
| Knowledge files | a trimmed reference subset for context (e.g. policy summary, focus notes) |
| Scoped Supabase connector | read analytics views + `plans`; insert into `exercise_log`; update `focus` — nothing else (§5) |

## 5. State model (Supabase)

### `exercise_log` (generalised from the old rep-max log)
Append-only; **any** exercise, so gymnastics/skill focus work is trackable alongside lifts.

| Column | Notes |
|--------|-------|
| `id`, `date`, `created_at` | |
| `exercise` (text), `category` (`barbell`\|`gymnastics`\|`accessory`\|`other`) | |
| `weight_kg`, `reps`, `sets`, `time_seconds`, `rpe` | nullable — populate what applies |
| `assistance` (text, null), `added_load_kg` (null) | skill progressions |
| `est_1rm` | **computed column** — SQL mirror of `cfprog`'s estimator; populated only for `barbell` with weight+reps |
| `is_focus_work` (bool), `note` (text, null) | |

Modelling decision: sparse real columns (not a `jsonb` blob), to keep SQL analytics clean.

### `max_events` → `current_maxes` (view)
Each max change; `current_maxes` = latest per lift. **Barbell only** — drives `calc.py`'s
load math. Doubles as PR history.

### `focus` (single active block)
`name, program_ref (→ drills/<name>.md), current_week, started_on`. One active focus at a
time (skill *or* strength).

### `plans` (**required**, not optional)
`week_of, spec_json, html (or html_url), created_at`. The Cowork planner writes here; the
chat reads it to answer plan queries and show the visual.

### Analytics — SQL views / RPCs
`e1rm_trend(lift)`, `volume_balance(window)`, `pr_history(lift)`. The chat SELECTs these and
renders an Artifact chart. This is the payoff of choosing a DB.

### Access control
The chat connector authenticates as a **restricted Postgres role / RLS policy**: SELECT on
the analytics views + `current_maxes` + `plans`, INSERT on `exercise_log`, UPDATE on
`focus`. No DDL, no deletes. This is what makes "no server, chat has SQL access" safe.

## 6. Deterministic core (`cfprog`)

`cfprog` stays the single source of truth for math: `calc.py` (loads/plates), the e1RM
estimator (inverse of the rep-max table), `render_week.py` (presentation only). The
**prime directive holds** in Cowork — every load from `calc.py`, nothing in the model.

e1RM appears in two places by necessity (Cowork has Python; the chat does not), so:
- `cfprog.estimate` is canonical (used by Cowork/CLIs);
- a Supabase function/computed column mirrors it for immediate chat analytics;
- a **parity test** asserts the SQL mirror == `cfprog` across a grid of inputs, so the two
  cannot silently diverge.

### Hydrate pattern (Cowork)
At session start the planner reads `current_maxes` into the local maxes file; `calc.py`
reads that file unchanged. Writes go out to Supabase.

## 7. Coaching & analytics layer

**Cowork (planner) — proactive, folded into the plan's `decisions` callout:**
- **Focus stewardship (headline):** fit this week's focus sessions from `drills/<name>.md`
  (`## Week N`); flag drift if focus work isn't being logged; **ask what the focus is if
  none is active**; advance `current_week`; **focus-scoped stall check** → suggest a
  variation if the focus measure flatlines.
- **Neglect & imbalance** (vs the `athlete-profile` ratio table); **fatigue / overreach**
  (feeds deconfliction); **PR & milestones** at log time.

**Chat (gym remote) — reactive:**
- Visualise history (analytics views → an in-chat **Artifact** chart).
- Query the plan (reads `plans`): "what's my Thursday?", "how heavy is the squat?".
- Log a set (insert; e1RM auto-computed); qualitative readiness advice ("drop ~1–2 RPE,
  half the sets") — precise re-loads deferred to Cowork.

**Focus lifecycle:** register a new focus by pasting its program in Cowork → structured
into `drills/<name>.md`; the `focus` pointer advances each plan.

## 8. Output conventions

- **Cowork:** brief chat (push/cruise/skip + `decisions`) + the HTML weekly plan via
  `render_week.py`, archived to `plans`.
- **Chat:** history as Artifact charts; plan answers read from `plans`.

## 9. Data flow

**Sunday (Cowork):** trigger → hydrate `current_maxes` + read `focus` → paste Slack program
→ planner tiers/fits/flags → propose → confirm → `calc.py` loads → `render_week.py` → write
plan to `plans` + any state.

**At the gym (chat):** open the Project on the phone → "show my front-squat e1RM" (Artifact)
/ "what's today?" (reads `plans`) / "logged a strict-HSPU triple" (insert, e1RM computed).

## 10. Success criteria

- A week is generated in Cowork from **one paste + one confirm**, every load from `calc.py`,
  archived to `plans`.
- The plan is **never built without a known focus**; no active focus → the coach asks.
- From the phone chat: history charts render, plan queries answer from `plans`, and a logged
  set persists with e1RM available immediately (barbell) or its raw measures (skill).
- The SQL e1RM mirror passes its parity test against `cfprog`.

## 11. Open items to confirm at build

- **Supabase connector for the chat:** Supabase's official remote MCP (added as a custom
  connector) vs a directory connector — whichever cleanly supports the scoped role + view
  SELECTs + inserts.
- **e1RM mirror:** confirm the rep-max model ports cleanly to a SQL function (table lookup);
  fallback is deferring e1RM to the next Cowork sync.
- **Chat instructions/knowledge:** how much reference context the Project needs vs. staying
  minimal.
- **Future upgrade path:** a thin `cfprog`-wrapping MCP if precise in-chat adjustments are
  later wanted (turns "light" into "full" without redesign — same shared core).

## 12. Migration / seed (optional, one-time)

BTWB has **no public API** (manual support-ticket export only). A one-time export from BTWB
(or the current `maxes.fixture.json` / `xrm_log.json`) can seed Supabase; thereafter
Supabase is the system of record.
