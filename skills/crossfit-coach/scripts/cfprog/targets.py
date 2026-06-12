"""Resolve a prescription target to a fraction of 1RM (and thus a weight).

All three target forms collapse to a single percentage of 1RM, using the
rep-max -> %1RM table from the spec (Section 4). This is deterministic, table
driven, and unit-tested — no runtime judgement, no model arithmetic.

Rep-max -> %1RM (spec, mirrors the Sheet):
    1RM 100 · 2RM 95 · 3RM 93 · 4RM 90 · 5RM 87 · 6RM 85 ·
    7RM 83 · 8RM 80 · 9RM 77 · 10RM 75

RPE handling
------------
The spec supplies a rep-max table but no separate RPE chart, so we map RPE to a
rep-max deterministically using the standard reps-in-reserve convention:

    RIR             = 10 - RPE              (RPE 8 => 2 reps in reserve)
    effective_reps  = reps + RIR           (the rep-max the set approximates)
    fraction        = REP_MAX_PCT[effective_reps] / 100

So "5 reps @ RPE 8" => 5 + 2 = 7 => treat as a 7RM => 83% of 1RM. This keeps the
whole system anchored to the single table the Sheet owns. effective_reps is
clamped to [1, 10] (the table's bounds) and a note is emitted when clamping
happens. RIR uses round-half-up so half-point RPEs land on a whole rep.
"""

from __future__ import annotations

from decimal import ROUND_HALF_UP, Decimal
from typing import Tuple

from cfprog.models import Target

# Rep-max -> %1RM, straight from the spec. Keyed by reps.
REP_MAX_PCT: dict[int, float] = {
    1: 100.0,
    2: 95.0,
    3: 93.0,
    4: 90.0,
    5: 87.0,
    6: 85.0,
    7: 83.0,
    8: 80.0,
    9: 77.0,
    10: 75.0,
}

_MIN_REPS = min(REP_MAX_PCT)
_MAX_REPS = max(REP_MAX_PCT)


def _round_half_up(value: float) -> int:
    return int(Decimal(str(value)).quantize(Decimal("1"), rounding=ROUND_HALF_UP))


def fraction_for_rep_max(reps: int) -> float:
    """%1RM (as a fraction, e.g. 0.93) for an n-rep max. Clamped to table bounds."""
    clamped = max(_MIN_REPS, min(_MAX_REPS, reps))
    return REP_MAX_PCT[clamped] / 100.0


def resolve_target_fraction(target: Target) -> Tuple[float, Tuple[str, ...]]:
    """Return (fraction_of_1RM, notes) for any target form.

    Pure and deterministic. notes carries any clamping/assumption messages.
    """
    notes: list[str] = []

    if target.kind == "percent":
        return target.percent / 100.0, ()

    if target.kind == "rep_max":
        reps = target.reps
        if reps > _MAX_REPS:
            notes.append(
                f"{reps}RM exceeds rep-max table (max {_MAX_REPS}RM); "
                f"clamped to {_MAX_REPS}RM = {REP_MAX_PCT[_MAX_REPS]:g}%"
            )
        return fraction_for_rep_max(reps), tuple(notes)

    if target.kind == "rpe":
        rir = _round_half_up(10.0 - target.rpe)
        effective_reps = target.reps + rir
        note = (
            f"RPE {target.rpe:g} for {target.reps} -> "
            f"{rir} reps in reserve -> effective {effective_reps}RM"
        )
        if effective_reps > _MAX_REPS:
            note += f" (clamped to {_MAX_REPS}RM)"
        elif effective_reps < _MIN_REPS:
            note += f" (clamped to {_MIN_REPS}RM)"
        notes.append(note)
        return fraction_for_rep_max(effective_reps), tuple(notes)

    raise ValueError(f"unknown target kind: {target.kind!r}")


def resolve_target_weight(
    target: Target, one_rm_kg: float
) -> Tuple[float, float, Tuple[str, ...]]:
    """Return (working_weight_kg, fraction, notes) for target against a 1RM.

    working_weight_kg is the raw weight *before* the display rounding to a
    loadable 0.5 kg (see models.round_to_half_kg).
    """
    fraction, notes = resolve_target_fraction(target)
    return one_rm_kg * fraction, fraction, notes
