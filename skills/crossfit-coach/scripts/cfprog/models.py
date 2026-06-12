"""Data models for the load calculator.

Everything here is plain data. The only arithmetic is a presentation-level
rounding of the working weight to a loadable kg — the consequential percentage /
RPE / rep-max math lives in `targets.py` so it can be unit-tested in isolation.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from decimal import ROUND_HALF_UP, Decimal
from typing import Literal, Optional


def round_to_half_kg(value: float) -> float:
    """Round to the nearest 0.5 kg, half-up.

    Presentation only — the weight to actually load on the bar, not a
    re-derivation of the percentage. An experienced lifter sorts the plates;
    the calculator just hands them a clean, loadable number.
    """
    halves = (Decimal(str(value)) / Decimal("0.5")).quantize(
        Decimal("1"), rounding=ROUND_HALF_UP
    )
    return float(halves * Decimal("0.5"))


# ---------------------------------------------------------------------------
# Targets
# ---------------------------------------------------------------------------

TargetKind = Literal["percent", "rep_max", "rpe"]


@dataclass(frozen=True)
class Target:
    """A prescription target, expressed one of three ways.

    Use the constructors `percent`, `rep_max`, or `rpe` rather than building
    this directly — they validate the right fields.

    kind == "percent":  percent set (e.g. 85.0 for 85% of 1RM)
    kind == "rep_max":  reps set    (e.g. reps=3 for a 3RM target)
    kind == "rpe":      reps + rpe  (e.g. reps=5, rpe=8 -> 5 reps @ RPE 8)
    """

    kind: TargetKind
    percent: Optional[float] = None
    reps: Optional[int] = None
    rpe: Optional[float] = None

    @classmethod
    def percent_of_1rm(cls, percent: float) -> "Target":
        if percent <= 0:
            raise ValueError("percent must be positive")
        return cls(kind="percent", percent=float(percent))

    @classmethod
    def rep_max(cls, reps: int) -> "Target":
        if reps < 1:
            raise ValueError("rep-max reps must be >= 1")
        return cls(kind="rep_max", reps=int(reps))

    @classmethod
    def rpe(cls, reps: int, rpe: float) -> "Target":
        if reps < 1:
            raise ValueError("rpe reps must be >= 1")
        if not (1 <= rpe <= 10):
            raise ValueError("rpe must be in [1, 10]")
        return cls(kind="rpe", reps=int(reps), rpe=float(rpe))

    def describe(self) -> str:
        if self.kind == "percent":
            return f"{self.percent:g}% of 1RM"
        if self.kind == "rep_max":
            return f"{self.reps}RM"
        return f"{self.reps} reps @ RPE {self.rpe:g}"


# ---------------------------------------------------------------------------
# Results
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class PrescriptionResult:
    """Full record for one prescription: lift + target -> working weight."""

    lift: str
    target: Target
    one_rm_kg: float
    target_fraction: float    # fraction of 1RM the target resolves to (e.g. 0.85)
    working_weight_kg: float  # one_rm * fraction, before display rounding
    notes: tuple[str, ...] = field(default_factory=tuple)

    @property
    def prescribed_kg(self) -> float:
        """Working weight rounded to the nearest 0.5 kg (half-up) — what to load."""
        return round_to_half_kg(self.working_weight_kg)

    def load_line(self) -> str:
        """The paste-ready load string, e.g. '144.5 kg (87.5% of 165)'."""
        pct = self.target_fraction * 100
        return f"{self.prescribed_kg:g} kg ({pct:g}% of {self.one_rm_kg:g})"

    def summary(self) -> str:
        head = f"{self.lift}  {self.target.describe()}  ->  {self.load_line()}"
        if self.notes:
            head += "\n" + "\n".join(f"    note: {n}" for n in self.notes)
        return head
