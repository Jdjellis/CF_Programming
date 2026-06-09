"""Deterministic analytics over logged actuals + maxes.

First analytics on top of the logging layer. Everything here is pure, tested
arithmetic (the model never computes these):

* `estimate_one_rm`  — invert the spec's rep-max table to estimate a 1RM from a
  performed set. Using the same table the prescription side uses keeps one
  source of truth for the rep<->% relationship.
* tonnage helpers     — volume from logged sets.
* `ratio_gaps`        — gap analysis of current maxes vs the spec's lift-ratio
  standards (reads the maxes source of truth; nothing hardcoded).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Iterable, List, Optional, Tuple

from cfprog.logstore import LoggedSet
from cfprog.maxes import MaxesProvider, normalize_lift
from cfprog.models import Target
from cfprog.targets import resolve_target_fraction


# ---------------------------------------------------------------------------
# Estimated 1RM
# ---------------------------------------------------------------------------

def estimate_one_rm(
    weight_kg: float, reps: int, rpe: Optional[float] = None
) -> Tuple[float, Tuple[str, ...]]:
    """Estimate 1RM from a performed set via the rep-max table (RPE-aware).

    weight / (%1RM for the effective rep-max). With an RPE, reps-in-reserve is
    folded in exactly as on the prescription side. Returns (estimate, notes).
    """
    target = Target.rpe(reps=reps, rpe=rpe) if rpe is not None else Target.rep_max(reps)
    fraction, notes = resolve_target_fraction(target)
    return round(weight_kg / fraction, 2), notes


def estimate_one_rm_for_set(s: LoggedSet) -> float:
    est, _ = estimate_one_rm(s.weight_kg, s.reps, s.rpe)
    return est


def best_estimated_one_rm(sets: Iterable[LoggedSet]) -> Optional[float]:
    """Highest estimated 1RM across the given sets (a PR-from-submaximal proxy)."""
    estimates = [estimate_one_rm_for_set(s) for s in sets]
    return max(estimates) if estimates else None


# ---------------------------------------------------------------------------
# Volume
# ---------------------------------------------------------------------------

def tonnage(sets: Iterable[LoggedSet]) -> float:
    return round(sum(s.tonnage_kg for s in sets), 5)


def tonnage_by_lift(sets: Iterable[LoggedSet]) -> Dict[str, float]:
    out: Dict[str, float] = {}
    for s in sets:
        out[s.lift] = round(out.get(s.lift, 0.0) + s.tonnage_kg, 5)
    return out


# ---------------------------------------------------------------------------
# Lift-ratio standards (spec Section 4)
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class RatioStandard:
    lift: str
    reference: str
    low: float
    high: float


# NOTE: "Push Press / Jerk" — the spec says "Jerk"; we use the split jerk (the
# athlete's heaviest jerk). Change `reference` here if you'd rather compare to
# the push jerk.
RATIO_STANDARDS: Tuple[RatioStandard, ...] = (
    RatioStandard("snatch", "back_squat", 60, 65),
    RatioStandard("clean_and_jerk", "back_squat", 80, 85),
    RatioStandard("clean_and_jerk", "front_squat", 85, 90),
    RatioStandard("snatch", "clean_and_jerk", 80, 85),
    RatioStandard("front_squat", "back_squat", 85, 93),
    RatioStandard("power_snatch", "snatch", 80, 85),
    RatioStandard("power_clean", "clean", 80, 90),
    RatioStandard("clean", "deadlift", 70, 75),
    RatioStandard("strict_press", "push_press", 70, 75),
    RatioStandard("push_press", "split_jerk", 75, 85),
    RatioStandard("overhead_squat", "back_squat", 65, 70),
)


@dataclass(frozen=True)
class RatioResult:
    lift: str
    reference: str
    actual_pct: float
    low: float
    high: float
    status: str        # "below" | "in_range" | "above"
    gap_pct: float     # how far below `low` (>0) or above `high` (<0); 0 in range

    def summary(self) -> str:
        band = f"{self.low:g}-{self.high:g}%"
        line = f"{self.lift} / {self.reference}: {self.actual_pct:.1f}% (target {band}) -> {self.status}"
        if self.status == "below":
            line += f", {self.gap_pct:.1f} pts low"
        elif self.status == "above":
            line += f", {-self.gap_pct:.1f} pts high"
        return line


def ratio_gaps(
    maxes: MaxesProvider, standards: Iterable[RatioStandard] = RATIO_STANDARDS
) -> List[RatioResult]:
    """Compare current maxes against the lift-ratio standards. Reads source of truth."""
    results: List[RatioResult] = []
    for std in standards:
        a = maxes.get_max(normalize_lift(std.lift))
        b = maxes.get_max(normalize_lift(std.reference))
        actual = round(100.0 * a / b, 2)
        if actual < std.low:
            status, gap = "below", round(std.low - actual, 2)
        elif actual > std.high:
            status, gap = "above", round(std.high - actual, 2)  # negative
        else:
            status, gap = "in_range", 0.0
        results.append(
            RatioResult(std.lift, std.reference, actual, std.low, std.high, status, gap)
        )
    return results
