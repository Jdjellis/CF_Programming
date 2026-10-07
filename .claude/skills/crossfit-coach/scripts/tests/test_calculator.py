"""End-to-end tests: lift + target -> working weight, via the fixture.

The calculator resolves a target to a raw working weight (one_rm * fraction) and
a loadable `prescribed_kg` rounded to the nearest 0.5 kg. There is no plate
math — an experienced lifter loads the bar themselves.
"""

import pytest

from cfprog.calculator import LoadCalculator
from cfprog.maxes import FixtureMaxesProvider, GoogleSheetsMaxesProvider
from cfprog.models import Target


@pytest.fixture(scope="module")
def calc():
    return LoadCalculator()


def test_front_squat_85pct(calc):
    res = calc.prescribe("front_squat", Target.percent_of_1rm(85))
    assert res.one_rm_kg == 135
    assert res.working_weight_kg == pytest.approx(114.75)
    assert res.prescribed_kg == 115.0  # nearest 0.5 kg, half-up
    assert res.load_line() == "115 kg (85% of 135)"


def test_clean_3rm(calc):
    res = calc.prescribe("clean", Target.rep_max(3))
    assert res.one_rm_kg == 124
    assert res.working_weight_kg == pytest.approx(124 * 0.93)  # 115.32
    assert res.prescribed_kg == 115.5  # 115.32 -> nearest 0.5
    assert res.load_line() == "115.5 kg (93% of 124)"


def test_strict_press_rpe8_for_5(calc):
    res = calc.prescribe("strict_press", Target.rpe(reps=5, rpe=8))
    assert res.one_rm_kg == 70
    # 7RM -> 83% of 70 = 58.1 kg -> 58.0 loadable
    assert res.working_weight_kg == pytest.approx(58.1)
    assert res.prescribed_kg == 58.0
    assert res.notes  # RPE assumption surfaced


def test_half_up_rounds_quarter_up(calc):
    # power_snatch 90% = 82.5 * 0.90 = 74.25 -> half-up to nearest 0.5 -> 74.5
    res = calc.prescribe("power_snatch", Target.percent_of_1rm(90))
    assert res.working_weight_kg == pytest.approx(74.25)
    assert res.prescribed_kg == 74.5


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
