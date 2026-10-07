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


def normalize_lift(name: str) -> str:
    """Canonicalise a lift name: lowercase, spaces/'&'/hyphens -> underscores."""
    key = name.strip().lower()
    key = key.replace("&", " and ")
    for ch in (" ", "-", "/"):
        key = key.replace(ch, "_")
    while "__" in key:
        key = key.replace("__", "_")
    return key.strip("_")


@runtime_checkable
class MaxesProvider(Protocol):
    """Anything that can return the current 1RM (kg) for a lift."""

    def get_max(self, lift: str) -> float: ...

    def all_maxes(self) -> Dict[str, float]: ...


class FixtureMaxesProvider:
    """Reads maxes from a JSON file shaped like data/maxes.json ({"maxes": {lift: {"one_rm": kg}}})."""

    def __init__(self, fixture_path: Path | str | None = None) -> None:
        self.fixture_path = Path(fixture_path) if fixture_path else DEFAULT_MAXES_PATH
        with open(self.fixture_path, "r", encoding="utf-8") as fh:
            data = json.load(fh)
        self._maxes: Dict[str, float] = {
            normalize_lift(lift): float(entry["one_rm"])
            for lift, entry in data["maxes"].items()
        }

    def get_max(self, lift: str) -> float:
        key = normalize_lift(lift)
        if key not in self._maxes:
            raise KeyError(
                f"no 1RM for lift {lift!r} (normalized {key!r}); "
                f"known lifts: {sorted(self._maxes)}"
            )
        return self._maxes[key]

    def all_maxes(self) -> Dict[str, float]:
        return dict(self._maxes)
