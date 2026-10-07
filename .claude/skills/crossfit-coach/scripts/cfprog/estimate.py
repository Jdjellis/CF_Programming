"""Estimate a 1RM from a performed set (xRM), via the spec's rep-max table.

Extracted from the old `analytics.py` so it carries no dependency on the retired
SQLite log layer. Using the *same* table the prescription side uses keeps one
source of truth for the rep<->% relationship — the estimate is the inverse of
the calculator.

    estimate = weight / (%1RM for the effective rep-max)

With an RPE, reps-in-reserve is folded in exactly as on the prescription side
(see `cfprog.targets`). This is pure, deterministic, unit-tested arithmetic — the
model never computes it at runtime.
"""

from __future__ import annotations

from typing import Optional, Tuple

from cfprog.models import Target
from cfprog.targets import resolve_target_fraction


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
