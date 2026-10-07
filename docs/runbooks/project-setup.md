# Project setup — "CrossFit Coach"

Do these once, in order, after the v3 PR is merged. Each step ends with a check.

## 1. GitHub
- Install the [Claude GitHub App](https://github.com/apps/claude) on this repo.
- Confirm `main` has **no branch protection** that blocks direct pushes
  (Settings → Branches). Threads commit state straight to `main`.
- **Check:** the repo appears in the Project's **New project** dialog.

## 2. Slack app
- Bot token scopes: `channels:read`, `groups:read`, `channels:history`,
  `groups:history`, `files:read`. Reinstall the app if scopes changed.
- Invite the bot to each programming channel (`/invite @<bot>`).
- Write the exact channel names, one per line, to `data/slack_channels.txt`;
  commit and push to `main`.
- **Check (locally):** `SLACK_BOT_TOKEN=<token> python3 .claude/skills/crossfit-coach/scripts/fetch_slack.py --since <last Sunday> --out /tmp/pdfs`
  lists last week's PDFs (exit 0, or 3 naming a channel that genuinely had none).

## 3. Create the Project
- claude.ai/code → **Projects → New project**. Name: `CrossFit Coach`. Goal:
  `Coach my training week by week`. Context: this repo only.
- **Project settings → Memory → Project instructions:** paste

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

- **Project settings → General:** Thread model **Opus**, Thread effort **medium**;
  coordinator left at default.
- **Check:** settings saved; the repo is listed under Environment.

## 4. Environment and connectors
- **Project settings → Environment → cloud environment:** add secret
  `SLACK_BOT_TOKEN`; allow network domains `slack.com` and `files.slack.com`.
- claude.ai/customize/connectors: **Google Drive** connected.
- **Check:** in the project conversation, ask: "Start a thread that runs
  `fetch_slack.py --out out/pdfs` and reads the POLP workbook from programs/polp.md,
  then reports what it found. Don't plan anything." It lists the PDFs and each POLP
  lift's next row.

## 5. First tasks (in the project conversation)
1. **Priorities review** — what matters for the next couple of months; refresh
   `athlete-profile.md` / `policy.md` via a PR if needed.
2. **Rowing and running** — find the blocks in the Endurance channel, pick personal
   start dates, transcribe each into `programs/<start-date>-<name>.md`.
3. **Pressing block** — design a 4–8 week block with the coach (mind the shoulder
   and the POLP press wk1 note); save to `programs/`.
4. **Maxes** — reconcile `data/maxes.json` with the XRM sheet and the POLP Setup tab
   (Setup currently shows FS 140, bench 110, DL 245, press 69); confirm each change.
- **Check:** `programs/` has the new files on `main`, each `status: active`.

## 6. Dry run
- Ask: "Create a routine that, every Sunday at 15:00 Australia/Perth, starts a thread
  named 'Week of <next Monday>' that runs the crossfit-coach weekly loop, but don't
  enable the schedule yet." Then run it once now from the **Routines** tab.
- **Check all of:**
  - [ ] PDFs fetched (or a clear "not posted yet" wait).
  - [ ] One message with last week + proposed week + the check-in question.
  - [ ] After your reply, `chore(state)` commits land on `main` (not a branch / PR).
  - [ ] The HTML opens from the **Library on the mobile app**. If it doesn't: change
        SKILL.md §3 Step 5 to also commit the HTML under `plans/`, and open it from
        GitHub instead.
  - [ ] A mid-week message in the thread ("what's today?") gets the right day.
  - [ ] Before its first state change, the thread is on `main` (`git branch --show-current`).
  - [ ] The run needed no permission prompts (otherwise add allow rules to `.claude/settings.json`).
- Enable the Sunday 15:00 Australia/Perth schedule only after every check passes.
- After a month: **Project settings → Usage**; lower thread effort if it's heavy.
