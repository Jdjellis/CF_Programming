# CF_Programming — repo rules

This repo is the brain and the state of a personal CrossFit coach that runs as a
Claude Project. The playbook is `.claude/skills/crossfit-coach/SKILL.md`; follow it.

## State: commit straight to main

`programs/`, `data/` and `plans/` are the coach's state. After **every** change to
them, immediately:

    git switch main            # only if `git branch --show-current` isn't main
    git add <the changed files>
    git commit -m "chore(state): <what changed>"
    git push origin HEAD:main

Never put state on a branch or in a pull request. Never batch state changes to the
end of a session — a cloud sandbox can resume from a fresh clone and lose
uncommitted work. If the push is rejected (another thread pushed first): `git pull --rebase origin main`, then push once more. If it still fails, say so plainly and stop treating the change as saved.

## Code: branch and PR

Changes to the skill, references or scripts go on a branch with a pull request.
Run `python3 -m pytest` first. Runtime code is Python standard library only.

## Never

- Compute a load in your head: `calc.py`, or the POLP workbook verbatim.
- Invent a max: `data/maxes.json`, else check the XRM sheet and confirm with the athlete.
- Write to the athlete's Google Sheets.
