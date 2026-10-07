# CrossFit Coach as a Claude Project — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking. Task 8 is a **manual runbook** done with the athlete, not by a subagent.

**Goal:** Re-platform the crossfit-coach skill so one Claude Project (cloud threads cloned from this repo) is the whole coach — weekly planning, mid-week adjustment, program tracking — with Supabase removed.

**Architecture:** The repo is the brain and the state: the skill moves to `.claude/skills/` (the only place cloud threads load skills from), mutable state lives in `programs/`, `data/` and `plans/` and is committed straight to `main`. Inputs come from Slack (a new stdlib `fetch_slack.py`) and Google Drive (the claude.ai connector, used by the model — no code). Loads come from `calc.py` or the POLP workbook verbatim.

**Tech Stack:** Python 3 standard library only (runtime); pytest (tests); Claude Projects (beta) for hosting.

**Spec:** [`docs/superpowers/specs/2026-10-07-crossfit-coach-claude-project-design.md`](../specs/2026-10-07-crossfit-coach-claude-project-design.md)

## Global Constraints

- Runtime code is **Python standard library only**; the only dev dependency is `pytest>=7`.
- **Never compute a load in the model.** POLP lifts: the workbook's kg verbatim (1 kg rounding). Everything else: `calc.py` (0.5 kg rounding). Never mix them.
- State paths: `programs/<start-date>-<name>.md` (exception: `programs/polp.md`), `data/maxes.json`, `plans/<Monday ISO>.json`. State is committed **directly to `main`** and pushed immediately.
- Timezone for all scheduling and "this week" logic: **AWST (UTC+8, Australia/Perth)**.
- Type-annotate every function signature; docstrings on public functions; no bare `except:`.
- Conventional commits (`feat:`, `fix:`, `refactor:`, `test:`, `docs:`, `chore:`), one logical change per commit, run `python3 -m pytest` before each commit. End every commit message with `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`.
- All work in this plan lands as **one PR** to `main` (spec §11.1).

## File Structure

| Path | Action | Responsibility |
|---|---|---|
| `supabase/`, `.mcp.json` | Delete | Removed backend |
| `skills/crossfit-coach/scripts/tests/test_{supabase_schema,e1rm_parity,analytics_views,scoped_role,focus_plans,focus_status,focus_trigger,neglected_lifts}.py` | Delete | Supabase-only tests |
| `skills/crossfit-coach/scripts/{log_xrm.py,data/xrm_log.json}` | Delete | Log replaced by BTWB |
| `skills/crossfit-coach/` → `.claude/skills/crossfit-coach/` | Move | Cloud threads load skills only from `.claude/skills/` |
| `.claude/skills/crossfit-coach/scripts/conftest.py` | Modify | Drop `db` fixture + `supabase` marker |
| `.claude/skills/crossfit-coach/scripts/cfprog/maxes.py` (+ `__init__.py`) | Modify | Default maxes → repo-root `data/maxes.json`; drop the unwired Sheets provider |
| `data/maxes.json` | Create (from old fixture) | The coach's own max record (state) |
| `.claude/skills/crossfit-coach/scripts/tests/fixtures/maxes.json` | Create (from old fixture) | Frozen maxes so calculator tests don't change when real maxes do |
| `.claude/skills/crossfit-coach/scripts/fetch_slack.py` | Create | Download the week's PDFs from Slack |
| `.claude/skills/crossfit-coach/scripts/tests/test_fetch_slack.py` | Create | Mocked-HTTP tests |
| `programs/README.md`, `programs/polp.md`, `plans/.gitkeep` | Create | State layout + POLP pointer |
| `CLAUDE.md`, `.claude/settings.json` | Create | Repo rules; pre-approved commands for threads |
| `.claude/skills/crossfit-coach/SKILL.md` | Rewrite | Weekly loop, programs, POLP, Slack/Drive |
| `.claude/skills/crossfit-coach/references/{policy.md,athlete-profile.md,drills/README.md,examples/weekly-plan.md}` | Modify | `focus-blocks.md` → `programs/`; maxes → `data/maxes.json`; new script paths |
| `.claude/skills/crossfit-coach/references/focus-blocks.md` | Delete | Replaced by `programs/` |
| `README.md`, `PROJECT_SPEC.md`, `pyproject.toml`, `requirements.txt`, `.gitignore` | Modify | Describe v3; test path; deps; `out/` |
| `docs/superpowers/specs/2026-06-24-*.md`, `docs/superpowers/plans/2026-06-24-*.md` | Modify | "Superseded by v3" banners |
| `docs/runbooks/project-setup.md` | Create | Manual Project setup + dry run |

---

### Task 1: Remove Supabase and the xRM log

**Files:**
- Delete: `supabase/` (whole directory), `.mcp.json`
- Delete: `skills/crossfit-coach/scripts/tests/test_supabase_schema.py`, `test_e1rm_parity.py`, `test_analytics_views.py`, `test_scoped_role.py`, `test_focus_plans.py`, `test_focus_status.py`, `test_focus_trigger.py`, `test_neglected_lifts.py`
- Delete: `skills/crossfit-coach/scripts/log_xrm.py`, `skills/crossfit-coach/scripts/data/xrm_log.json`
- Modify: `skills/crossfit-coach/scripts/conftest.py`
- Modify: `requirements.txt`

**Interfaces:**
- Consumes: nothing.
- Produces: a test suite with no database dependency (`test_calculator.py`, `test_estimate.py`, `test_render_week.py`, `test_targets.py` remain).

- [ ] **Step 1: Record the baseline**

Run: `python3 -m pytest 2>&1 | tail -3`
Expected: passes, with Supabase tests skipped (no local DB). Note the counts.

- [ ] **Step 2: Delete the Supabase backend, its tests and the log**

```bash
git rm -r -q supabase .mcp.json \
  skills/crossfit-coach/scripts/tests/test_supabase_schema.py \
  skills/crossfit-coach/scripts/tests/test_e1rm_parity.py \
  skills/crossfit-coach/scripts/tests/test_analytics_views.py \
  skills/crossfit-coach/scripts/tests/test_scoped_role.py \
  skills/crossfit-coach/scripts/tests/test_focus_plans.py \
  skills/crossfit-coach/scripts/tests/test_focus_status.py \
  skills/crossfit-coach/scripts/tests/test_focus_trigger.py \
  skills/crossfit-coach/scripts/tests/test_neglected_lifts.py \
  skills/crossfit-coach/scripts/log_xrm.py \
  skills/crossfit-coach/scripts/data/xrm_log.json
```

- [ ] **Step 3: Strip the DB fixture from conftest**

Replace the whole of `skills/crossfit-coach/scripts/conftest.py` with:

```python
"""Put the vendored `cfprog` package and the scripts on the path for the test run.

The scripts are invoked as `python3 scripts/<name>.py` and add this directory to
sys.path themselves; this conftest does the same for pytest so the tests under
`scripts/tests/` can `import cfprog` (and the script modules) without an install.
"""

import os
import sys

sys.path.insert(0, os.path.dirname(__file__))
```

- [ ] **Step 4: Drop the Postgres test dependency**

Replace the whole of `requirements.txt` with:

```text
# The skill itself needs nothing beyond the Python standard library — the
# deterministic calculator and the Slack fetcher are pure stdlib, no install.
# The only dependency is the test runner:
#
#   python3 -m pip install pytest
#   python3 -m pytest
pytest>=7
```

- [ ] **Step 5: Verify nothing still references the removed pieces**

Run: `grep -rn -i -E 'supabase|psycopg|log_xrm|xrm_log' --include='*.py' --include='*.toml' --include='*.txt' . | grep -v '^./docs/'`
Expected: no output.

Run: `python3 -m pytest 2>&1 | tail -3`
Expected: all pass, 0 skipped.

- [ ] **Step 6: Commit**

```bash
git add -A
git commit -m "refactor: remove Supabase backend and xRM log

BTWB and the athlete's XRM sheet already hold the training log; the coach
no longer needs a database.

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 2: Move the skill to `.claude/skills/`

**Files:**
- Move: `skills/crossfit-coach/` → `.claude/skills/crossfit-coach/`
- Modify: `pyproject.toml`
- Modify: `.claude/skills/crossfit-coach/references/examples/weekly-plan.md` (render command path)

**Interfaces:**
- Consumes: Task 1's suite.
- Produces: every later path is under `.claude/skills/crossfit-coach/`.

- [ ] **Step 1: Move with history**

```bash
mkdir -p .claude/skills
git mv skills/crossfit-coach .claude/skills/crossfit-coach
rmdir skills 2>/dev/null || true
```

- [ ] **Step 2: Point pytest at the new location**

Replace the whole of `pyproject.toml` with:

```toml
# This repo is a Claude skill (.claude/skills/crossfit-coach) plus the coach's
# state (programs/, data/, plans/), not an installable package. The scripts put
# their vendored `cfprog` package on the path themselves — no build/install step.
# This file only configures the test run.

[tool.pytest.ini_options]
testpaths = [".claude/skills/crossfit-coach/scripts/tests"]
addopts = "-q"
```

- [ ] **Step 3: Fix the render command path in the example**

In `.claude/skills/crossfit-coach/references/examples/weekly-plan.md`, replace
`python3 skills/crossfit-coach/scripts/render_week.py` with
`python3 .claude/skills/crossfit-coach/scripts/render_week.py` (both occurrences in the bash block).

- [ ] **Step 4: Verify the suite still collects from the hidden directory**

Run: `python3 -m pytest 2>&1 | tail -3`
Expected: same pass count as Task 1 Step 5 (not "no tests ran").

Run: `grep -rn 'skills/crossfit-coach' --include='*.md' --include='*.py' --include='*.toml' . | grep -v '\.claude/skills/crossfit-coach' | grep -v '^./docs/superpowers/'`
Expected: matches only in `README.md`, `PROJECT_SPEC.md` and `.claude/skills/crossfit-coach/SKILL.md` (all rewritten in Tasks 6–7).

- [ ] **Step 5: Commit**

```bash
git add -A
git commit -m "refactor: move the skill to .claude/skills so Project threads load it

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 3: Maxes live in repo-root `data/maxes.json`

**Files:**
- Create: `data/maxes.json` (via `git mv` of `.claude/skills/crossfit-coach/scripts/data/maxes.fixture.json`, then edited)
- Create: `.claude/skills/crossfit-coach/scripts/tests/fixtures/maxes.json`
- Modify: `.claude/skills/crossfit-coach/scripts/cfprog/maxes.py`
- Modify: `.claude/skills/crossfit-coach/scripts/cfprog/__init__.py`
- Modify: `.claude/skills/crossfit-coach/scripts/calc.py` (demo banner text only)
- Test: `.claude/skills/crossfit-coach/scripts/tests/test_calculator.py`

**Interfaces:**
- Consumes: `LoadCalculator(maxes: MaxesProvider | None)`, `FixtureMaxesProvider(fixture_path: Path | str | None)` (unchanged signatures).
- Produces: `cfprog.maxes.DEFAULT_MAXES_PATH: Path` = `<repo root>/data/maxes.json`. `GoogleSheetsMaxesProvider` and `SHEET_ID` are **removed** from `cfprog` and its `__all__`.

- [ ] **Step 1: Freeze a test copy of the current maxes**

```bash
mkdir -p .claude/skills/crossfit-coach/scripts/tests/fixtures
cp .claude/skills/crossfit-coach/scripts/data/maxes.fixture.json \
   .claude/skills/crossfit-coach/scripts/tests/fixtures/maxes.json
```

- [ ] **Step 2: Write the failing tests**

In `.claude/skills/crossfit-coach/scripts/tests/test_calculator.py`:

Replace the imports and the `calc` fixture (lines 8–17) with:

```python
from pathlib import Path

import pytest

from cfprog.calculator import LoadCalculator
from cfprog.maxes import DEFAULT_MAXES_PATH, FixtureMaxesProvider
from cfprog.models import Target

REPO_ROOT = Path(__file__).resolve().parents[5]
TEST_MAXES = Path(__file__).resolve().parent / "fixtures" / "maxes.json"


@pytest.fixture(scope="module")
def calc() -> LoadCalculator:
    # Frozen maxes: the real data/maxes.json changes as the athlete gets stronger.
    return LoadCalculator(FixtureMaxesProvider(TEST_MAXES))
```

Replace `test_fixture_documents_sheet_source` and `test_sheets_provider_not_wired_yet` (the last two tests) with:

```python
def test_test_fixture_maxes_are_readable():
    maxes = FixtureMaxesProvider(TEST_MAXES).all_maxes()
    assert maxes["back_squat"] == 165
    assert maxes["power_snatch"] == 82.5


def test_default_maxes_file_is_repo_root_data_maxes_json():
    assert DEFAULT_MAXES_PATH == REPO_ROOT / "data" / "maxes.json"
    assert DEFAULT_MAXES_PATH.is_file()


def test_default_provider_reads_the_coach_maxes_record():
    assert FixtureMaxesProvider().all_maxes()
```

- [ ] **Step 3: Run them to verify they fail**

Run: `python3 -m pytest .claude/skills/crossfit-coach/scripts/tests/test_calculator.py -v`
Expected: collection ERROR — `ImportError: cannot import name 'DEFAULT_MAXES_PATH'`.

- [ ] **Step 4: Move the maxes record to `data/`**

```bash
mkdir -p data
git mv .claude/skills/crossfit-coach/scripts/data/maxes.fixture.json data/maxes.json
rmdir .claude/skills/crossfit-coach/scripts/data 2>/dev/null || true
```

Replace the header keys of `data/maxes.json` (everything before `"maxes"`) so the file begins:

```json
{
  "_comment": "The coach's own record of current 1RMs; calc.py reads it. Source to check when a lift is missing or stale: the athlete's XRM Google Sheet (xrm_sheet_id) — confirm with the athlete before changing a value. POLP lifts don't use this file; their loads come from the POLP workbook.",
  "xrm_sheet_id": "1Q1RlKE9LfTpUYSAqwFWnknJ_g9ftTal1P4eeMBnqY_A",
  "unit": "kg",
  "maxes": {
```

(The `"maxes"` object and closing braces stay exactly as they were.)

- [ ] **Step 5: Point the provider at it and drop the Sheets stub**

In `.claude/skills/crossfit-coach/scripts/cfprog/maxes.py`:

Replace the module docstring and everything from `# Source-of-truth Sheet` through the `_DEFAULT_FIXTURE = ...` line with:

```python
"""Read current 1RMs from the coach's maxes record.

The record is `data/maxes.json` at the repo root — state the coach maintains
(it checks the athlete's XRM Google Sheet and confirms with them before changing
a value). Reads sit behind the `MaxesProvider` interface so the calculator never
cares where maxes come from.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, Protocol, runtime_checkable

# .claude/skills/crossfit-coach/scripts/cfprog/maxes.py -> parents[5] is the repo root.
DEFAULT_MAXES_PATH = Path(__file__).resolve().parents[5] / "data" / "maxes.json"
```

In `FixtureMaxesProvider`, replace its docstring with
`"""Reads maxes from a JSON file shaped like data/maxes.json ({"maxes": {lift: {"one_rm": kg}}})."""`
and `_DEFAULT_FIXTURE` with `DEFAULT_MAXES_PATH` in `__init__`.

Delete the whole `GoogleSheetsMaxesProvider` class.

In `.claude/skills/crossfit-coach/scripts/cfprog/__init__.py`: in the docstring replace the "Maxes read behind an interface…" bullet with
`    - Maxes read behind an interface (cfprog.maxes) from the repo's data/maxes.json.`;
in the `from cfprog.maxes import (...)` block and in `__all__`, replace `GoogleSheetsMaxesProvider` and `SHEET_ID` with `DEFAULT_MAXES_PATH`.

In `.claude/skills/crossfit-coach/scripts/calc.py`, replace the demo banner string
`"Load calculator — demo cases (maxes from fixture mirroring the Sheet)\n"` with
`"Load calculator — demo cases (maxes from data/maxes.json)\n"`.

- [ ] **Step 6: Run the tests to verify they pass**

Run: `python3 -m pytest -v 2>&1 | tail -15`
Expected: all pass, including the three new tests.

Run: `python3 .claude/skills/crossfit-coach/scripts/calc.py front_squat --percent 85`
Expected: `115 kg (85% of 135)`.

- [ ] **Step 7: Commit**

```bash
git add -A
git commit -m "refactor: maxes record moves to data/maxes.json; drop unwired Sheets provider

Calculator tests now use a frozen fixture so updating real maxes can't break them.

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 4: `fetch_slack.py`

**Files:**
- Create: `.claude/skills/crossfit-coach/scripts/fetch_slack.py`
- Test: `.claude/skills/crossfit-coach/scripts/tests/test_fetch_slack.py`

**Interfaces:**
- Consumes: env `SLACK_BOT_TOKEN`; `data/slack_channels.txt` (one channel name per line, optional leading `#`; created in Task 8).
- Produces (CLI): `python3 .claude/skills/crossfit-coach/scripts/fetch_slack.py [--channels-file PATH] [--since YYYY-MM-DD] [--out DIR]`. Stdout: one line per PDF, `channel<TAB>YYYY-MM-DD HH:MM<TAB>path`. Exit `0` all channels had a PDF; `2` config/API/network error; `3` some channels had no PDF since `--since` (others still downloaded; stderr names them).
- Produces (Python): `AWST`, `SlackError`, `SlackFile(channel, name, url, posted)`, `SlackClient(token, opener=None).api(method, **params) -> dict`, `.download(url) -> bytes`, `most_recent_sunday(now) -> datetime`, `channel_ids(client, names) -> dict[str, str]`, `pdfs_since(client, channel, channel_id, since) -> list[SlackFile]`, `fetch(client, channels, since, out_dir) -> tuple[list[tuple[SlackFile, Path]], list[str]]`, `read_channels(path) -> list[str]`, `main(argv=None, opener=None) -> int`.

- [ ] **Step 1: Write the failing tests**

Create `.claude/skills/crossfit-coach/scripts/tests/test_fetch_slack.py`:

```python
"""fetch_slack against a fake Slack: no network, no token."""

import io
import json
import urllib.parse
import urllib.request
from datetime import datetime
from pathlib import Path
from typing import Dict, List

import pytest

from fetch_slack import (
    AWST,
    SlackClient,
    SlackError,
    channel_ids,
    fetch,
    main,
    most_recent_sunday,
)

PDF_BYTES = b"%PDF-1.4 fake"
SUNDAY_10AM = str(datetime(2026, 10, 11, 10, 0, tzinfo=AWST).timestamp())


class FakeSlack:
    """Stands in for urllib.request.urlopen, routing Slack calls to canned data."""

    def __init__(self, channel_pages: List[List[dict]], history: Dict[str, List[dict]]) -> None:
        self.channel_pages = channel_pages
        self.history = history
        self.requests: List[urllib.request.Request] = []

    def __call__(self, req: urllib.request.Request) -> io.BytesIO:
        self.requests.append(req)
        url = urllib.parse.urlparse(req.full_url)
        if url.netloc == "files.slack.com":
            return io.BytesIO(PDF_BYTES)
        params = dict(urllib.parse.parse_qsl(url.query))
        method = url.path.rsplit("/", 1)[-1]
        if method == "conversations.list":
            page = int(params.get("cursor") or 0)
            next_cursor = str(page + 1) if page + 1 < len(self.channel_pages) else ""
            body = {
                "ok": True,
                "channels": self.channel_pages[page],
                "response_metadata": {"next_cursor": next_cursor},
            }
        elif method == "conversations.history":
            body = {
                "ok": True,
                "messages": self.history.get(params["channel"], []),
                "response_metadata": {"next_cursor": ""},
            }
        else:
            body = {"ok": False, "error": "unknown_method"}
        return io.BytesIO(json.dumps(body).encode())


def pdf_message(name: str) -> dict:
    return {
        "ts": SUNDAY_10AM,
        "files": [
            {
                "name": name,
                "filetype": "pdf",
                "url_private_download": f"https://files.slack.com/files-pri/T1-F1/{name}",
            }
        ],
    }


def two_channel_slack() -> FakeSlack:
    return FakeSlack(
        channel_pages=[[{"id": "C1", "name": "performance"}], [{"id": "C2", "name": "comp"}]],
        history={"C1": [pdf_message("week.pdf")], "C2": []},
    )


def test_most_recent_sunday_from_midweek_is_previous_sunday_midnight_awst():
    wednesday = datetime(2026, 10, 14, 9, 30, tzinfo=AWST)
    assert most_recent_sunday(wednesday) == datetime(2026, 10, 11, 0, 0, tzinfo=AWST)


def test_most_recent_sunday_on_a_sunday_is_that_morning():
    sunday_afternoon = datetime(2026, 10, 11, 15, 0, tzinfo=AWST)
    assert most_recent_sunday(sunday_afternoon) == datetime(2026, 10, 11, 0, 0, tzinfo=AWST)


def test_api_sends_bearer_token():
    fake = two_channel_slack()
    SlackClient("xoxb-test", opener=fake).api("conversations.list")
    assert fake.requests[0].get_header("Authorization") == "Bearer xoxb-test"


def test_api_raises_slack_error_when_slack_says_not_ok():
    client = SlackClient("xoxb-test", opener=two_channel_slack())
    with pytest.raises(SlackError, match="unknown_method"):
        client.api("bogus.method")


def test_channel_ids_follows_pagination():
    client = SlackClient("xoxb-test", opener=two_channel_slack())
    assert channel_ids(client, ["comp", "performance"]) == {"comp": "C2", "performance": "C1"}


def test_channel_ids_names_the_missing_channels():
    client = SlackClient("xoxb-test", opener=two_channel_slack())
    with pytest.raises(SlackError, match="endurance"):
        channel_ids(client, ["performance", "endurance"])


def test_fetch_downloads_only_pdfs_prefixed_by_channel(tmp_path: Path):
    fake = FakeSlack(
        channel_pages=[[{"id": "C1", "name": "performance"}]],
        history={
            "C1": [
                pdf_message("week.pdf"),
                {
                    "ts": SUNDAY_10AM,
                    "files": [
                        {
                            "name": "photo.jpg",
                            "filetype": "jpg",
                            "url_private_download": "https://files.slack.com/x/photo.jpg",
                        }
                    ],
                },
                {"ts": SUNDAY_10AM, "text": "no attachment"},
            ]
        },
    )
    since = datetime(2026, 10, 11, 0, 0, tzinfo=AWST)
    saved, empty = fetch(SlackClient("xoxb-test", opener=fake), ["performance"], since, tmp_path)
    assert [path.name for _, path in saved] == ["performance-week.pdf"]
    assert (tmp_path / "performance-week.pdf").read_bytes() == PDF_BYTES
    assert empty == []


def test_main_without_token_exits_2(monkeypatch: pytest.MonkeyPatch, tmp_path: Path, capsys):
    monkeypatch.delenv("SLACK_BOT_TOKEN", raising=False)
    channels = tmp_path / "channels.txt"
    channels.write_text("performance\n")
    assert main(["--channels-file", str(channels), "--out", str(tmp_path)]) == 2
    assert "SLACK_BOT_TOKEN" in capsys.readouterr().err


def test_main_reports_channel_without_pdf_and_exits_3(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, capsys
):
    monkeypatch.setenv("SLACK_BOT_TOKEN", "xoxb-test")
    channels = tmp_path / "channels.txt"
    channels.write_text("performance\n#comp\n\n")
    out = tmp_path / "out"
    argv = ["--channels-file", str(channels), "--since", "2026-10-11", "--out", str(out)]
    assert main(argv, opener=two_channel_slack()) == 3
    captured = capsys.readouterr()
    assert "performance-week.pdf" in captured.out
    assert "no PDF in #comp" in captured.err


def test_main_with_unknown_channel_exits_2(monkeypatch: pytest.MonkeyPatch, tmp_path: Path, capsys):
    monkeypatch.setenv("SLACK_BOT_TOKEN", "xoxb-test")
    channels = tmp_path / "channels.txt"
    channels.write_text("endurance\n")
    assert main(["--channels-file", str(channels), "--out", str(tmp_path)], opener=two_channel_slack()) == 2
    assert "endurance" in capsys.readouterr().err
```

- [ ] **Step 2: Run them to verify they fail**

Run: `python3 -m pytest .claude/skills/crossfit-coach/scripts/tests/test_fetch_slack.py -v`
Expected: collection ERROR — `ModuleNotFoundError: No module named 'fetch_slack'`.

- [ ] **Step 3: Write the implementation**

Create `.claude/skills/crossfit-coach/scripts/fetch_slack.py`:

```python
"""Fetch the week's programming PDFs from the gym's Slack channels.

    python3 fetch_slack.py                              # since last Sunday 00:00 AWST
    python3 fetch_slack.py --since 2026-10-11 --out /tmp/week

Channels come from data/slack_channels.txt (one name per line, '#' optional).
Needs SLACK_BOT_TOKEN for a bot with scopes channels:read, groups:read,
channels:history, groups:history and files:read, invited to each channel.

Prints one tab-separated line per downloaded PDF: channel, posted (AWST), path.
Exit codes: 0 every channel had a PDF; 2 configuration, API or network error;
3 some channels had no PDF since --since (the others were still downloaded).
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import tempfile
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple

API_BASE = "https://slack.com/api/"
AWST = timezone(timedelta(hours=8), "AWST")
# .claude/skills/crossfit-coach/scripts/fetch_slack.py -> parents[4] is the repo root.
DEFAULT_CHANNELS_FILE = Path(__file__).resolve().parents[4] / "data" / "slack_channels.txt"

Opener = Callable[[urllib.request.Request], Any]


class SlackError(RuntimeError):
    """Slack answered ok=false, or a configured channel can't be found."""


@dataclass(frozen=True)
class SlackFile:
    """A PDF shared in a channel."""

    channel: str
    name: str
    url: str
    posted: datetime


class SlackClient:
    """Minimal Slack Web API client: GET requests with a bearer token."""

    def __init__(self, token: str, opener: Optional[Opener] = None) -> None:
        self._token = token
        self._opener: Opener = opener or urllib.request.urlopen

    def _get(self, url: str) -> bytes:
        req = urllib.request.Request(url, headers={"Authorization": f"Bearer {self._token}"})
        with self._opener(req) as resp:
            return resp.read()

    def api(self, method: str, **params: str) -> Dict[str, Any]:
        """Call a Web API method; raise SlackError unless Slack says ok."""
        url = API_BASE + method + "?" + urllib.parse.urlencode(params)
        data = json.loads(self._get(url))
        if not data.get("ok"):
            raise SlackError(f"{method}: {data.get('error', 'unknown error')}")
        return data

    def download(self, url: str) -> bytes:
        """Download a private file URL (url_private_download)."""
        return self._get(url)


def most_recent_sunday(now: datetime) -> datetime:
    """Midnight AWST at the start of the most recent Sunday (today, if Sunday)."""
    local = now.astimezone(AWST)
    days_back = (local.weekday() - 6) % 7
    start = local - timedelta(days=days_back)
    return start.replace(hour=0, minute=0, second=0, microsecond=0)


def channel_ids(client: SlackClient, names: List[str]) -> Dict[str, str]:
    """Map channel names to IDs; raise SlackError naming any that are missing."""
    found: Dict[str, str] = {}
    cursor = ""
    while True:
        params = {"types": "public_channel,private_channel", "exclude_archived": "true", "limit": "1000"}
        if cursor:
            params["cursor"] = cursor
        data = client.api("conversations.list", **params)
        for channel in data.get("channels", []):
            found[channel["name"]] = channel["id"]
        cursor = data.get("response_metadata", {}).get("next_cursor", "")
        if not cursor:
            break
    missing = [name for name in names if name not in found]
    if missing:
        raise SlackError(f"channel(s) not found or bot not invited: {', '.join(missing)}")
    return {name: found[name] for name in names}


def pdfs_since(client: SlackClient, channel: str, channel_id: str, since: datetime) -> List[SlackFile]:
    """Every PDF shared in the channel at or after `since`, oldest first."""
    files: List[SlackFile] = []
    cursor = ""
    while True:
        params = {"channel": channel_id, "oldest": f"{since.timestamp():.6f}", "limit": "200"}
        if cursor:
            params["cursor"] = cursor
        data = client.api("conversations.history", **params)
        for message in data.get("messages", []):
            posted = datetime.fromtimestamp(float(message["ts"]), AWST)
            for shared in message.get("files", []):
                if shared.get("filetype") == "pdf":
                    files.append(SlackFile(channel, shared["name"], shared["url_private_download"], posted))
        cursor = data.get("response_metadata", {}).get("next_cursor", "")
        if not cursor:
            break
    return sorted(files, key=lambda f: f.posted)


def fetch(
    client: SlackClient, channels: List[str], since: datetime, out_dir: Path
) -> Tuple[List[Tuple[SlackFile, Path]], List[str]]:
    """Download each channel's PDFs into out_dir as '<channel>-<name>'.

    Returns (saved files with their paths, channels that had no PDF).
    """
    out_dir.mkdir(parents=True, exist_ok=True)
    ids = channel_ids(client, channels)
    saved: List[Tuple[SlackFile, Path]] = []
    empty: List[str] = []
    for name in channels:
        pdfs = pdfs_since(client, name, ids[name], since)
        if not pdfs:
            empty.append(name)
            continue
        for pdf in pdfs:
            path = out_dir / f"{name}-{pdf.name}"
            path.write_bytes(client.download(pdf.url))
            saved.append((pdf, path))
    return saved, empty


def read_channels(path: Path) -> List[str]:
    """Channel names from a file: one per line, blank lines ignored, '#' optional."""
    names = [line.strip().lstrip("#") for line in path.read_text(encoding="utf-8").splitlines()]
    return [name for name in names if name]


def main(argv: Optional[List[str]] = None, opener: Optional[Opener] = None) -> int:
    """CLI entry point; see the module docstring for exit codes."""
    parser = argparse.ArgumentParser(description="Download this week's programming PDFs from Slack.")
    parser.add_argument("--channels-file", default=str(DEFAULT_CHANNELS_FILE))
    parser.add_argument("--since", help="YYYY-MM-DD (midnight AWST); default: most recent Sunday")
    parser.add_argument("--out", help="output directory; default: a new temp directory")
    args = parser.parse_args(argv)

    token = os.environ.get("SLACK_BOT_TOKEN")
    if not token:
        print("SLACK_BOT_TOKEN is not set (add it to the Project's cloud environment).", file=sys.stderr)
        return 2
    try:
        channels = read_channels(Path(args.channels_file))
    except FileNotFoundError:
        print(f"channels file not found: {args.channels_file}", file=sys.stderr)
        return 2
    if not channels:
        print(f"no channels listed in {args.channels_file}", file=sys.stderr)
        return 2

    if args.since:
        since = datetime.strptime(args.since, "%Y-%m-%d").replace(tzinfo=AWST)
    else:
        since = most_recent_sunday(datetime.now(AWST))
    out_dir = Path(args.out) if args.out else Path(tempfile.mkdtemp(prefix="slack-pdfs-"))

    try:
        saved, empty = fetch(SlackClient(token, opener), channels, since, out_dir)
    except SlackError as exc:
        print(f"slack error: {exc}", file=sys.stderr)
        return 2
    except urllib.error.URLError as exc:
        print(f"network error reaching Slack (is slack.com allowed?): {exc}", file=sys.stderr)
        return 2

    for pdf, path in saved:
        print(f"{pdf.channel}\t{pdf.posted:%Y-%m-%d %H:%M}\t{path}")
    for name in empty:
        print(f"no PDF in #{name} since {since:%Y-%m-%d %H:%M} AWST", file=sys.stderr)
    return 3 if empty else 0


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `python3 -m pytest .claude/skills/crossfit-coach/scripts/tests/test_fetch_slack.py -v`
Expected: 10 passed.

Run: `python3 -m pytest 2>&1 | tail -3`
Expected: all pass.

- [ ] **Step 5: Commit**

```bash
git add .claude/skills/crossfit-coach/scripts/fetch_slack.py \
        .claude/skills/crossfit-coach/scripts/tests/test_fetch_slack.py
git commit -m "feat: fetch_slack.py downloads the week's programming PDFs from Slack

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 5: State layout, repo rules, thread permissions

**Files:**
- Create: `programs/README.md`, `programs/polp.md`, `plans/.gitkeep`
- Create: `CLAUDE.md`
- Create: `.claude/settings.json`
- Modify: `.gitignore`

**Interfaces:**
- Consumes: `data/maxes.json` (Task 3), `fetch_slack.py` (Task 4).
- Produces: the program-file format that SKILL.md (Task 6) refers to; the POLP workbook ID in `programs/polp.md`.

- [ ] **Step 1: Write `programs/README.md`**

````markdown
# programs/

One file per personal program the coach tracks, named `<start-date>-<name>.md`
(the athlete's own start date, e.g. `2026-10-13-rowing-12wk.md`), so repeat
blocks never collide. Finished programs stay here with `status: done`.
`polp.md` is the exception: the POLP workbook tracks its own position.

The coach reads these as plain markdown (no parser) and commits every change
straight to `main`.

## Format

```markdown
---
name: Rowing 12-wk
status: active            # active | done
started: 2026-10-13       # the athlete's own start, not the channel's
source: Endurance channel PDF, Sep 2026 (original in the Project Library)
current: W1 S1            # the next session to do
sessions_per_week: 2
---

## Sessions

### W1 S1
<session text, verbatim from the source>

### W1 S2
...

## Log
- 2026-10-19 — W1 S1, S2 done. "Felt easy." → current: W2 S1
```

- `current` always names the **next** session to do.
- `## Log` is append-only: one line per check-in or mid-week report.
- A program the coach designs (e.g. a pressing block) uses the same format;
  `source:` says "Designed with the coach, <date>" and loads are written as
  calc.py targets (`--percent`, `--rep-max`, `--rpe`), never as kg.
````

- [ ] **Step 2: Write `programs/polp.md`**

```markdown
---
name: POLP (Jason's POLP Program)
status: active
workbook_file_id: 1hjiWJ5HDh--huMb31r1pXeySRun7pdar
lifts: back_squat, front_squat, bench_press, deadlift, press
---

# POLP

The gym runs POLP inside class time ("Bench Press — POLP programming"). The
athlete logs each session in the workbook; the workbook does all load math.

- Read the workbook with the Google Drive connector (`read_file_content` on
  `workbook_file_id`). One tab per lift; each tab is one table, one row per week.
- **Next session for a lift** = the first row whose `S1 reps` is blank. Use that
  row's `Sets × Reps`, `B1 kg`, `B2 kg`, `S1 kg`, `S2 kg`, `S3 kg` **verbatim**
  (the workbook rounds to 1 kg; never re-derive them with calc.py).
- **Last result** = the row above it: `Result` (PASS/FAIL), `Fails at this
  weight`, `Action`, `Notes`.
- Deadlift ramps (sets climb to the top set); the other lifts are sets across.
- A cycle ends with a deload row and a 1RM test row. After a test the athlete
  starts a fresh workbook copy: ask for the new file ID and update this file.

## Notes
- 2026-10-07 — Press wk1 note in workbook: "This was way too hard..."; Setup
  notes shoulder niggles on the press 1RM. Factor into any extra pressing.
```

- [ ] **Step 3: Keep `plans/` in git**

```bash
mkdir -p plans && touch plans/.gitkeep
```

- [ ] **Step 4: Write `CLAUDE.md`**

```markdown
# CF_Programming — repo rules

This repo is the brain and the state of a personal CrossFit coach that runs as a
Claude Project. The playbook is `.claude/skills/crossfit-coach/SKILL.md`; follow it.

## State: commit straight to main

`programs/`, `data/` and `plans/` are the coach's state. After **every** change to
them, immediately:

    git add <the changed files>
    git commit -m "chore(state): <what changed>"
    git push origin main

Never put state on a branch or in a pull request. Never batch state changes to the
end of a session — a cloud sandbox can resume from a fresh clone and lose
uncommitted work. If the push fails, say so plainly and don't carry on as if saved.

## Code: branch and PR

Changes to the skill, references or scripts go on a branch with a pull request.
Run `python3 -m pytest` first. Runtime code is Python standard library only.

## Never

- Compute a load in your head: `calc.py`, or the POLP workbook verbatim.
- Invent a max: `data/maxes.json`, else check the XRM sheet and confirm with the athlete.
- Write to the athlete's Google Sheets.
```

- [ ] **Step 5: Write `.claude/settings.json`**

```json
{
  "permissions": {
    "allow": [
      "Bash(python3 .claude/skills/crossfit-coach/scripts/calc.py:*)",
      "Bash(python3 .claude/skills/crossfit-coach/scripts/estimate_1rm.py:*)",
      "Bash(python3 .claude/skills/crossfit-coach/scripts/render_week.py:*)",
      "Bash(python3 .claude/skills/crossfit-coach/scripts/fetch_slack.py:*)",
      "Bash(python3 -m pytest:*)",
      "Bash(git add:*)",
      "Bash(git commit:*)",
      "Bash(git push origin main)",
      "Bash(git pull:*)"
    ]
  }
}
```

- [ ] **Step 6: Ignore rendered output**

Append to `.gitignore`:

```text

# Rendered weekly HTML (delivered to the Project Library, not committed)
out/
```

- [ ] **Step 7: Verify**

Run: `python3 -m json.tool .claude/settings.json > /dev/null && echo ok`
Expected: `ok`.

Run: `python3 -m pytest 2>&1 | tail -3`
Expected: all pass.

- [ ] **Step 8: Commit**

```bash
git add programs plans CLAUDE.md .claude/settings.json .gitignore
git commit -m "feat: state layout (programs/, plans/), repo rules and thread permissions

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 6: Rewrite SKILL.md around the weekly loop; retire focus-blocks.md

**Files:**
- Rewrite: `.claude/skills/crossfit-coach/SKILL.md`
- Delete: `.claude/skills/crossfit-coach/references/focus-blocks.md`
- Modify: `.claude/skills/crossfit-coach/references/policy.md` (§4 last bullet; "Current focus" bullets)
- Modify: `.claude/skills/crossfit-coach/references/drills/README.md` (intro; "reads the week" bullet)
- Modify: `.claude/skills/crossfit-coach/references/athlete-profile.md` ("Current maxes" paragraph)

**Interfaces:**
- Consumes: paths and formats from Tasks 2–5 (`calc.py`, `estimate_1rm.py`, `render_week.py`, `fetch_slack.py` exit codes, `programs/` format, `programs/polp.md`, `data/maxes.json`).
- Produces: the playbook every project thread follows.

- [ ] **Step 1: Capture the sections kept verbatim**

Before rewriting, copy from the current SKILL.md, unchanged, for reuse below:
- **§3 body** — from `When the athlete reports how they feel` through `proactively move or de-load the clashing personal work for the rest of the week.`
- **The whole `## Changelog` section** (1.2.0, 1.1.0, 1.0.0 entries).

- [ ] **Step 2: Write the new SKILL.md**

Replace the whole file with the content below, pasting the two captured pieces where marked `<<…>>` (exact text, no edits):

````markdown
---
name: crossfit-coach
description: >
  Personal CrossFit coach running as a Claude Project. Use for the weekly
  planning thread ("Week of <Monday>", started by the Sunday routine), the
  athlete's check-in, mid-week questions ("what's today?", "I'm smashed, adjust
  Thursday"), reporting sessions done in a self-paced program, reporting a heavy
  set, or designing / updating a program block. Fetches the gym's programming
  PDFs from Slack, reads the POLP workbook from Google Drive, tracks programs in
  programs/, and calls a deterministic calculator for every load (never does the
  math itself).
version: 2.0.0
---

# CrossFit Coach

You are the athlete's coach. Each week you merge the gym's class programming with
the athlete's personal programs — each on its own clock — into one tiered,
load-calculated week, check in on how last week went, and adjust mid-week. You
supply **judgment**; scripts and the POLP workbook supply **arithmetic**.

## §0. Prime directive — you never do load math

- **POLP lifts** (back squat, front squat, bench press, deadlift, press): use the
  POLP workbook's kg **verbatim** (§4.2). Never recompute them.
- **Everything else** (class %-work, Weightlifting, designed programs): run the
  calculator and paste its line verbatim:

  ```
  python3 .claude/skills/crossfit-coach/scripts/calc.py <lift> --percent 85
  python3 .claude/skills/crossfit-coach/scripts/calc.py <lift> --rep-max 3
  python3 .claude/skills/crossfit-coach/scripts/calc.py <lift> --rpe 8 --reps 5
  ```

- If a lift isn't in `data/maxes.json`, the calculator errors: follow §6, never
  invent a max.

## §1. Where things live

| What | Where | How to read / write |
|---|---|---|
| Policy (tiers, autoregulation, deconfliction, menus) | `references/policy.md` | Read; apply as written |
| Diagnostic, goals, lift ratios | `references/athlete-profile.md` | Read |
| Usual training week | `references/availability.md` | Read; the athlete says when a week differs |
| Drill / program templates | `references/drills/` | Read when designing a program |
| Personal programs + where each is up to | `programs/*.md` (`status: active`) | Read; update + commit (§2) |
| POLP position and loads | POLP workbook in Drive (ID in `programs/polp.md`) | Google Drive connector, read only |
| Current maxes | `data/maxes.json` | `calc.py` reads it; update + commit (§6) |
| Last week's confirmed plan | `plans/<Monday>.json` | Read; write + commit (§3 step 5) |
| Class programming | Slack PDFs | `fetch_slack.py` (§3 step 1) |
| Training log | BTWB | Not reachable — ask the athlete |

## §2. Commit every state change immediately

After any change to `programs/`, `data/` or `plans/`:

```
git add <changed files>
git commit -m "chore(state): <what changed>"
git push origin main
```

Straight to `main`, never a branch or PR, never batched. If the push fails, tell
the athlete and stop treating the change as saved.

## §3. The weekly loop

The Sunday routine starts a thread named **"Week of <Monday ISO>"**. The athlete
sends every message for that week to this thread.

### Step 1 — Gather (no questions yet)

1. `git pull` so you have the latest state.
2. Fetch the programming:

   ```
   python3 .claude/skills/crossfit-coach/scripts/fetch_slack.py --out out/pdfs
   ```

   - Exit `0`: read every listed PDF. Deliver them to the Library as outputs.
   - Exit `3`: some channels have nothing yet. Tell the athlete which, and wait
     for "go" (then re-run). Don't plan from partial programming unless they
     say to.
   - Exit `2`: configuration / network problem. Quote the error and stop.
3. Read the POLP workbook (§4.2): each lift's last logged row and next row.
4. Read every `programs/*.md` with `status: active`, and last week's
   `plans/<previous Monday>.json` if it exists.
5. If there is **no active program** besides POLP, ask the athlete what the
   priority is before fitting personal work. Don't plan personal work in a vacuum.

### Step 2 — Draft the week

Assume last week went as planned. Then, in this order:

1. **Evaluate the class week.** Map the programming onto `availability.md`. Use
   the gym's stream names (Performance, Fitness, Comp, Weightlifting, Endurance —
   never "CrossFit"). Tag each class session by primary stimulus
   (`heavy_squat | heavy_pull | press | gymnastics | engine | mixed`), read the
   load picture (what the class already taxes hard, where the fresh days are), and
   tier it (policy §1; the class metcon is CRUISE).
2. **Fit the programs.** POLP rows go into the class slots that name POLP
   ("Bench Press — POLP programming"). Each active self-paced program contributes
   its next `sessions_per_week` sessions from `current:` onward.
3. **Deconflict and triage** (policy §3). No same stimulus on consecutive days;
   strength before conditioning; keep rest days rest. When the week is full, apply
   the triage order (PROTECT top sets → class → accessory → skill). **Record every
   placement, move or drop** as a decision.
4. Build the Mon–Sun × AM/PM grid (markdown table) and the decisions list.

### Step 3 — One stop: check-in + proposal

Send **one** message, then wait:

> **Last week, as I have it:** POLP — <lift: result per the workbook, or "not
> logged">. <Program>: <sessions> assumed done. <Anything from last week's plan
> not covered above.>
>
> **Proposed week:** <grid> <decisions>
>
> **Anything missed, how did the week feel, and is this plan OK?**

### Step 4 — Apply the reply

1. Update each program's `current:` and append a `## Log` line (date, what was
   done or missed, the athlete's words). Update `data/maxes.json` only via §6.
   Commit (§2).
2. If the reply changes the plan (missed sessions, a niggle, a different week),
   re-draft (Step 2) and send the proposal again. Otherwise go to Step 5.

### Step 5 — Emit

1. Resolve every load: POLP rows verbatim; everything else via `calc.py`.
2. Write the plan spec (shape: `references/examples/weekly-plan.json`, including
   `week_start` and the `decisions` list; class workout text **verbatim** from the
   PDFs; the athlete's own blocks `"accent": "lim"`) to `plans/<Monday>.json`.
   Commit (§2).
3. Render and deliver the HTML to the Library:

   ```
   python3 .claude/skills/crossfit-coach/scripts/render_week.py plans/<Monday>.json -o "out/Gym Program - Week starting <Monday>.html"
   ```

4. Reply with a short summary: what to push / cruise / skip, plus the file name.

## §4. Programs

### §4.1 Self-paced programs (`programs/<start-date>-<name>.md`)

Format: `programs/README.md`. `current:` is always the next session to do.

- **Session done** ("row W1 S2 done, felt easy"): advance `current:`, append a
  log line, commit.
- **Session missed:** leave `current:` where it is; log it; it carries into next
  week's plan.
- **Starting a program from a channel PDF** (e.g. a block the athlete is weeks
  behind on): transcribe every session verbatim into a new file, start date = the
  athlete's chosen start, `current: W1 S1`. Commit. Deliver the source PDF to the
  Library.
- **Designing a program with the athlete** (e.g. a 4–8 week pressing block):
  start from `references/drills/` templates and policy §5 menus; write loads as
  calc.py targets, never kg; confirm the block with the athlete before saving.
- **Finishing:** set `status: done`, add a closing log line, commit, and ask
  what replaces it.

### §4.2 POLP (`programs/polp.md`)

Read the workbook ID from `programs/polp.md` and follow its reading rules. When
the athlete reports a POLP session, remind them to log it in the workbook — it is
the source of truth for POLP position; you never write to it.

## §5. Mid-week autoregulation ("I'm beaten up, adjust today")

<<paste the captured §3 body here verbatim>>

Re-emit the affected day(s) as a short chat message (template:
`references/examples/daily-adjust.md`). Re-render the HTML only if the athlete
asks for it.

## §6. Maxes and heavy sets

- `data/maxes.json` is your record. When a lift you need is missing or looks
  stale, read the XRM sheet (`xrm_sheet_id` in the file) with the Google Drive
  connector, **confirm the number with the athlete**, then write it and commit.
- When the athlete reports a heavy set (e.g. "front-squat triple at 122"):

  ```
  python3 .claude/skills/crossfit-coach/scripts/estimate_1rm.py --lift front_squat --weight 122 --reps 3 [--rpe N]
  ```

  Report the estimate against the current max. If it beats it, ask whether to
  update `data/maxes.json` (and suggest they update their XRM sheet). Commit if
  they say yes.

## §7. Hard constraints

- No mental load arithmetic (§0).
- Maxes never invented (§6).
- Apply the policy as written; if a situation isn't covered, reason from
  `athlete-profile.md` and say so.
- Keep rest days rest unless the athlete opts into open gym.
- Record any readiness override the athlete makes against a wearable score.
- If Slack, Drive or a file you need is unavailable, say exactly what's missing
  and wait. Don't guess or substitute.

## §8. Output conventions

Canonical templates: `references/examples/weekly-plan.md` and
`references/examples/daily-adjust.md`; load-line format `144.5 kg (87.5% of 165)`
(POLP lines: `<kg> kg (POLP wk<N>, <sets × reps>)`). The athlete reads on a phone:
short and skimmable, lead with push / cruise / skip. The renderer is presentation
only and does no math.

---

## Changelog

### 2.0.0
- **Re-platformed as a Claude Project.** The skill moved to `.claude/skills/` so
  cloud threads load it. One thread per training week, started by a Sunday 15:00
  AWST routine: gather (Slack PDFs via `fetch_slack.py`, POLP workbook via Drive,
  `programs/`, last plan) → draft → one check-in + proposal stop → apply →
  emit. Supabase, the xRM log and `focus-blocks.md` are gone; personal programs
  live in `programs/` with their own `current:` pointers, maxes in
  `data/maxes.json`, confirmed plans in `plans/`, all committed straight to main.
  POLP loads come from the workbook verbatim.

<<paste the captured 1.2.0, 1.1.0 and 1.0.0 changelog entries here verbatim>>
````

- [ ] **Step 3: Retire focus-blocks.md and repoint the references**

```bash
git rm -q .claude/skills/crossfit-coach/references/focus-blocks.md
```

In `.claude/skills/crossfit-coach/references/policy.md`:
- Replace `session template you slot around the class plan. The athlete's current blocks\n  live in \`references/focus-blocks.md\`.` with `session template you slot around the class plan. The athlete's current programs\n  live in \`programs/\` at the repo root (see \`programs/README.md\`).`
- Replace the bullet starting `- Each block in \`references/focus-blocks.md\` names a drill/program file in` (through `(e.g. "week 3 of 6").`) with:
  `- Each active program in \`programs/\` carries its own sessions and a \`current:\`\n  pointer to the next one; templates for new programs live in \`references/drills/\`.`

In `.claude/skills/crossfit-coach/references/drills/README.md`:
- Replace the intro paragraph (from `These Markdown files are the` through `not by hand-typing drills each week.`) with:
  `These Markdown files are **templates** for personal programs. When the athlete\nstarts one, the coach copies the sessions into a dated file in \`programs/\` (see\n\`programs/README.md\`), which then tracks where they're up to.`
- Replace the bullet `- The assistant reads the week stated for the block in \`../focus-blocks.md\` (bump\n  it as the weeks pass, or infer it from the date / training log).` with
  `- Position is tracked in the program's file in \`programs/\`, not here.`

In `.claude/skills/crossfit-coach/references/athlete-profile.md`, replace the paragraph under `## Current maxes — single source of truth` (from `Current 1RMs live in` through `not this document.`) with:

```markdown
Current 1RMs live in **`data/maxes.json`** at the repo root — the coach's record,
which the calculator reads. **Do not duplicate or hardcode maxes in this file.** When
the athlete hits a new max, the coach confirms it and updates `data/maxes.json` (and
the athlete updates their XRM sheet) — not this document. POLP lifts take their loads
from the POLP workbook instead.
```

- [ ] **Step 4: Verify no stale references remain in the skill**

Run: `grep -rn -i -E 'focus-blocks|supabase|log_xrm|xrm_log|maxes\.fixture|python3 skills/' .claude/skills`
Expected: only matches inside the `## Changelog` 1.x entries of SKILL.md.

Run: `python3 -m pytest 2>&1 | tail -3`
Expected: all pass.

- [ ] **Step 5: Commit**

```bash
git add -A
git commit -m "feat: SKILL.md 2.0 — weekly Project loop, programs/, POLP workbook, Slack fetch

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 7: Top-level docs describe v3

**Files:**
- Rewrite: `README.md`
- Modify: `PROJECT_SPEC.md` (banner only)
- Modify: `docs/superpowers/specs/2026-06-24-crossfit-coach-plugin-design.md`, `docs/superpowers/plans/2026-06-24-crossfit-coach-supabase-foundation.md`, `docs/superpowers/plans/2026-06-24-crossfit-coach-planner-integration.md`, `docs/superpowers/plans/2026-06-24-crossfit-coach-chat-project.md` (banner only)

**Interfaces:**
- Consumes: final layout from Tasks 1–6.
- Produces: nothing code-facing.

- [ ] **Step 1: Rewrite README.md**

Replace the whole file with:

````markdown
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
````

- [ ] **Step 2: Banner PROJECT_SPEC.md**

Insert directly under the `# CrossFit Programming & Autoregulation System — Project Spec` heading:

```markdown
> **⚠️ Architecture update (2026-10): now a Claude Project.** See
> [`docs/superpowers/specs/2026-10-07-crossfit-coach-claude-project-design.md`](docs/superpowers/specs/2026-10-07-crossfit-coach-claude-project-design.md).
> The skill lives in `.claude/skills/crossfit-coach/`. The athlete profile and policy
> rationale below remain valid; everything about architecture is history.
```

- [ ] **Step 3: Banner the superseded design and plans**

Insert directly under the first `#` heading of each of the four 2026-06-24 files:

```markdown
> **Superseded (2026-10-07)** by the v3 design,
> [`2026-10-07-crossfit-coach-claude-project-design.md`](../specs/2026-10-07-crossfit-coach-claude-project-design.md).
> Supabase and the two-surface split were removed. Kept for history.
```

(For the spec file itself, which lives in `specs/`, the link is `2026-10-07-crossfit-coach-claude-project-design.md` with no `../specs/` prefix.)

- [ ] **Step 4: Verify links resolve**

Run: `for f in README.md PROJECT_SPEC.md; do grep -o 'docs/superpowers/specs/[^)]*' $f | xargs -I{} test -f {} && echo "$f ok"; done`
Expected: `README.md ok` and `PROJECT_SPEC.md ok`.

- [ ] **Step 5: Commit**

```bash
git add README.md PROJECT_SPEC.md docs/superpowers
git commit -m "docs: describe the v3 Claude Project coach; mark v2 docs superseded

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 8: Project setup runbook (manual, with the athlete)

**Files:**
- Create: `docs/runbooks/project-setup.md`
- Create (during the runbook): `data/slack_channels.txt`

**Interfaces:**
- Consumes: everything above, merged to `main`.
- Produces: a working Project. Steps 3 onward are **done by the athlete in the Claude / Slack / GitHub UIs**; each has a verification check.

- [ ] **Step 1: Write the runbook**

Create `docs/runbooks/project-setup.md`:

````markdown
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
- Ask: "Create a routine: every Sunday at 15:00 Australia/Perth, start a thread
  named 'Week of <next Monday>' that runs the crossfit-coach weekly loop." Then run it
  once now from the **Routines** tab.
- **Check all of:**
  - [ ] PDFs fetched (or a clear "not posted yet" wait).
  - [ ] One message with last week + proposed week + the check-in question.
  - [ ] After your reply, `chore(state)` commits land on `main` (not a branch / PR).
  - [ ] The HTML opens from the **Library on the mobile app**. If it doesn't: change
        SKILL.md §3 Step 5 to also commit the HTML under `plans/`, and open it from
        GitHub instead.
  - [ ] A mid-week message in the thread ("what's today?") gets the right day.
- After a month: **Project settings → Usage**; lower thread effort if it's heavy.
````

- [ ] **Step 2: Commit the runbook**

```bash
mkdir -p docs/runbooks
git add docs/runbooks/project-setup.md
git commit -m "docs: Project setup runbook and dry-run checklist

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

- [ ] **Step 3: Open the PR**

Push the branch and open one PR titled `feat: CrossFit coach as a single Claude Project (v3)` whose body links the spec and this plan, lists Tasks 1–7 as the code changes, and states that runbook steps 1–6 are manual and follow merge.

- [ ] **Step 4: After merge — walk the athlete through runbook steps 1–6**, ticking each check.
