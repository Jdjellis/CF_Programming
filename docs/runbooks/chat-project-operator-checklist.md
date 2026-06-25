# Chat Project — operator checklist (Plan 3 manual steps)

These are the Plan 3 steps that need **you** (an operator with a Supabase account, the
Claude consumer app, and a phone). The code/doc parts of Plan 3 are already done:

- ✅ `supabase/migrations/0010_authenticator_membership.sql` (`grant chat_remote to authenticator`) + test — landed in this branch.
- ✅ `docs/runbooks/chat-project-setup.md` — the Project instructions + knowledge list + connector decision (**Option A — Supabase MCP**).

Work top to bottom. Commands assume you run them from the repo root with the Supabase CLI
logged in (`supabase login`). Tick each box as you go.

---

## Step 1 — Provision the hosted Supabase project (Plan 3 Task 2)

- [ ] **Create + link the project** (pick your own org, region, db password):
  ```bash
  supabase projects create crossfit-coach --org-id <org> --region <region> --db-password <pw>
  supabase link --project-ref <project-ref>
  ```
- [ ] **Point `config.toml` at the hosted ref.** It currently holds the local container name
  `project_id = "eager-gagarin-76203c"` (the worktree-name default flagged back in PR #8).
  Replace it with your real `<project-ref>`:
  ```toml
  # supabase/config.toml line 5
  project_id = "<project-ref>"
  ```
- [ ] **Push all migrations to hosted:**
  ```bash
  supabase db push
  ```
  Expected: `0001`–`0010` apply cleanly.
- [ ] **Seed maxes on hosted** (the seed script is idempotent — re-running skips already-seeded lifts):
  ```bash
  DATABASE_URL="<hosted pooler connection string>" python3 supabase/seed/seed_from_fixture.py
  ```
  Expected: `seeded 14 maxes`.
- [ ] **Acceptance — verify in the Supabase SQL editor:**
  - `select count(*) from current_maxes;` → **14**
  - `select cf_est_1rm(122, 3, null);` → **131.18**
  - `\du chat_remote` (describes the *role*, not a relation — `\d` is for tables/views) or
    check the dashboard roles → the Plan 1 grants are present, and `authenticator` is a
    member of `chat_remote` (from `0010`, so it can `SET ROLE chat_remote`).
- [ ] **Export the project credentials into your Cowork environment** (Plan 2 Task 4's
  `.mcp.json` reads these — this is what turns the Plan 2 PENDING checks below green):
  ```bash
  export SUPABASE_PROJECT_REF="<project-ref>"
  export SUPABASE_ACCESS_TOKEN="<a read-mostly, project-scoped access token>"
  ```
- [ ] **Commit the linked ref** (this is the one repo change in this step):
  ```bash
  git add supabase/config.toml
  git commit -m "chore: link Supabase project_id to the hosted ref"
  ```

> ⚠️ Do **not** commit any access token or db password. Only `config.toml`'s `project_id`
> (a non-secret ref) gets committed.

---

## Step 2 — Add the chat connector (Plan 3 Task 3, Option A)

The decision is already recorded in `docs/runbooks/chat-project-setup.md`: **Option A — Supabase
MCP, no server.** `chat_remote`'s scope is documentary, not hard-enforced, on this route (the
connector authenticates with a project-scoped token that is broader than `chat_remote`). That's
acceptable for your own low-sensitivity data; `0010` keeps **Option B** (PostgREST + RLS, the real
boundary) a drop-in upgrade if you ever want hard scoping.

- [ ] In the Claude app (Pro/Max), phone or desktop: **Customize → Connectors → Add custom
  connector** → Supabase's connector / MCP URL → authenticate with a **read-mostly,
  project-scoped** Supabase access token.
- [ ] Confirm the connector lists the project's tables/views.
- [ ] **Acceptance** — in a throwaway chat with the connector attached:
  - ask it to `select count(*) from current_maxes` → returns **14**
  - confirm it can `insert into exercise_log (...)` and read back `est_1rm`.
  - *(If you instead chose Option B: verify via a `role=chat_remote` JWT against the REST
    endpoint that a `delete from exercise_log` is **rejected**.)*

---

## Step 3 — Build the Claude Project (Plan 3 Task 4 Step 2)

- [ ] In the Claude app: **Projects → New** → name it **"CrossFit Coach (gym)"**.
- [ ] Paste the **Custom instructions** from `docs/runbooks/chat-project-setup.md` (the
  `## Custom instructions (paste into the Project)` section — paste it verbatim; the wording is
  the load-bearing boundary that keeps the chat from computing loads).
- [ ] Upload the three **knowledge files** (trimmed copies are fine):
  - `skills/crossfit-coach/references/policy.md`
  - `skills/crossfit-coach/references/athlete-profile.md`
  - `skills/crossfit-coach/references/focus-blocks.md`
- [ ] Attach the connector from Step 2.

---

## Step 4 — End-to-end verification from your phone (Plan 3 Task 5)

This is the whole point of the build. In the Project chat **on your phone**:

- [ ] **Log:** "logged a strict-HSPU triple" → a row lands in `exercise_log` (`is_focus_work`
  true if it's the current focus); a barbell set reports its `est_1rm`.
- [ ] **History:** "show my front-squat e1RM" → an Artifact chart from `e1rm_trend`.
- [ ] **Plan query:** "what's my Thursday?" → answered from the latest `plans` row (written by
  the Cowork planner in Plan 2).
- [ ] **Focus:** "what's my focus / am I behind?" → answered from `focus_status`.
- [ ] **Boundary:** "recalc my squats 10% lighter" → gives qualitative advice and defers exact
  kg to Cowork (does **not** invent loads).

---

## Step 5 — Fold in the Plan 2 PENDING acceptance checks

Plan 2's SQL was unit-tested, but three behavioural checks were left PENDING because they need
exactly the hosted+seeded surface you just stood up. Run them now (they overlap Step 4 above):

- [ ] **Plan 2 Task 4 (`.mcp.json`):** with `SUPABASE_PROJECT_REF`/`SUPABASE_ACCESS_TOKEN` exported
  (Step 1), open a Claude Code session on this repo → the `supabase` MCP appears and a read tool
  (e.g. list tables) returns the Plan 1 objects.
- [ ] **Plan 2 Task 5 (hydrate + archive):** run a live Cowork planning turn → the planner reads
  `current_maxes` via the MCP and rewrites `skills/crossfit-coach/scripts/data/maxes.fixture.json`
  (values match `current_maxes`); loads come from `calc.py`; after you confirm the week, a `plans`
  row exists for that Monday with both `spec_json` and `html` populated.
- [ ] **Plan 2 Task 6 (stewardship + flags):** in a planning turn — (a) with `focus` empty, the
  planner asks what the focus is before proposing personal work; (b) with an active focus and no
  `is_focus_work` log for ~10 days, `decisions` carries a stay-on-focus reminder; (c) a goal lift
  with a max but no recent log → `decisions` raises its priority; (d) after you confirm the week,
  `focus.current_week` is incremented by 1.

---

## Notes / known caveats carried from earlier plans

- **`focus_status` drift is not scoped to the active focus period** (`0008`): `days_since_focus_work`
  takes the most recent `is_focus_work` log across *all* history, so a prior focus block's logs can
  make drift look smaller than it is (it only ever under-nudges, never spuriously nags). Bounded and
  by-design for now; a cheap tightening is `and e.date >= f.started_on` in the view's subqueries if it
  ever matters. (Full per-focus attribution would need a schema FK from `exercise_log` → `focus`.)
- **`neglected_lifts` is planner-only** and deliberately not granted to `chat_remote` (see the comment
  in `0009`). Under Option A that boundary is documentary (the connector token can read it anyway);
  it becomes a hard boundary only under Option B.
