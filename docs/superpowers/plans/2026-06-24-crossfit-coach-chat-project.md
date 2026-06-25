# CrossFit Coach — Chat Project Runbook (Plan 3 of 3)

> **For agentic workers:** parts of this plan are **configuration in hosted dashboards / the Claude app**, not code. Code/SQL steps follow the usual TDD loop; manual steps carry an explicit verification check. Use superpowers:subagent-driven-development for the code tasks; do the manual tasks yourself with the operator.

**Goal:** Stand up the gym-side surface — a hosted Supabase, the scoped chat connection, and a Claude **Project** (instructions + knowledge) — so the athlete can view history, query the plan, and log sets from their phone.

**Architecture:** A Claude Project in the consumer app, connected to the hosted Supabase via a connector. **No server is hosted** (the athlete's choice). The chat is *view + log + qualitative advice* only; planning and exact loads stay in Cowork.

**Depends on:** Plans 1 & 2 merged; a Supabase account.

## Global Constraints

- All prior Global Constraints carry. The chat **never** computes a load or invents a max.
- Exercise names normalised to `lowercase_with_underscores` before insert.
- The chat is read + log + qualitative advice; it must defer exact re-loads to Cowork.

## ⚠️ The one real decision: how the connector enforces scope

Plan 1 built a least-privilege `chat_remote` role. Whether it actually *binds* depends on how the chat connects, and the "no server" choice constrains the options:

- **Option A — Supabase MCP connector (zero hosting, recommended for "no server").** The Claude app adds Supabase's connector, authenticating with a Supabase **access token**. This is **broader than `chat_remote`** (project-level), so the scoped role becomes defense-in-documentation rather than a hard wall. Acceptable here because it's the athlete's own low-sensitivity data, the Project instructions keep the chat read-mostly, and Supabase's connector supports a read-mostly posture. This honours "no server".
- **Option B — PostgREST data API + RLS (hard scoping, tiny shim).** The chat goes through Supabase's REST endpoint with a JWT carrying `role=chat_remote` (enabled by Task 1's grant) + RLS policies. This makes `chat_remote` the real boundary — but reaching PostgREST from the Claude app needs a connector that speaks the data API, i.e. the **small server we deferred**. Choosing B reopens that hosting cost.

**Recommendation:** start with **Option A** (matches the decision on record), keep Task 1's grant + this note so **B is a drop-in upgrade** the day hard scoping matters. Task 3 records the choice.

## File Structure

- Create `supabase/migrations/0010_authenticator_membership.sql` — `grant chat_remote to authenticator` (enables Option B; harmless under A).
- Create `skills/crossfit-coach/scripts/tests/test_authenticator_membership.py`.
- Modify `supabase/config.toml` — set `project_id` to the real linked ref.
- Create `docs/runbooks/chat-project-setup.md` — the Project instructions + knowledge list (operator-facing).

---

### Task 1: `grant chat_remote to authenticator`

**Files:**
- Create: `supabase/migrations/0010_authenticator_membership.sql`
- Test: `skills/crossfit-coach/scripts/tests/test_authenticator_membership.py`

**Interfaces:**
- Consumes: role `chat_remote` (Plan 1), Supabase's built-in `authenticator` role.
- Produces: membership so a JWT with `role=chat_remote` is served as `chat_remote` (Option B). Does not widen `chat_remote`'s own privileges.

- [ ] **Step 1: Write the failing test**

Create `skills/crossfit-coach/scripts/tests/test_authenticator_membership.py`:
```python
import pytest


@pytest.mark.supabase
def test_authenticator_can_assume_chat_remote(db):
    with db.cursor() as cur:
        cur.execute(
            "select 1 from pg_auth_members m "
            "join pg_roles r on m.roleid = r.oid "
            "join pg_roles mem on m.member = mem.oid "
            "where r.rolname = 'chat_remote' and mem.rolname = 'authenticator'"
        )
        assert cur.fetchone() is not None
    db.rollback()
```

- [ ] **Step 2: Run it, verify it fails**

Run: `python3 -m pytest skills/crossfit-coach/scripts/tests/test_authenticator_membership.py -m supabase -v`
Expected: FAIL — no membership row.

- [ ] **Step 3: Write the migration**

Create `supabase/migrations/0010_authenticator_membership.sql`:
```sql
-- Let Supabase's PostgREST login role (authenticator) SET ROLE into chat_remote,
-- so a request with a JWT role claim of 'chat_remote' is served with exactly
-- chat_remote's privileges. Only load-bearing for the PostgREST data-API route
-- (Option B); harmless under the Supabase-MCP route (Option A).
grant chat_remote to authenticator;
```

- [ ] **Step 4: Apply and verify it passes**

Run:
```bash
supabase db reset
python3 -m pytest skills/crossfit-coach/scripts/tests/test_authenticator_membership.py -m supabase -v
```
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add supabase/migrations/0010_authenticator_membership.sql \
        skills/crossfit-coach/scripts/tests/test_authenticator_membership.py
git commit -m "feat: grant chat_remote to authenticator (enables scoped data-API route)"
```

---

### Task 2: Provision hosted Supabase + push migrations

**Files:**
- Modify: `supabase/config.toml` (`project_id`)

Manual/runbook task. Verification check at the end.

- [ ] **Step 1: Create the project and link**

Run (operator, with a Supabase account):
```bash
supabase projects create crossfit-coach --org-id <org> --region <region> --db-password <pw>
supabase link --project-ref <project-ref>
```
Then set `project_id = "<project-ref>"` in `supabase/config.toml` (replacing the worktree-name default flagged in PR #8).

- [ ] **Step 2: Push all migrations to hosted**

Run: `supabase db push`
Expected: migrations `0001`–`0010` apply cleanly to the hosted database.

- [ ] **Step 3: Seed maxes on hosted**

Run: `DATABASE_URL="<hosted pooler connection string>" python3 supabase/seed/seed_from_fixture.py`
Expected: `seeded 14 maxes`.

- [ ] **Step 4: Verify (acceptance)**

In the Supabase SQL editor: `select count(*) from current_maxes;` → 14; `select cf_est_1rm(122,3,null);` → `131.18`; `\d chat_remote` grants present. Set `SUPABASE_PROJECT_REF`/`SUPABASE_ACCESS_TOKEN` in the Cowork environment (Plan 2 Task 4 reads these).

- [ ] **Step 5: Commit**

```bash
git add supabase/config.toml
git commit -m "chore: link Supabase project_id to the hosted ref"
```

---

### Task 3: Choose + configure the chat connector

Manual/runbook task. Record the choice; default to Option A.

- [ ] **Step 1: Record the decision**

Add a short note to `docs/runbooks/chat-project-setup.md` (created in Task 4): "Connector route: **A — Supabase MCP** (no server). `chat_remote` scope is documented but not hard-enforced; upgrade to B (PostgREST + RLS) if/when hard scoping is needed."

- [ ] **Step 2: Add the connector (Option A)**

In the Claude app (Pro/Max), on your phone or desktop: **Customize → Connectors → Add custom connector** → Supabase's connector / MCP URL → authenticate with a **read-mostly, project-scoped** Supabase access token. Confirm the connector lists the project's tables/views.

- [ ] **Step 3: Verify (acceptance)**

In a throwaway chat with the connector attached: ask it to `select count(*) from current_maxes` → returns 14. Confirm it can `insert into exercise_log (...)` and read back `est_1rm`. (If you chose Option B instead, verify via a `role=chat_remote` JWT against the REST endpoint that a `delete from exercise_log` is rejected.)

---

### Task 4: Create the Claude Project

Manual/runbook task. The instruction + knowledge content below is the deliverable.

- [ ] **Step 1: Create `docs/runbooks/chat-project-setup.md`**

Create `docs/runbooks/chat-project-setup.md`:
```markdown
# Chat Project — "CrossFit Coach (gym)" setup

Connector route: A — Supabase MCP (see Plan 3 §"one real decision").

## Custom instructions (paste into the Project)

You are the athlete's gym-side CrossFit assistant — a LIGHT surface: view history,
answer questions about the current week's plan, and log performed sets. You do NOT
plan the week or recalculate loads; weekly planning and exact load math happen in
Cowork. A Supabase connector exposes the training database.

LOG a set: insert into exercise_log (exercise, category, weight_kg, reps, sets, rpe,
is_focus_work, note). Normalise exercise to lowercase_with_underscores; category is
one of barbell|gymnastics|accessory|other. After a barbell set, read back its est_1rm
and report it (e.g. "e1RM ~131 kg, up from ~129 at the start of the block").

SHOW history: query e1rm_trend, pr_history, volume_balance, or focus_status, and
render trends as a chart Artifact.

ANSWER plan questions: read the latest plans row (by week_of); answer from spec_json
or show html.

READINESS: give QUALITATIVE advice only ("drop ~1–2 RPE, halve the back-off sets").
Never compute a new exact load — say "I'll get Cowork to recalc the exact kg."

Never invent a max or a load. Never do load math yourself.

## Knowledge files (upload trimmed copies)
- references/policy.md (push/cruise/skip tiers, readiness)
- references/athlete-profile.md (goals + lift-ratio table)
- references/focus-blocks.md (current focus context)
```

- [ ] **Step 2: Build the Project (operator)**

In the Claude app: **Projects → New** "CrossFit Coach (gym)" → paste the custom instructions → upload the three knowledge files → attach the connector from Task 3.

- [ ] **Step 3: Commit the runbook**

```bash
git add docs/runbooks/chat-project-setup.md
git commit -m "docs: chat Project setup runbook (instructions + knowledge + connector)"
```

---

### Task 5: End-to-end verification from the phone

Manual acceptance — the whole point of the build.

- [ ] **Log:** in the Project chat on your phone, "logged a strict-HSPU triple" → a row lands in `exercise_log` (`is_focus_work` true if it's the focus); a barbell set reports its `est_1rm`.
- [ ] **History:** "show my front-squat e1RM" → an Artifact chart from `e1rm_trend`.
- [ ] **Plan query:** "what's my Thursday?" → answered from the latest `plans` row (written by the Cowork planner in Plan 2).
- [ ] **Focus:** "what's my focus / am I behind?" → answered from `focus_status`.
- [ ] **Boundary:** "recalc my squats 10% lighter" → it gives qualitative advice and defers exact kg to Cowork (does not invent loads).

---

## Carried over from Plan 2 execution

> Recorded while executing Plan 2 on branch `claude/thirsty-cori-1d131d` (migrations `0007`–`0009`, `.mcp.json`, the planner SKILL.md edits). These were not verifiable in the Plan-2 session — they need the hosted, seeded Supabase + live sessions that **this** plan stands up — so they land here rather than being lost.

### A. PENDING acceptance checks from Plan 2 (verify once Plan 3 Task 2 sets the env + connector)

Plan 2's SQL was TDD-tested locally (`supabase db reset` + pytest, all green), but these *behavioural* checks require a live surface and are still unrun:

- [ ] **Plan 2 Task 4 (`.mcp.json`):** in a Claude Code session on this repo with `SUPABASE_PROJECT_REF`/`SUPABASE_ACCESS_TOKEN` exported (set in Plan 3 Task 2 §4), the `supabase` MCP appears and a read tool (e.g. list tables) returns the Plan 1 objects.
- [ ] **Plan 2 Task 5 (hydrate + archive):** in a live planning turn against the seeded DB — the planner reads `current_maxes` via the MCP and rewrites `scripts/data/maxes.fixture.json` (values match `current_maxes`); loads come from `calc.py` (no hand math); after confirm, a `plans` row exists for that Monday with `spec_json` **and** `html` populated.
- [ ] **Plan 2 Task 6 (stewardship + flags):** (a) `focus` empty → planner asks what the focus is before proposing personal work; (b) active focus, no `is_focus_work` log for ~10 days → `decisions` carries a stay-on-focus reminder; (c) a goal lift with a max but no recent log → `decisions` raises its priority; (d) after confirming the week, `focus.current_week` incremented by 1.

These overlap Plan 3 Task 5's phone verification (which already exercises `focus_status` and the `plans` row) — fold them in there rather than running a separate pass.

### B. Backlog surfaced by the Plan 2 final review (Minor — not blockers)

- **`focus_status` drift is not scoped to the active focus period** (`0008_focus_status.sql`): `last_focus_log` / `days_since_focus_work` take `max(date) where is_focus_work` across *all* `exercise_log` rows, not just the current focus's. A prior focus block's logs can bleed in — impact is bounded (it only ever makes drift look *smaller*, i.e. under-nudges). It was verbatim-from-plan, so a design call, not a defect. Matters here because Plan 3 Task 5's "am I behind on my focus?" reads `focus_status`. True per-focus attribution would need a schema FK from `exercise_log` → `focus` (none exists); a cheap partial fix is `and e.date >= f.started_on` in both subqueries.
- **No test for the `focus_status` no-log fallback branch** (`test_focus_status.py`): the `coalesce(..., started_on)` path (focus with zero `is_focus_work` logs → `days_since_focus_work == days_in`) is untested. Add the assertion if `focus_status` is touched again.
- Cosmetic only: `0009` has no trailing newline; `test_focus_trigger.py` rollback lacks an explanatory comment.

### C. Cross-link to §"one real decision"

Plan 2 Task 4's commit [`68a8281`] added a comment to `0009_neglected_lifts.sql` stating `neglected_lifts` is **planner-only** and must **not** be granted to `chat_remote`. Note this is a *documentary* boundary: under **Option A** (Supabase MCP, project-scoped token) the connector can read it regardless, exactly as §"one real decision" already warns. The comment becomes a *hard* boundary only under **Option B** (PostgREST + `role=chat_remote`), where the absent grant actually hides it from chat. No action needed — just keep the two consistent if the connector route changes.

---

## Self-Review (spec coverage)

| Spec item | Covered by |
|-----------|-----------|
| `grant chat_remote to authenticator` (PR #8 deferral) | Task 1 |
| Hosted Supabase + migrations + seed | Task 2 |
| Scoped connector + the honest scope caveat | §"one real decision", Task 3 |
| Claude Project: instructions + knowledge | Task 4 |
| Chat does view + log + qualitative advice (not planning) | Task 4 instructions, Task 5 |
| End-to-end gym verification | Task 5 |

Open/honest items: under Option A the `chat_remote` scope is documentary, not enforced — Task 1 keeps Option B a drop-in upgrade. Connector tool-surface specifics (exact Supabase connector add-flow) may shift; verify against current Claude/Supabase docs at setup time.
