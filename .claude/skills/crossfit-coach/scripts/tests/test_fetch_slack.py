"""fetch_slack against a fake Slack: no network, no token."""

import io
import json
import urllib.parse
import urllib.request
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

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
        self.file_bytes = PDF_BYTES

    def __call__(self, req: urllib.request.Request, timeout: Optional[float] = None) -> io.BytesIO:
        self.requests.append(req)
        url = urllib.parse.urlparse(req.full_url)
        if url.netloc == "files.slack.com":
            return io.BytesIO(self.file_bytes)
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


def single_channel_slack(messages: List[dict]) -> FakeSlack:
    return FakeSlack(channel_pages=[[{"id": "C1", "name": "performance"}]], history={"C1": messages})


def run_main(monkeypatch: pytest.MonkeyPatch, tmp_path: Path, opener, extra: Optional[List[str]] = None) -> int:
    monkeypatch.setenv("SLACK_BOT_TOKEN", "xoxb-test")
    channels = tmp_path / "channels.txt"
    channels.write_text("performance\n")
    argv = ["--channels-file", str(channels), "--since", "2026-10-11", "--out", str(tmp_path / "out")]
    return main(argv + (extra or []), opener=opener)


def test_main_exits_0_when_every_channel_has_a_pdf(monkeypatch: pytest.MonkeyPatch, tmp_path: Path):
    assert run_main(monkeypatch, tmp_path, single_channel_slack([pdf_message("week.pdf")])) == 0


def test_main_with_bad_since_exits_2(monkeypatch: pytest.MonkeyPatch, tmp_path: Path, capsys):
    opener = single_channel_slack([pdf_message("week.pdf")])
    assert run_main(monkeypatch, tmp_path, opener, ["--since", "2026-13-45"]) == 2
    assert "YYYY-MM-DD" in capsys.readouterr().err


def test_main_exits_2_when_the_opener_times_out(monkeypatch: pytest.MonkeyPatch, tmp_path: Path, capsys):
    def timing_out(req: urllib.request.Request, timeout: Optional[float] = None) -> io.BytesIO:
        raise TimeoutError("timed out")

    assert run_main(monkeypatch, tmp_path, timing_out) == 2
    assert "timed out" in capsys.readouterr().err


def test_main_exits_2_when_download_is_not_a_pdf(monkeypatch: pytest.MonkeyPatch, tmp_path: Path, capsys):
    fake = single_channel_slack([pdf_message("week.pdf")])
    fake.file_bytes = b"<html>sign in</html>"
    assert run_main(monkeypatch, tmp_path, fake) == 2
    assert "files:read" in capsys.readouterr().err


def test_fetch_keeps_both_same_named_pdfs(tmp_path: Path):
    fake = single_channel_slack([pdf_message("week.pdf"), pdf_message("week.pdf")])
    since = datetime(2026, 10, 11, 0, 0, tzinfo=AWST)
    saved, _ = fetch(SlackClient("xoxb-test", opener=fake), ["performance"], since, tmp_path)
    assert sorted(path.name for _, path in saved) == ["performance-week-2.pdf", "performance-week.pdf"]


def test_fetch_keeps_a_hostile_file_name_inside_out_dir(tmp_path: Path):
    out = tmp_path / "out"
    fake = single_channel_slack([pdf_message("../../evil.pdf")])
    since = datetime(2026, 10, 11, 0, 0, tzinfo=AWST)
    saved, _ = fetch(SlackClient("xoxb-test", opener=fake), ["performance"], since, out)
    assert [path.parent for _, path in saved] == [out]
    assert not (tmp_path / "evil.pdf").exists()


def test_fetch_skips_pdf_entries_missing_name_or_url_and_saves_the_valid_one(tmp_path: Path):
    malformed = {"ts": SUNDAY_10AM, "files": [{"filetype": "pdf"}]}
    fake = single_channel_slack([malformed, pdf_message("week.pdf")])
    since = datetime(2026, 10, 11, 0, 0, tzinfo=AWST)
    saved, _ = fetch(SlackClient("xoxb-test", opener=fake), ["performance"], since, tmp_path)
    assert [path.name for _, path in saved] == ["performance-week.pdf"]
