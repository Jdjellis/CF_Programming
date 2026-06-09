"""The week's class plan — the generator's primary programming input.

The Slack PDF is the *eventual* source (spec Section 5), but Slack ingestion is
out of scope this phase. Until it lands, the class plan is supplied through the
`ClassPlanProvider` interface — exactly mirroring how `MaxesProvider` stubs the
Sheet. A fixture/manual JSON file (`data/classplan.fixture.json`) stands in.

Nothing here does load arithmetic. A class session carries *targets* (a lift +
a `Target`); the deterministic `LoadCalculator` turns those into kilos + plates
downstream. Stimulus tags drive deconfliction (spec Section 3.3); they are the
only "judgment" this layer encodes, and they are an input, not a computation.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional, Protocol, Tuple, runtime_checkable

from cfprog.models import Target

# The six primary-stimulus tags deconfliction operates on (spec Section 3.3).
STIMULUS_TAGS: Tuple[str, ...] = (
    "heavy_squat",
    "heavy_pull",
    "press",
    "gymnastics",
    "engine",
    "mixed",
)

_DEFAULT_FIXTURE = (
    Path(__file__).resolve().parents[2] / "data" / "classplan.fixture.json"
)


def _check_stimulus(tag: str) -> str:
    if tag not in STIMULUS_TAGS:
        raise ValueError(f"unknown stimulus tag {tag!r}; must be one of {STIMULUS_TAGS}")
    return tag


# ---------------------------------------------------------------------------
# Strength prescriptions (shared by class sessions and focus templates)
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class SetScheme:
    """A block of identical sets at one target (e.g. 5 sets x 3 reps @ 87.5%).

    The `target` is what the calculator resolves to kilos. `reps` is carried for
    display only; for an RPE target it duplicates the reps inside the target.
    """

    sets: int
    target: Target
    reps: Optional[int] = None

    def __post_init__(self) -> None:
        if self.sets < 1:
            raise ValueError("sets must be >= 1")

    def describe(self) -> str:
        reps = self.reps if self.reps is not None else self.target.reps
        rep_str = f"{reps}" if reps is not None else "?"
        return f"{self.sets} x {rep_str} @ {self.target.describe()}"


@dataclass(frozen=True)
class StrengthPiece:
    """A named barbell movement with one or more set schemes."""

    lift: str
    label: str
    schemes: Tuple[SetScheme, ...]


def parse_target(d: dict) -> Tuple[Target, Optional[int]]:
    """Parse a scheme dict into a (Target, display_reps) pair.

    Accepts exactly one of: `percent`, `rpe` (+ `reps`), or `rep_max`.
    """
    if "percent" in d:
        return Target.percent_of_1rm(float(d["percent"])), d.get("reps")
    if "rpe" in d:
        reps = int(d["reps"])
        return Target.rpe(reps=reps, rpe=float(d["rpe"])), reps
    if "rep_max" in d:
        reps = int(d["rep_max"])
        return Target.rep_max(reps), reps
    raise ValueError(
        f"scheme must specify one of 'percent', 'rpe'(+reps), or 'rep_max': {d!r}"
    )


def parse_scheme(d: dict) -> SetScheme:
    target, reps = parse_target(d)
    return SetScheme(sets=int(d.get("sets", 1)), target=target, reps=reps)


def parse_strength_piece(d: dict) -> StrengthPiece:
    return StrengthPiece(
        lift=str(d["lift"]),
        label=str(d.get("label", d["lift"])),
        schemes=tuple(parse_scheme(s) for s in d["schemes"]),
    )


# ---------------------------------------------------------------------------
# Class session
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class ClassSession:
    """One day's class programming, tagged by primary stimulus.

    `also_taxes` lists secondary patterns the day still loads (e.g. Monday's
    primary is heavy_squat but it also presses and pulls). Deconfliction's
    "don't double-load a pattern the class already taxes" rule reads the full
    taxed set; the consecutive-day rule reads the primary `stimulus`.
    """

    day: str
    date: str
    title: str
    stimulus: str
    also_taxes: Tuple[str, ...] = ()
    movements: Tuple[str, ...] = ()
    strength: Tuple[StrengthPiece, ...] = ()

    def __post_init__(self) -> None:
        _check_stimulus(self.stimulus)
        for tag in self.also_taxes:
            _check_stimulus(tag)

    @property
    def taxed_patterns(self) -> frozenset:
        """Primary + secondary stimuli — everything the day loads."""
        return frozenset((self.stimulus,) + tuple(self.also_taxes))


# ---------------------------------------------------------------------------
# Provider interface + fixture implementation
# ---------------------------------------------------------------------------

@runtime_checkable
class ClassPlanProvider(Protocol):
    """Anything that can supply a week's class sessions."""

    def week_start(self) -> str: ...

    def sessions(self) -> List[ClassSession]: ...


class FixtureClassPlanProvider:
    """Reads the week's class plan from a local JSON fixture / manual entry file.

    Phase-2 stand-in for Slack PDF ingestion. Swapping in the real ingestion
    later means implementing `SlackClassPlanProvider.sessions()` and changing one
    line at the call site — no generator change.
    """

    def __init__(self, fixture_path: Path | str | None = None) -> None:
        self.fixture_path = Path(fixture_path) if fixture_path else _DEFAULT_FIXTURE
        with open(self.fixture_path, "r", encoding="utf-8") as fh:
            self._data = json.load(fh)
        self._sessions = tuple(_parse_session(s) for s in self._data["sessions"])

    def week_start(self) -> str:
        return str(self._data["week_start"])

    @property
    def source_label(self) -> str:
        return str(self._data.get("source_label", self._data.get("source", "fixture")))

    def sessions(self) -> List[ClassSession]:
        return list(self._sessions)


class InMemoryClassPlanProvider:
    """A provider built directly from objects — handy for tests and manual entry."""

    def __init__(self, week_start: str, sessions: List[ClassSession]) -> None:
        self._week_start = week_start
        self._sessions = list(sessions)
        self.source_label = "in-memory"

    def week_start(self) -> str:
        return self._week_start

    def sessions(self) -> List[ClassSession]:
        return list(self._sessions)


def _parse_session(d: dict) -> ClassSession:
    return ClassSession(
        day=str(d["day"]),
        date=str(d["date"]),
        title=str(d.get("title", "")),
        stimulus=_check_stimulus(str(d["stimulus"])),
        also_taxes=tuple(_check_stimulus(t) for t in d.get("also_taxes", ())),
        movements=tuple(d.get("movements", ())),
        strength=tuple(parse_strength_piece(s) for s in d.get("strength", ())),
    )
