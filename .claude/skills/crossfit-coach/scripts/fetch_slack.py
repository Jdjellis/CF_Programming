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
HTTP_TIMEOUT_SECONDS = 30
AWST = timezone(timedelta(hours=8), "AWST")
# .claude/skills/crossfit-coach/scripts/fetch_slack.py -> parents[4] is the repo root.
DEFAULT_CHANNELS_FILE = Path(__file__).resolve().parents[4] / "data" / "slack_channels.txt"

Opener = Callable[..., Any]


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
        with self._opener(req, timeout=HTTP_TIMEOUT_SECONDS) as resp:
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
        data = self._get(url)
        if not data.startswith(b"%PDF"):
            raise SlackError(
                "downloaded file is not a PDF; the bot token may lack the files:read scope"
            )
        return data


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
                if shared.get("filetype") != "pdf":
                    continue
                name = shared.get("name")
                url = shared.get("url_private_download")
                if not name or not url:
                    continue
                files.append(SlackFile(channel, name, url, posted))
        cursor = data.get("response_metadata", {}).get("next_cursor", "")
        if not cursor:
            break
    return sorted(files, key=lambda f: f.posted)


def unique_path(out_dir: Path, filename: str) -> Path:
    """out_dir/filename, or with -2, -3, ... before the suffix if that name is taken."""
    candidate = out_dir / filename
    stem, suffix = candidate.stem, candidate.suffix
    counter = 2
    while candidate.exists():
        candidate = out_dir / f"{stem}-{counter}{suffix}"
        counter += 1
    return candidate


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
            path = unique_path(out_dir, f"{name}-{Path(pdf.name).name}")
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
        try:
            since = datetime.strptime(args.since, "%Y-%m-%d").replace(tzinfo=AWST)
        except ValueError:
            print(f"invalid --since {args.since!r}: expected YYYY-MM-DD", file=sys.stderr)
            return 2
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
    except TimeoutError as exc:
        print(f"timed out talking to Slack: {exc}", file=sys.stderr)
        return 2
    except json.JSONDecodeError as exc:
        print(f"unexpected non-JSON response from Slack: {exc}", file=sys.stderr)
        return 2
    except OSError as exc:
        print(f"file error: {exc}", file=sys.stderr)
        return 2

    for pdf, path in saved:
        print(f"{pdf.channel}\t{pdf.posted:%Y-%m-%d %H:%M}\t{path}")
    for name in empty:
        print(f"no PDF in #{name} since {since:%Y-%m-%d %H:%M} AWST", file=sys.stderr)
    return 3 if empty else 0


if __name__ == "__main__":
    sys.exit(main())
