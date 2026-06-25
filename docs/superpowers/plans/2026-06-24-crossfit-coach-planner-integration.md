# CrossFit Coach — Planner Integration & Coaching Intelligence (Plan 2 of 3)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Wire the Cowork planner to the Supabase foundation (hydrate maxes, archive the plan) and add the coaching intelligence — focus stewardship + proactive flags — surfaced in the plan's `decisions` callout.

**Architecture:** The planner stays a Cowork (Claude Code) skill. It reaches Supabase through the **Supabase MCP** (the model orchestrates SELECT/INSERT), so `calc.py`/`render_week.py` stay unchanged. Proactive flags are **deterministic SQL** (a view + a function) the planner reads and phrases; judgment (tiering, deconfliction, how to word a nudge) stays in the skill instructions.

**Tech Stack:** SQL migrations `0007–0009`, the existing pytest + `psycopg` `supabase`-marked harness, the plugin's `.mcp.json` (Supabase MCP), and `skills/crossfit-coach/SKILL.md` instruction edits.

**Depends on:** PR #8 (Plan 1) merged to `main`.

## Global Constraints

- All of Plan 1's Global Constraints carry (kg, normalized lift names, e1RM model verbatim, prime directive, conventional commits).
- e1RM is only ever read from `cf_est_1rm` / the `est_1rm` column — never recomputed.
- Exactly one active focus at a time (`focus.is_active` partial unique index from Plan 1).
- DB-dependent tests carry `@pytest.mark.supabase` and skip cleanly with no DB.
- Cowork reaches Supabase via the **Supabase MCP**, not a Python DB client — the deterministic scripts remain file-based and untouched.
- Instruction (SKILL.md) tasks are verified by a **scripted example scenario** with an explicit acceptance checklist, not by pytest. Provide the exact instruction text — never "describe the behaviour".

## File Structure

- Create `supabase/migrations/0007_focus_updated_at.sql` — auto-update trigger on `focus.updated_at`.
- Create `supabase/migrations/0008_focus_status.sql` — `focus_status` view (+ grant to `chat_remote`).
- Create `supabase/migrations/0009_neglected_lifts.sql` — `neglected_lifts(days)` function.
- Create `.mcp.json` (repo root) — registers the Supabase MCP for the plugin.
- Modify `skills/crossfit-coach/SKILL.md` — hydrate step, archive-to-`plans` step, focus stewardship, proactive flags into `decisions`.
- Create tests `skills/crossfit-coach/scripts/tests/test_focus_trigger.py`, `test_focus_status.py`, `test_neglected_lifts.py`.

---

### Task 1: `focus.updated_at` auto-update trigger

**Files:**
- Create: `supabase/migrations/0007_focus_updated_at.sql`
- Test: `skills/crossfit-coach/scripts/tests/test_focus_trigger.py`

**Interfaces:**
- Consumes: `focus` (Plan 1).
- Produces: trigger function `set_updated_at()` and trigger `focus_set_updated_at` that stamps `focus.updated_at = clock_timestamp()` on every UPDATE. (Uses `clock_timestamp()`, not `now()`, so the bump is observable within a single transaction.)

- [ ] **Step 1: Write the failing test**

Create `skills/crossfit-coach/scripts/tests/test_focus_trigger.py`:
```python
import pytest


@pytest.mark.supabase
def test_focus_updated_at_bumps_on_update(db):
    with db.cursor() as cur:
        cur.execute("insert into focus (name) values ('ring_mu') returning updated_at")
        before = cur.fetchone()[0]
        cur.execute(
            "update focus set current_week = current_week + 1 "
            "where name = 'ring_mu' returning updated_at"
        )
        after = cur.fetchone()[0]
        assert after > before
    db.rollback()
```

- [ ] **Step 2: Run it, verify it fails**

Run: `python3 -m pytest skills/crossfit-coach/scripts/tests/test_focus_trigger.py -m supabase -v`
Expected: FAIL — `after > before` is false (no trigger; `now()` is constant within the transaction).

- [ ] **Step 3: Write the migration**

Create `supabase/migrations/0007_focus_updated_at.sql`:
```sql
-- Stamp updated_at on every UPDATE. clock_timestamp() (not now()) so the bump is
-- observable even within a single transaction, and reflects real modification time.
create or replace function set_updated_at()
returns trigger language plpgsql as $$
begin
  new.updated_at = clock_timestamp();
  return new;
end;
$$;

drop trigger if exists focus_set_updated_at on focus;
create trigger focus_set_updated_at
  before update on focus
  for each row execute function set_updated_at();
```

- [ ] **Step 4: Apply and verify it passes**

Run:
```bash
supabase db reset
python3 -m pytest skills/crossfit-coach/scripts/tests/test_focus_trigger.py -m supabase -v
```
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add supabase/migrations/0007_focus_updated_at.sql skills/crossfit-coach/scripts/tests/test_focus_trigger.py
git commit -m "feat: auto-update focus.updated_at on modification"
```

---

### Task 2: `focus_status` view

**Files:**
- Create: `supabase/migrations/0008_focus_status.sql`
- Test: `skills/crossfit-coach/scripts/tests/test_focus_status.py`

**Interfaces:**
- Consumes: `focus`, `exercise_log` (Plan 1).
- Produces: view `focus_status(name, program_ref, current_week, started_on, days_in, last_focus_log, days_since_focus_work)` over the single active focus; granted SELECT to `chat_remote`. `days_since_focus_work` is measured from the most recent `is_focus_work` log (or `started_on` if none yet).

- [ ] **Step 1: Write the failing test**

Create `skills/crossfit-coach/scripts/tests/test_focus_status.py`:
```python
import pytest


@pytest.mark.supabase
def test_focus_status_reports_active_focus_and_drift(db):
    with db.cursor() as cur:
        cur.execute("insert into focus (name, program_ref, current_week, started_on) "
                    "values ('ring_mu', 'drills/ring-mu-kipping.md', 3, current_date - 20)")
        # a focus-work log 5 days ago
        cur.execute("insert into exercise_log (exercise, category, reps, is_focus_work, date) "
                    "values ('ring_muscle_up', 'gymnastics', 3, true, current_date - 5)")
        cur.execute("select name, current_week, days_since_focus_work from focus_status")
        name, week, drift = cur.fetchone()
        assert name == 'ring_mu' and week == 3 and drift == 5
    db.rollback()
```

- [ ] **Step 2: Run it, verify it fails**

Run: `python3 -m pytest skills/crossfit-coach/scripts/tests/test_focus_status.py -m supabase -v`
Expected: FAIL — `relation "focus_status" does not exist`.

- [ ] **Step 3: Write the migration**

Create `supabase/migrations/0008_focus_status.sql`:
```sql
-- The active focus + drift signals the planner reads to steward it.
create or replace view focus_status as
select f.name,
       f.program_ref,
       f.current_week,
       f.started_on,
       (current_date - f.started_on) as days_in,
       (select max(e.date) from exercise_log e where e.is_focus_work) as last_focus_log,
       (current_date - coalesce(
          (select max(e.date) from exercise_log e where e.is_focus_work),
          f.started_on)) as days_since_focus_work
from focus f
where f.is_active;

-- Chat may answer "what's my focus / am I behind on it?".
grant select on focus_status to chat_remote;
```

- [ ] **Step 4: Apply and verify it passes**

Run:
```bash
supabase db reset
python3 -m pytest skills/crossfit-coach/scripts/tests/test_focus_status.py -m supabase -v
```
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add supabase/migrations/0008_focus_status.sql skills/crossfit-coach/scripts/tests/test_focus_status.py
git commit -m "feat: add focus_status view (active focus + drift signals)"
```

---

### Task 3: `neglected_lifts(days)` function

**Files:**
- Create: `supabase/migrations/0009_neglected_lifts.sql`
- Test: `skills/crossfit-coach/scripts/tests/test_neglected_lifts.py`

**Interfaces:**
- Consumes: `current_maxes`, `exercise_log` (Plan 1).
- Produces: function `neglected_lifts(days integer default 14) returns table(lift text, last_logged date)` — barbell lifts that have a current max but no barbell log entry within `days` (or never).

- [ ] **Step 1: Write the failing test**

Create `skills/crossfit-coach/scripts/tests/test_neglected_lifts.py`:
```python
import pytest


@pytest.mark.supabase
def test_neglected_lifts_flags_and_clears(db):
    with db.cursor() as cur:
        cur.execute("insert into max_events (lift, weight_kg) values ('strict_press', 70)")
        # never logged -> neglected
        cur.execute("select lift from neglected_lifts(14)")
        assert ('strict_press',) in cur.fetchall()
        # log it today -> clears
        cur.execute("insert into exercise_log (exercise, category, weight_kg, reps) "
                    "values ('strict_press', 'barbell', 60, 5)")
        cur.execute("select lift from neglected_lifts(14)")
        assert ('strict_press',) not in cur.fetchall()
    db.rollback()
```

- [ ] **Step 2: Run it, verify it fails**

Run: `python3 -m pytest skills/crossfit-coach/scripts/tests/test_neglected_lifts.py -m supabase -v`
Expected: FAIL — `function neglected_lifts(integer) does not exist`.

- [ ] **Step 3: Write the migration**

Create `supabase/migrations/0009_neglected_lifts.sql`:
```sql
-- Barbell lifts with a current max but no barbell log within `days` (or never).
create or replace function neglected_lifts(days integer default 14)
returns table(lift text, last_logged date)
language sql stable as $$
  select m.lift, max(e.date) as last_logged
  from current_maxes m
  left join exercise_log e
    on e.exercise = m.lift and e.category = 'barbell'
  group by m.lift
  having max(e.date) is null
      or max(e.date) < current_date - make_interval(days => days);
$$;
```

- [ ] **Step 4: Apply and verify it passes**

Run:
```bash
supabase db reset
python3 -m pytest skills/crossfit-coach/scripts/tests/test_neglected_lifts.py -m supabase -v
```
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add supabase/migrations/0009_neglected_lifts.sql skills/crossfit-coach/scripts/tests/test_neglected_lifts.py
git commit -m "feat: add neglected_lifts(days) function for the neglect flag"
```

---

### Task 4: Register the Supabase MCP for the plugin

**Files:**
- Create: `.mcp.json` (repo root)

**Interfaces:**
- Produces: a `supabase` MCP server available to the planner skill, reading project ref + access token from env (`SUPABASE_PROJECT_REF`, `SUPABASE_ACCESS_TOKEN`). No secrets are committed.

- [ ] **Step 1: Write `.mcp.json`**

Create `.mcp.json`:
```json
{
  "mcpServers": {
    "supabase": {
      "command": "npx",
      "args": [
        "-y",
        "@supabase/mcp-server-supabase@latest",
        "--project-ref",
        "${SUPABASE_PROJECT_REF}"
      ],
      "env": {
        "SUPABASE_ACCESS_TOKEN": "${SUPABASE_ACCESS_TOKEN}"
      }
    }
  }
}
```
(Confirm flag names against the current `@supabase/mcp-server-supabase` README — they move occasionally. For local-only dev you may instead point at the local DB; the production project ref is set in Plan 3.)

- [ ] **Step 2: Verify the server loads (manual)**

Run, with `SUPABASE_PROJECT_REF` + `SUPABASE_ACCESS_TOKEN` exported:
```bash
npx -y @supabase/mcp-server-supabase@latest --project-ref "$SUPABASE_PROJECT_REF" --help
```
Expected: the server prints usage (proves the package resolves). Acceptance: in a Claude Code session with this repo, the `supabase` MCP appears and a read tool (e.g. list tables) returns the Plan 1 objects.

- [ ] **Step 3: Commit**

```bash
git add .mcp.json
git commit -m "chore: register Supabase MCP for the planner plugin"
```

---

### Task 5: Planner hydrate + archive-to-`plans` (SKILL.md)

**Files:**
- Modify: `skills/crossfit-coach/SKILL.md` (§1 inputs; §2 step 6 "Emit")

**Interfaces:**
- Consumes: `current_maxes` (read via Supabase MCP), `plans` (insert/upsert via Supabase MCP), the existing `calc.py`/`render_week.py`.
- Produces: a deterministic hydrate-then-emit flow; `calc.py` still reads the local maxes file, now populated from Supabase.

This is an **instruction task** — verified by the scripted scenario in Step 3, not pytest.

- [ ] **Step 1: Add the hydrate instruction**

In `skills/crossfit-coach/SKILL.md`, add a subsection after §1 (Inputs):
```markdown
### §1.5 Hydrate maxes from Supabase (start of every planning turn)

Before any load math, read the current maxes from Supabase and write them to the
local maxes file the calculator reads:

1. Via the `supabase` MCP, run: `select lift, weight_kg from current_maxes`.
2. Write those rows into `scripts/data/maxes.fixture.json` under `"maxes"` as
   `{ "<lift>": { "one_rm": <weight_kg> } }` (the shape `FixtureMaxesProvider`
   already reads). Do not invent or edit maxes by hand.
3. `calc.py` then reads that file unchanged. Supabase is the source of truth;
   the file is a per-session cache.
```

- [ ] **Step 2: Add the archive-to-`plans` instruction**

In `skills/crossfit-coach/SKILL.md` §2 step 6 (Emit), after rendering the HTML, append:
```markdown
   After rendering, archive the plan via the `supabase` MCP so the chat surface
   can query it:

   ```sql
   insert into plans (week_of, spec_json, html)
   values ('<Monday ISO>', '<the plan JSON spec>', '<the rendered HTML>')
   on conflict (week_of) do update
     set spec_json = excluded.spec_json, html = excluded.html;
   ```
```

- [ ] **Step 3: Verify with a scripted scenario (acceptance)**

In a Claude Code session on this repo (Supabase reachable, seeded), run the planner with a pasted sample week. Acceptance checklist:
- [ ] The planner reads `current_maxes` via the MCP and updates `maxes.fixture.json` (the file's values match `current_maxes`).
- [ ] Loads in the output come from `calc.py` (no hand math).
- [ ] After confirming the schedule, a row appears in `plans` for that Monday with both `spec_json` and `html` populated (`select week_of, spec_json is not null, html is not null from plans`).

- [ ] **Step 4: Commit**

```bash
git add skills/crossfit-coach/SKILL.md
git commit -m "feat: planner hydrates maxes from Supabase and archives plans"
```

---

### Task 6: Focus stewardship + proactive flags into `decisions` (SKILL.md)

**Files:**
- Modify: `skills/crossfit-coach/SKILL.md` (§2 step 2 "Decide individual work"; §2 step 3/4 decisions)

**Interfaces:**
- Consumes: `focus_status` (Task 2), `neglected_lifts(14)` (Task 3), `volume_balance` (Plan 1), `current_maxes` + `references/athlete-profile.md` ratio table (for imbalance), all read via the Supabase MCP.
- Produces: the headline focus-stewardship behaviour + the three proactive flags folded into the plan's `decisions` callout.

Instruction task — verified by the scenarios in Step 2.

- [ ] **Step 1: Add the stewardship + flags instruction**

In `skills/crossfit-coach/SKILL.md` §2, replace the opening of step 2 ("Decide the individual work to fit") with:
```markdown
2. **Read the focus, then decide the individual work.** First read `focus_status`
   via the `supabase` MCP:
   - **No active focus** (no row) → **stop and ask the athlete what the focus is**
     before building the week. Do not plan personal work in a vacuum.
   - **Active focus** → fit this week's sessions from `current_week` of its
     `program_ref` drill file. If `days_since_focus_work` shows drift (focus work
     not logged recently), add a gentle reminder to `decisions` that the focus is
     `<name>` and this week's sessions matter.
   Then pick complementary PROTECT/ACCESSORY work as before.

   **Proactive flags** — read these and fold any that fire into the top-level
   `decisions` list (phrase them, don't dump rows):
   - **Neglect:** `select lift from neglected_lifts(14)` → raise priority of a
     neglected goal lift this week (especially strict press, which class under-supplies).
   - **Imbalance:** compare `current_maxes` ratios against the lift-ratio table in
     `references/athlete-profile.md`; flag a lift that has drifted out of range.
   - **Fatigue / overreach:** read `volume_balance`; if a pattern is already taxed
     hard this block, back the personal work off (feeds existing deconfliction).
   - **Focus stall:** if the focus measure isn't progressing, suggest a variation
     rather than grinding the same drill.
```

- [ ] **Step 2: Advance the focus week + verify scenarios (acceptance)**

Add to §2 step 6 (Emit): `After the week is confirmed, advance the focus: update focus set current_week = current_week + 1 where is_active (via the supabase MCP).`

Acceptance scenarios (run each in a Claude Code session):
- [ ] **No focus:** with `focus` empty, paste a week → the planner asks what the focus is before proposing personal work (does not invent it).
- [ ] **Active focus + drift:** active focus, no `is_focus_work` log for 10 days → `decisions` contains a reminder to stay on the focus.
- [ ] **Neglect:** a goal lift with a max but no recent log → `decisions` raises its priority.
- [ ] **Advance:** after confirming the week, `focus.current_week` incremented by 1.

- [ ] **Step 3: Commit**

```bash
git add skills/crossfit-coach/SKILL.md
git commit -m "feat: focus stewardship + proactive flags in the plan's decisions"
```

---

## Self-Review (spec coverage)

| Spec §7 item | Covered by |
|--------------|-----------|
| Hydrate pattern (maxes → local file) | Task 5 |
| `.mcp.json` → Supabase MCP | Task 4 |
| Archive plan to `plans` (chat queryability) | Task 5 |
| Focus stewardship (fit week, ask if none, drift reminder, advance week) | Tasks 2, 6 |
| Focus-scoped stall | Task 6 |
| Neglect flag | Tasks 3, 6 |
| Imbalance flag (vs profile ratio table) | Task 6 |
| Fatigue/overreach flag | Task 6 |
| `focus.updated_at` trigger (PR #8 follow-up) | Task 1 |

Placeholder scan: instruction tasks carry exact text to insert + scripted acceptance checklists (not "describe the behaviour"). Type consistency: `focus_status`, `neglected_lifts(days)`, `current_maxes`, `plans`, `volume_balance` names match Plan 1 and PR #8 exactly.

**Deferred to Plan 3:** `grant chat_remote to authenticator`, the hosted Supabase project, the chat connector, and the Claude Project.
