"""Tests for the deterministic plate solver — the spec's top-priority module."""

import pytest

from cfprog.models import Plate, PlateInventory
from cfprog.plates import best_loadout


# The confirmed inventory: 20 kg bar; pairs of 25/20/15/10/5/2.5/1.25 + 0.5 micro,
# effectively unlimited supply.
FULL = PlateInventory(
    bar_weight_kg=20.0,
    plates=(
        Plate(25.0), Plate(20.0), Plate(15.0), Plate(10.0),
        Plate(5.0), Plate(2.5), Plate(1.25), Plate(0.5),
    ),
)


def side_map(loadout):
    """{weight: count_per_side} for easy assertions."""
    return {pc.weight_kg: pc.count for pc in loadout.per_side}


# ---------------------------------------------------------------------------
# Exact loads
# ---------------------------------------------------------------------------

def test_empty_bar_exact():
    lo = best_loadout(20.0, FULL)
    assert lo.exact and lo.achieved_kg == 20.0
    assert lo.per_side == ()
    assert not lo.below_bar


def test_single_pair_exact():
    lo = best_loadout(70.0, FULL)  # 20 + 2*25
    assert lo.exact
    assert side_map(lo) == {25.0: 1}
    assert lo.per_side_kg == 25.0


def test_classic_100kg():
    lo = best_loadout(100.0, FULL)  # 20 + 2*(25+15) = 100
    assert lo.exact
    assert side_map(lo) == {25.0: 1, 15.0: 1}


def test_140_minimises_plate_count():
    # 60 kg/side. Should be 25+25+10, not 25+20+15 etc. (3 plates, fewest).
    lo = best_loadout(140.0, FULL)
    assert lo.exact
    assert lo.plates_per_side == 3
    assert side_map(lo) == {25.0: 2, 10.0: 1}


def test_heavy_deadlift_240():
    lo = best_loadout(240.0, FULL)  # 110/side = 4x25 + 10
    assert lo.exact
    assert side_map(lo) == {25.0: 4, 10.0: 1}


def test_fractional_exact_with_micro():
    # 20 + 2*(1.25 + 0.5) = 23.5
    lo = best_loadout(23.5, FULL)
    assert lo.exact
    assert side_map(lo) == {1.25: 1, 0.5: 1}


def test_smallest_increment_is_half_kg_per_side():
    # 0.5 kg micro on each side => 1 kg total step above the bar.
    lo = best_loadout(21.0, FULL)
    assert lo.exact
    assert side_map(lo) == {0.5: 1}


# ---------------------------------------------------------------------------
# Rounding to nearest loadable + delta reporting
# ---------------------------------------------------------------------------

def test_rounds_to_nearest_loadable_and_reports_delta():
    # 114.75 -> per side 47.375; nearest loadable is 47.5 (25+20+2.5) => 115.0
    lo = best_loadout(114.75, FULL)
    assert not lo.exact
    assert lo.achieved_kg == 115.0
    assert lo.delta_kg == pytest.approx(0.25)
    assert side_map(lo) == {25.0: 1, 20.0: 1, 2.5: 1}


def test_rounds_up_when_closer_above():
    # 115.32 -> per side 47.66; 47.75 (=>115.5, d +0.18) beats 47.5 (=>115.0, d -0.32)
    lo = best_loadout(115.32, FULL)
    assert not lo.exact
    assert lo.achieved_kg == 115.5
    assert lo.delta_kg == pytest.approx(0.18)


def test_rounds_down_when_closer_below():
    # 116.2 -> per side 48.1; 48.0 (=>116.0, d -0.2) beats 48.25 (=>116.5, d +0.3)
    lo = best_loadout(116.2, FULL)
    assert not lo.exact
    assert lo.achieved_kg == 116.0
    assert lo.delta_kg == pytest.approx(-0.2)


def test_unloadable_gap_rounds_to_nearest():
    # 20.4: below smallest loadable step (21.0). Nearest is the bare bar (20.0).
    lo = best_loadout(20.4, FULL)
    assert lo.achieved_kg == 20.0
    assert lo.per_side == ()
    assert lo.delta_kg == pytest.approx(-0.4)


def test_exact_distance_tie_prefers_rounding_down():
    # Without a 0.5 plate, steps are 2.5 kg/side = 5 kg total above 20.
    # Target 22.5 sits exactly between 20.0 and 25.0 -> prefer 20.0 (no overshoot).
    inv = PlateInventory(
        bar_weight_kg=20.0,
        plates=(Plate(25.0), Plate(20.0), Plate(2.5)),
    )
    lo = best_loadout(22.5, inv)
    assert lo.achieved_kg == 20.0
    assert lo.delta_kg == pytest.approx(-2.5)


# ---------------------------------------------------------------------------
# Sub-bar loads
# ---------------------------------------------------------------------------

def test_sub_bar_load_flagged():
    lo = best_loadout(15.0, FULL)
    assert lo.below_bar
    assert lo.achieved_kg == 20.0
    assert lo.per_side == ()
    assert lo.delta_kg == pytest.approx(5.0)


# ---------------------------------------------------------------------------
# Inventory limits (generalised — confirmed inventory is unlimited)
# ---------------------------------------------------------------------------

def test_limited_inventory_falls_back_to_smaller_plates():
    # Only one pair of 25s. 60/side wants 2x25+10 but we have one 25.
    inv = PlateInventory(
        bar_weight_kg=20.0,
        plates=(Plate(25.0, count=1), Plate(20.0), Plate(15.0), Plate(10.0)),
    )
    lo = best_loadout(140.0, inv)  # 60/side
    assert lo.exact
    counts = side_map(lo)
    assert counts.get(25.0, 0) <= 1
    assert sum(w * c for w, c in counts.items()) == 60.0


def test_runs_out_of_plates_rounds_to_best_available():
    # One pair of 10s only; can't reach 60/side. Best loadable is 10/side => 40.
    inv = PlateInventory(bar_weight_kg=20.0, plates=(Plate(10.0, count=1),))
    lo = best_loadout(140.0, inv)
    assert not lo.exact
    assert lo.achieved_kg == 40.0
    assert side_map(lo) == {10.0: 1}


# ---------------------------------------------------------------------------
# Symmetry / determinism invariants
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("target", [60, 72.5, 100, 102.5, 137.5, 200, 240])
def test_total_equals_bar_plus_two_sides(target):
    lo = best_loadout(float(target), FULL)
    rebuilt = lo.bar_weight_kg + 2 * sum(
        pc.weight_kg * pc.count for pc in lo.per_side
    )
    assert rebuilt == pytest.approx(lo.achieved_kg)


def test_deterministic_repeatable():
    a = best_loadout(142.5, FULL)
    b = best_loadout(142.5, FULL)
    assert side_map(a) == side_map(b)
    assert a.achieved_kg == b.achieved_kg
