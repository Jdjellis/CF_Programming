"""Data models for the load/plate calculator.

Everything here is plain data. No arithmetic of consequence happens in this
module beyond trivial conversions; the load math lives in `plates.py` and
`targets.py` so it can be unit-tested in isolation.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal, Optional


# ---------------------------------------------------------------------------
# Inventory
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class Plate:
    """A plate denomination and how many *pairs* are available.

    count is the number of plates available *per side* (i.e. pairs). None means
    effectively unlimited supply.
    """

    weight_kg: float
    count: Optional[int] = None  # None => unlimited

    def __post_init__(self) -> None:
        if self.weight_kg <= 0:
            raise ValueError(f"plate weight must be positive, got {self.weight_kg}")
        if self.count is not None and self.count < 0:
            raise ValueError(f"plate count must be >= 0 or None, got {self.count}")


@dataclass(frozen=True)
class PlateInventory:
    """The bar plus the set of plate denominations available."""

    bar_weight_kg: float
    plates: tuple[Plate, ...]

    def __post_init__(self) -> None:
        if self.bar_weight_kg <= 0:
            raise ValueError(f"bar weight must be positive, got {self.bar_weight_kg}")
        if not self.plates:
            raise ValueError("inventory must contain at least one plate denomination")

    @classmethod
    def from_dict(cls, data: dict) -> "PlateInventory":
        plates = tuple(
            Plate(weight_kg=float(p["weight_kg"]), count=p.get("count"))
            for p in data["plates"]
        )
        return cls(bar_weight_kg=float(data["bar_weight_kg"]), plates=plates)


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
class PlateCount:
    """A denomination and how many go on *each* side."""

    weight_kg: float
    count: int  # plates per side

    def __str__(self) -> str:
        w = f"{self.weight_kg:g}"
        return f"{self.count}x{w}"


@dataclass(frozen=True)
class Loadout:
    """The result of solving plate math for a single target weight."""

    target_kg: float          # the weight we were asked to load
    achieved_kg: float        # nearest loadable total with the inventory
    bar_weight_kg: float
    per_side: tuple[PlateCount, ...]  # plates per side, heaviest first
    exact: bool               # achieved == target (within rounding tolerance)
    below_bar: bool           # target was lighter than the empty bar

    @property
    def delta_kg(self) -> float:
        """achieved - target. Positive => rounded up, negative => rounded down."""
        return round(self.achieved_kg - self.target_kg, 5)

    @property
    def per_side_kg(self) -> float:
        return round((self.achieved_kg - self.bar_weight_kg) / 2.0, 5)

    @property
    def plates_per_side(self) -> int:
        return sum(pc.count for pc in self.per_side)

    def per_side_str(self) -> str:
        if not self.per_side:
            return "(empty bar)"
        parts = []
        for pc in self.per_side:
            if pc.count > 1:
                parts.append(f"{pc.count}×{pc.weight_kg:g}")
            else:
                parts.append(f"{pc.weight_kg:g}")
        return " + ".join(parts)

    def summary(self) -> str:
        line = (
            f"{self.achieved_kg:g} kg = {self.bar_weight_kg:g} bar "
            f"+ [{self.per_side_str()}] per side"
        )
        if not self.exact:
            sign = "+" if self.delta_kg >= 0 else ""
            line += f"  (target {self.target_kg:g}, delta {sign}{self.delta_kg:g} kg)"
        if self.below_bar:
            line += "  [BELOW BAR — empty bar is heavier than target]"
        return line


@dataclass(frozen=True)
class PrescriptionResult:
    """Full record for one prescription: lift + target -> weight + loadout."""

    lift: str
    target: Target
    one_rm_kg: float
    target_fraction: float    # fraction of 1RM the target resolves to (e.g. 0.85)
    working_weight_kg: float  # one_rm * fraction, before plate rounding
    loadout: Loadout
    notes: tuple[str, ...] = field(default_factory=tuple)

    def summary(self) -> str:
        pct = self.target_fraction * 100
        head = (
            f"{self.lift}  {self.target.describe()}  "
            f"-> {pct:.1f}% of {self.one_rm_kg:g} = {self.working_weight_kg:.2f} kg"
        )
        body = f"    {self.loadout.summary()}"
        if self.notes:
            body += "\n" + "\n".join(f"    note: {n}" for n in self.notes)
        return head + "\n" + body
