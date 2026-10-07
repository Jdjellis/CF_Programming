# CF_Programming — a personal CrossFit coach (Claude Project)

A coach that runs as a [Claude Project](https://code.claude.com/docs/en/claude-projects):
one conversation, one thread per training week, usable from the phone. Each Sunday it
pulls the gym's programming from Slack, reads the POLP workbook from Google Drive,
checks in on last week, and proposes a tiered, load-calculated week that fits the
athlete's personal programs (rowing, running, pressing…) around class.

> **Core principle:** the model supplies *judgment*; code (or the gym's POLP workbook)
> supplies *arithmetic*. The coach never computes a weight in its head.

## How it's used

- **Sunday 15:00 AWST** a routine starts "Week of <Monday>". The coach replies once
  with last week as it understands it, the proposed week, and "anything missed, how
  did it feel, is this OK?". Answer from the phone; it finishes the plan and drops the
  HTML in the Project Library.
- **Mid-week**, in the same thread: "what's today?", "smashed, adjust Thursday",
  "row W1 S2 done", "triple at 122".

## Layout

```
.claude/skills/crossfit-coach/   the skill (playbook, policy, references, scripts)
  scripts/calc.py                %/rep-max/RPE -> loadable kg (from data/maxes.json)
  scripts/estimate_1rm.py        e1RM from a performed set
  scripts/render_week.py         phone-first weekly HTML
  scripts/fetch_slack.py         the week's programming PDFs from Slack
programs/                        personal programs + where each is up to (state)
data/maxes.json                  the coach's max record (state)
plans/                           each confirmed week's spec (state)
CLAUDE.md                        repo rules — state is committed straight to main
docs/runbooks/project-setup.md   how the Project is configured
```

Logging lives in **BTWB** (the gym's app); maxes are cross-checked against the
athlete's XRM sheet. There is no database.

## Tests

```bash
python3 -m pip install pytest
python3 -m pytest
```

## Background

- Design: [`docs/superpowers/specs/2026-10-07-crossfit-coach-claude-project-design.md`](docs/superpowers/specs/2026-10-07-crossfit-coach-claude-project-design.md)
- Athlete profile and policy rationale: [`PROJECT_SPEC.md`](PROJECT_SPEC.md)
- Earlier designs (deterministic generator → chat skill → Supabase two-surface) are in
  `docs/superpowers/` and git history.
