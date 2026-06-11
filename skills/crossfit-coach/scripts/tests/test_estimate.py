"""Tests for estimated 1RM (the inverse of the rep-max table)."""

import pytest

from cfprog.estimate import estimate_one_rm


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
