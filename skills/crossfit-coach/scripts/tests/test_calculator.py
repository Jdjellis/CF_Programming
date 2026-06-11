"""End-to-end tests: lift + target -> working weight + loadout, via the fixture."""

import pytest

from cfprog.calculator import LoadCalculator, load_inventory
from cfprog.maxes import FixtureMaxesProvider, GoogleSheetsMaxesProvider
from cfprog.models import Target


@pytest.fixture(scope="module")
def calc():
    return LoadCalculator()


def test_front_squat_85pct(calc):
    res = calc.prescribe("front_squat", Target.percent_of_1rm(85))
    assert res.one_rm_kg == 135
    assert res.working_weight_kg == pytest.approx(114.75)
    assert res.loadout.achieved_kg == 115.0  # nearest loadable
    assert res.loadout.delta_kg == pytest.approx(0.25)


def test_clean_3rm(calc):
    res = calc.prescribe("clean", Target.rep_max(3))
    assert res.one_rm_kg == 124
    assert res.working_weight_kg == pytest.approx(124 * 0.93)  # 115.32
    # nearest loadable to 115.32 is 115.5 (47.75/side), rounding up 0.18 kg
    assert res.loadout.achieved_kg == 115.5
    assert res.loadout.delta_kg == pytest.approx(0.18)


def test_strict_press_rpe8_for_5(calc):
    res = calc.prescribe("strict_press", Target.rpe(reps=5, rpe=8))
    assert res.one_rm_kg == 70
    # 7RM -> 83% of 70 = 58.1 kg
    assert res.working_weight_kg == pytest.approx(58.1)
    # per side 19.05 -> nearest loadable 19.0 (15+2.5+1.25+... ) check it's close
    assert res.loadout.achieved_kg == pytest.approx(58.0)
    assert res.loadout.delta_kg == pytest.approx(-0.1)
    assert res.notes  # RPE assumption surfaced


def test_lift_name_normalisation(calc):
    a = calc.prescribe("Front Squat", Target.percent_of_1rm(85))
    b = calc.prescribe("front_squat", Target.percent_of_1rm(85))
    assert a.one_rm_kg == b.one_rm_kg


def test_clean_and_jerk_alias(calc):
    res = calc.prescribe("Clean & Jerk", Target.percent_of_1rm(80))
    assert res.one_rm_kg == 124


def test_unknown_lift_raises(calc):
    with pytest.raises(KeyError):
        calc.prescribe("turkish_getup", Target.percent_of_1rm(80))


def test_fixture_documents_sheet_source():
    prov = FixtureMaxesProvider()
    maxes = prov.all_maxes()
    assert maxes["back_squat"] == 165
    assert maxes["power_snatch"] == 82.5


def test_sheets_provider_not_wired_yet():
    prov = GoogleSheetsMaxesProvider()
    with pytest.raises(NotImplementedError):
        prov.get_max("front_squat")


def test_default_inventory_loads():
    inv = load_inventory()
    assert inv.bar_weight_kg == 20.0
    assert any(p.weight_kg == 0.5 for p in inv.plates)
