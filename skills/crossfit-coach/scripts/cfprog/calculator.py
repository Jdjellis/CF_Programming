"""High-level load calculator: lift + target + max -> working weight.

Ties together the deterministic pieces:
    maxes (source of truth) -> targets (% resolution) -> working weight.
No arithmetic happens here that isn't delegated to a tested module.
"""

from __future__ import annotations

from cfprog.maxes import FixtureMaxesProvider, MaxesProvider
from cfprog.models import PrescriptionResult, Target
from cfprog.targets import resolve_target_weight


class LoadCalculator:
    """Resolve prescriptions to concrete working weights."""

    def __init__(self, maxes: MaxesProvider | None = None) -> None:
        self.maxes: MaxesProvider = maxes or FixtureMaxesProvider()

    def prescribe(self, lift: str, target: Target) -> PrescriptionResult:
        one_rm = self.maxes.get_max(lift)
        working_weight, fraction, notes = resolve_target_weight(target, one_rm)
        return PrescriptionResult(
            lift=lift,
            target=target,
            one_rm_kg=one_rm,
            target_fraction=fraction,
            working_weight_kg=working_weight,
            notes=notes,
        )
