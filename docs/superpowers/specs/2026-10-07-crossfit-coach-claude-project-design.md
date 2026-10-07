# CrossFit Coach — Design Spec (v3: one Claude Project)

**Date:** 2026-10-07
**Status:** Approved in brainstorm; awaiting spec review
**Supersedes:** [v2 two-surface design](2026-06-24-crossfit-coach-plugin-design.md),
Plan 2 (planner integration, merged — its Supabase wiring is removed here) and Plan 3
(chat Project runbook, never executed).

## 1. Context & goal

The coach turns the gym's weekly programming plus the athlete's personal programs into a
tiered, load-calculated weekly plan, adjusts it mid-week, and keeps track of where each
self-paced program is up to. The model supplies **judgment**; code (or the gym's own
spreadsheet) supplies **every load** — the prime directive is unchanged.

v2 split this across Cowork (planning, Python) and a claude.ai chat Project (phone, no
Python) joined by Supabase. **Claude Projects (beta)** removes the reason for the split:
every project thread is a cloud Claude Code session that clones this repo, loads its
skill, runs `calc.py`, reaches claude.ai connectors, and is usable from the mobile app.

**Goal:** one Claude Project is the whole coach — weekly planning, mid-week adjustment,
progress tracking — from phone or desktop. **As simple as possible**; v2 was
over-engineered.

## 2. Non-goals

- A training log. **BTWB** already logs everything programmed (and accessory work can be
  added there); the coach does not duplicate it.
- Analytics. BTWB covers it. A BTWB export dropped into the Library is the escape hatch.
- Reading BTWB automatically (no API; browser scraping is fragile and would need the
  password as a secret).
- Any database or hosted server. **Supabase is removed.**
- Writing to the athlete's Google Sheets. The athlete updates them; the coach reads.

## 3. What the coach juggles

Several programs, each on **its own clock**, merged into one week:

| Program | Source | Position held by |
|---|---|---|
| Class / Comp / Weightlifting | Weekly PDFs in Slack channels | The calendar |
| POLP (back squat, front squat, bench, deadlift, press) | The gym's POLP workbook in Drive — it does its own load math | The workbook: next unlogged row per lift (athlete logs there) |
| Rowing 12-wk (started Sep in the endurance channel; athlete is behind) | Endurance channel PDF, transcribed once | Coach (`programs/`) |
| Running progression | Same | Coach (`programs/`) |
| Pressing 4–8 wk | Designed with the coach in chat | Coach (`programs/`) |

POLP slots appear in class programming as allotted time ("Bench Press — POLP
programming"); the coach fills them with that lift's next workbook row.

## 4. Architecture

```
            Claude Project "CrossFit Coach"  (claude.ai/code · desktop · mobile)
            ─ conversation (coordinator; no connectors)
            ─ one thread per training week  ← Sunday routine starts it
            ─ Library: weekly HTML, raw PDFs, ad-hoc drops
                          │ clones
                          ▼
            GitHub repo (this one) — the brain and the state
            ─ .claude/skills/crossfit-coach/  (skill, references, scripts)
            ─ programs/  data/  plans/        (state, committed to main)
                          │ reads
              ┌───────────┴────────────┐
              ▼                        ▼
   Slack (bot token, env secret)   Google Drive connector
   weekly programming PDFs         POLP workbook, XRM sheet
```

**Placement rule:** anything the coach reads back next week lives in the **repo**
(versioned, writable by any thread, survives the project). Anything only the athlete
views, or raw input, lives in the **Library** (copies, no history, deleted with the
project).

## 5. Repo layout

```
.claude/skills/crossfit-coach/          ← moved from skills/crossfit-coach/ (threads only
  SKILL.md                                 load skills from .claude/skills/)
  references/
    policy.md, athlete-profile.md, availability.md   (kept)
    drills/                              (kept — a library of templates, incl. the
                                          never-started squat-12wk and ring-MU blocks)
    examples/                            (kept)
  scripts/
    calc.py, estimate_1rm.py, cfprog/    (kept — deterministic math)
    render_week.py                       (kept — phone-first HTML)
    fetch_slack.py                       (new)
    tests/                               (cfprog/calculator/estimate/render + fetch_slack)
programs/
  <start-date>-<name>.md                 e.g. 2026-10-13-rowing-12wk.md
data/
  maxes.json                             ← replaces scripts/data/maxes.fixture.json
plans/
  <Monday>.json                          the confirmed week's spec
CLAUDE.md                                repo rules (commit state to main, push at once)
.claude/settings.json                    pre-approved commands
```

**Removed:** `supabase/`, `.mcp.json`, the Supabase-dependent tests
(`test_supabase_schema`, `test_e1rm_parity`, `test_analytics_views`, `test_scoped_role`,
`test_focus_plans`, `test_focus_status`, `test_focus_trigger`, `test_neglected_lifts`),
`log_xrm.py`, `xrm_log.json`,
`references/focus-blocks.md` (replaced by `programs/`), the Supabase sections of
SKILL.md (§1.5 hydrate, `plans` insert, `focus_status` reads, proactive-flag SQL).
`conftest.py` loses its `db` fixture / `supabase` marker; `requirements.txt` loses the
Supabase test deps. README.md and PROJECT_SPEC.md are updated to describe v3. Plans 2
and 3 get a "Superseded by v3" banner.

### 5.1 Program file format

Plain markdown; read by the model, no parser.

```markdown
---
name: Rowing 12-wk
status: active            # active | done
started: 2026-10-13       # the athlete's own start, not the channel's
source: Endurance channel PDF, Sep 2026 (original in Library)
current: W1 S1            # next session to do
sessions_per_week: 2
---

## Sessions
### W1 S1
<verbatim session text>
...

## Log
- 2026-10-19 — W1 S1, S2 done. "Felt easy." → current: W2 S1
```

`polp.md` is the exception: no sessions or pointer — it records the workbook's Drive
file ID, the lifts in play, and notes; position always comes from the workbook.

### 5.2 Maxes

`data/maxes.json` is the coach's own record and what `calc.py` reads (same shape as the
old fixture). When a needed lift is missing or looks stale, the coach checks the XRM
sheet in Drive, **confirms with the athlete**, then writes and commits. When the athlete
reports a heavy set, `estimate_1rm.py` gives the e1RM and the coach asks whether to
update the max. POLP lifts don't use it — the workbook's kg are used verbatim (it rounds
to 1 kg; `calc.py` to 0.5 kg; never mix them).

## 6. The weekly loop

**Sunday 3pm AWST** a project routine starts thread **"Week of <Monday>"**:

1. **Gather** (no input needed)
   - `fetch_slack.py` downloads the week's PDFs from the Performance, Comp,
     Weightlifting and Endurance channels into the Library.
   - Read the POLP workbook (last logged + next row per lift).
   - Read last week's `plans/<Monday>.json` and every `status: active` program.
   - If the PDFs aren't posted yet: say so and wait for the athlete's "go".
2. **Draft** — the existing SKILL §2 order: evaluate the class week → fit each active
   program's next session(s), POLP rows into POLP slots → deconflict / triage → build
   the AM/PM grid and decisions. Assumes last week went as planned.
3. **One stop** — a single message: last week as the coach understands it (POLP results
   from the workbook; self-paced sessions assumed done) + the proposed week + "anything
   missed, how did it go, and is this OK?"
4. **Apply the reply**
   - Update `programs/` pointers and logs, `data/maxes.json` if changed; commit + push.
   - If the reply changes the plan, re-draft and ask again (step 3). Otherwise continue.
5. **Emit** — resolve loads (`calc.py` / workbook), write `plans/<Monday>.json`,
   commit + push, render the HTML into the Library.

**Mid-week**, messages go to the same thread: "what's today?", "smashed, adjust
Thursday" (existing autoregulation, policy §2), "row W1 S2 done, felt easy" (update +
commit), "triple at 122" (e1RM, offer to update max).

Every state change is committed and pushed **immediately** — a cloud sandbox can resume
from a fresh clone and lose uncommitted work.

## 7. fetch_slack.py

Small, stdlib-only CLI.

- Input: `SLACK_BOT_TOKEN` env var; channel names/IDs from a constant or flag; a
  `--since` date (default: the most recent Sunday 00:00 AWST).
- Behaviour: for each channel, list messages since `--since`, collect PDF file shares,
  download each to an output dir (`--out`, default a temp dir; the thread then delivers
  the files to the Library), print one line per
  file (channel, filename, posted time). Exit non-zero with a clear message when the
  token is missing, a channel isn't found, or a channel has no PDF since `--since`
  (reported per channel, so a partial week is visible).
- Tests: mocked HTTP for the happy path, missing token, no PDFs, partial channels.
- Exact Slack scopes and channel IDs are confirmed during implementation against the
  athlete's app.

## 8. Project configuration

| Setting | Value |
|---|---|
| Repository | This repo only (so `.claude/settings.json` permission rules apply to threads) |
| Instructions | §8.1 |
| Environment | Secret `SLACK_BOT_TOKEN`; network allows `slack.com`, `files.slack.com`; no setup script |
| Connectors | Google Drive (claude.ai account) |
| Routine | Sunday 15:00 AWST → "Week of <Monday>" thread running §6 |
| Models | Threads: Opus, medium effort. Coordinator: default |
| GitHub | Claude GitHub App on the repo; `main` not branch-protected |
| `.claude/settings.json` | Allow `python3 .claude/skills/crossfit-coach/scripts/*`, `git add/commit`, `git push origin main` |

### 8.1 Project instructions (draft)

```text
This project is my personal CrossFit coach. The crossfit-coach skill in the repo is the
playbook; follow it.

- One thread per training week ("Week of <Monday>"). Route every mid-week message to
  the current week's thread. Answer in the conversation only when the answer is already
  in a thread's report.
- State lives in programs/, data/ and plans/. Commit those straight to main and push
  immediately after each change. Never open a pull request for state.
- Never compute a load in your head: calc.py or the POLP workbook, verbatim.
- If Slack, Drive or a max is unavailable, say exactly what's missing and wait. Don't
  guess or substitute.
```

## 9. Error handling

| Situation | Behaviour |
|---|---|
| PDFs not posted | Report which channels are missing; wait for "go" |
| Drive unreadable | Ask the athlete for the POLP rows / max directly |
| Max missing or stale | Check XRM sheet → confirm with athlete → record |
| Push fails | Say so in the thread; don't continue as if saved |
| Unknown situation | Reason from athlete-profile.md and say so (existing rule) |

## 10. Testing

Keep the existing `cfprog`, calculator, estimator and renderer tests; add
`fetch_slack.py` tests (§7). No parser and no tests for `programs/` — the model reads it.
`pytest` passes with no Supabase marker or database.

## 11. Rollout

1. **Repo changes** (one PR): move the skill, add `programs/`, `data/`, `plans/`,
   `CLAUDE.md`, `.claude/settings.json`, `fetch_slack.py`; rewrite SKILL.md around §6;
   remove Supabase and the log; banner the old plans.
2. **Project setup** (manual): GitHub App, create the project, instructions,
   environment + secret, confirm Drive connector, model settings.
3. **First project tasks** (in the project, not code):
   - Priorities review: what matters for the next couple of months; refresh
     athlete-profile.md / policy.md if needed.
   - Transcribe the rowing and running blocks from the endurance channel into
     `programs/`; pick personal start dates.
   - Design the pressing block with the coach (mind the shoulder note on the POLP press
     1RM and the "way too hard" wk1 note).
   - Seed `data/maxes.json` from the XRM sheet, confirmed with the athlete.
4. **Dry run**: trigger the routine manually once; check the PDFs land, the one-stop
   message reads well, commits reach main, and the HTML opens from the **Library on the
   mobile app** (unverified in the docs — fallback: commit the HTML to `plans/` too).
5. Enable the Sunday schedule.

## 12. Open risks

- **Projects is beta** and rolling out; behaviour (routing, Library, routines) may shift.
- **"Commit to main" is an instruction, not a setting** — a thread may still branch. The
  dry run checks this; CLAUDE.md repeats it.
- **Library HTML on mobile** unverified (§11.4).
- **Cost:** threads draw on the plan faster than a single session; one thread per week at
  medium effort keeps it modest. Revisit in Project settings > Usage after a month.
