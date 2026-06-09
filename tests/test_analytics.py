"""Tests for deterministic analytics: estimated 1RM, tonnage, ratio gaps."""

import pytest

from cfprog.analytics import (
    best_estimated_one_rm,
    estimate_one_rm,
    ratio_gaps,
    tonnage,
    tonnage_by_lift,
)
from cfprog.logstore import LoggedSet
from cfprog.maxes import FixtureMaxesProvider


# ---------------------------------------------------------------------------
# Estimated 1RM (inverse of the rep-max table)
# ---------------------------------------------------------------------------

def test_estimate_from_true_1rm_is_identity():
    est, _ = estimate_one_rm(100, reps=1)
    assert est == 100.0


def test_estimate_from_rep_max():
    # 100 kg x 5 -> 5RM = 87% -> ~114.94
    est, _ = estimate_one_rm(100, reps=5)
    assert est == pytest.approx(114.94, abs=0.01)


def test_estimate_rpe_aware():
    # 100 x 5 @ RPE 8 -> effective 7RM = 83% -> ~120.48
    est, notes = estimate_one_rm(100, reps=5, rpe=8)
    assert est == pytest.approx(120.48, abs=0.01)
    assert notes  # RPE assumption surfaced


def test_best_estimated_one_rm_picks_max():
    sets = [
        LoggedSet(lift="clean", weight_kg=100, reps=3),       # 93% -> ~107.5
        LoggedSet(lift="clean", weight_kg=110, reps=1),       # 100% -> 110
        LoggedSet(lift="clean", weight_kg=95, reps=5, rpe=9), # eff 6RM 85% -> ~111.8
    ]
    assert best_estimated_one_rm(sets) == pytest.approx(111.76, abs=0.1)
    assert best_estimated_one_rm([]) is None


# ---------------------------------------------------------------------------
# Tonnage
# ---------------------------------------------------------------------------

def test_tonnage_and_by_lift():
    sets = [
        LoggedSet(lift="front_squat", weight_kg=100, reps=5),  # 500
        LoggedSet(lift="front_squat", weight_kg=100, reps=3),  # 300
        LoggedSet(lift="clean", weight_kg=80, reps=2),         # 160
    ]
    assert tonnage(sets) == 960
    assert tonnage_by_lift(sets) == {"front_squat": 800, "clean": 160}


# ---------------------------------------------------------------------------
# Ratio gaps vs standards
# ---------------------------------------------------------------------------

def test_ratio_gaps_flag_known_weaknesses():
    results = {(r.lift, r.reference): r for r in ratio_gaps(FixtureMaxesProvider())}

    # Snatch is technique-limited: 88/165 = 53.3% vs 60-65% -> below.
    snatch = results[("snatch", "back_squat")]
    assert snatch.actual_pct == pytest.approx(53.33, abs=0.01)
    assert snatch.status == "below"
    assert snatch.gap_pct == pytest.approx(6.67, abs=0.01)

    # Front squat is the keystone limiter: 135/165 = 81.8% vs 85-93% -> below.
    fs = results[("front_squat", "back_squat")]
    assert fs.status == "below"

    # Clean is too high relative to deadlift bias is fine; C&J/FS too high:
    # 124/135 = 91.9% vs 85-90% -> above.
    cj_fs = results[("clean_and_jerk", "front_squat")]
    assert cj_fs.status == "above"
    assert cj_fs.gap_pct < 0


def test_ratio_results_have_full_coverage():
    results = ratio_gaps(FixtureMaxesProvider())
    assert len(results) == 11
    for r in results:
        assert r.status in {"below", "in_range", "above"}
