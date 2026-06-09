"""Tests for target resolution (%/rep-max/RPE -> fraction of 1RM)."""

import pytest

from cfprog.models import Target
from cfprog.targets import (
    REP_MAX_PCT,
    fraction_for_rep_max,
    resolve_target_fraction,
    resolve_target_weight,
)


def test_percent_passthrough():
    frac, notes = resolve_target_fraction(Target.percent_of_1rm(85))
    assert frac == pytest.approx(0.85)
    assert notes == ()


@pytest.mark.parametrize(
    "reps,pct",
    [(1, 100), (2, 95), (3, 93), (4, 90), (5, 87),
     (6, 85), (7, 83), (8, 80), (9, 77), (10, 75)],
)
def test_rep_max_table(reps, pct):
    frac, _ = resolve_target_fraction(Target.rep_max(reps))
    assert frac == pytest.approx(pct / 100.0)
    assert REP_MAX_PCT[reps] == pct


def test_rep_max_above_table_clamps_with_note():
    frac, notes = resolve_target_fraction(Target.rep_max(12))
    assert frac == pytest.approx(0.75)  # clamped to 10RM
    assert notes and "clamped" in notes[0].lower()


def test_rpe8_for_5_is_7rm():
    # 5 reps @ RPE 8 -> 2 RIR -> effective 7RM -> 83%.
    frac, notes = resolve_target_fraction(Target.rpe(reps=5, rpe=8))
    assert frac == pytest.approx(0.83)
    assert notes and "7RM" in notes[0]


def test_rpe10_single_is_1rm():
    frac, _ = resolve_target_fraction(Target.rpe(reps=1, rpe=10))
    assert frac == pytest.approx(1.00)


def test_rpe_half_point_rounds_half_up():
    # 3 reps @ RPE 8.5 -> RIR 1.5 -> round-half-up to 2 -> effective 5RM -> 87%.
    frac, _ = resolve_target_fraction(Target.rpe(reps=3, rpe=8.5))
    assert frac == pytest.approx(0.87)


def test_rpe_low_effective_clamps_high_side():
    # 10 reps @ RPE 6 -> 4 RIR -> effective 14RM -> clamps to 10RM (75%).
    frac, notes = resolve_target_fraction(Target.rpe(reps=10, rpe=6))
    assert frac == pytest.approx(0.75)
    assert "clamped" in notes[0].lower()


def test_resolve_weight_combines_max_and_fraction():
    weight, frac, _ = resolve_target_weight(Target.percent_of_1rm(85), one_rm_kg=135)
    assert frac == pytest.approx(0.85)
    assert weight == pytest.approx(114.75)


def test_fraction_for_rep_max_clamps_both_ends():
    assert fraction_for_rep_max(0) == pytest.approx(1.0)   # clamps to 1RM
    assert fraction_for_rep_max(99) == pytest.approx(0.75)  # clamps to 10RM
