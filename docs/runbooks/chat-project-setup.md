# Chat Project — "CrossFit Coach (gym)" setup

## Connector route decision

**Connector route: A — Supabase MCP** (no server). `chat_remote` scope is documented
but not hard-enforced; upgrade to B (PostgREST + RLS) if/when hard scoping is needed.

Option A is the chosen default. The `chat_remote` Postgres role exists and its grant
list is recorded in the codebase (see `docs/runbooks` and migration history), but the
Claude Project connector authenticates via a project-scoped Supabase access token —
role selection is advisory, not enforced at the transport layer. Option B (PostgREST +
RLS with a `role=chat_remote` JWT) is a drop-in upgrade that adds hard scoping without
any change to the Project instructions below.

For operator steps (adding the connector in the Claude app), see Task 3 Step 2 in the
project SDD.

---

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
