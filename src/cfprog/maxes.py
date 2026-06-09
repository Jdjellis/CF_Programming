"""Read current 1RMs from the source of truth.

Spec Section 8: the Google Sheet top section is the single source of truth for
maxes — read it, never hardcode maxes elsewhere. Sheets auth isn't wired in
Phase 1, so the read sits behind the `MaxesProvider` interface and loads from a
local fixture that mirrors the Sheet. Swapping in real Sheets I/O later means
implementing `GoogleSheetsMaxesProvider.get_max` and changing one line at the
call site — no calculator change.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, Protocol, runtime_checkable

# Source-of-truth Sheet (top section). Do NOT read the deprecated training
# blocks lower in the workbook.
SHEET_ID = "1Q1RlKE9LfTpUYSAqwFWnknJ_g9ftTal1P4eeMBnqY_A"

_DEFAULT_FIXTURE = Path(__file__).resolve().parents[2] / "data" / "maxes.fixture.json"


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
    """Reads maxes from a local JSON fixture mirroring the Sheet top section.

    Phase 1 stand-in for live Sheets reads. The fixture documents its own
    provenance (sheet_id) so it's never mistaken for the canonical store.
    """

    def __init__(self, fixture_path: Path | str | None = None) -> None:
        self.fixture_path = Path(fixture_path) if fixture_path else _DEFAULT_FIXTURE
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


class GoogleSheetsMaxesProvider:
    """Live read from the Sheet top section. Not wired in Phase 1.

    Implement `get_max`/`all_maxes` here when Sheets auth lands (gspread or the
    google-api client). Read only the top section; never touch the deprecated
    training blocks.
    """

    def __init__(self, sheet_id: str = SHEET_ID) -> None:
        self.sheet_id = sheet_id

    def _not_wired(self) -> "NotImplementedError":
        return NotImplementedError(
            "Google Sheets read not wired yet (Phase 1). Use FixtureMaxesProvider "
            f"until auth is configured. Source-of-truth Sheet: {self.sheet_id}"
        )

    def get_max(self, lift: str) -> float:
        raise self._not_wired()

    def all_maxes(self) -> Dict[str, float]:
        raise self._not_wired()
