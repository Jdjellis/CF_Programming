"""End-to-end tests: lift + target -> working weight, via the fixture.

The calculator resolves a target to a raw working weight (one_rm * fraction) and
a loadable `prescribed_kg` rounded to the nearest 0.5 kg. There is no plate
math — an experienced lifter loads the bar themselves.
"""

from pathlib import Path

import pytest

from cfprog.calculator import LoadCalculator
from cfprog.maxes import DEFAULT_MAXES_PATH, FixtureMaxesProvider
from cfprog.models import Target

REPO_ROOT = Path(__file__).resolve().parents[5]
TEST_MAXES = Path(__file__).resolve().parent / "fixtures" / "maxes.json"


@pytest.fixture(scope="module")
def calc() -> LoadCalculator:
    # Frozen maxes: the real data/maxes.json changes as the athlete gets stronger.
    return LoadCalculator(FixtureMaxesProvider(TEST_MAXES))


def test_front_squat_85pct(calc):
    res = calc.prescribe("front_squat", Target.percent_of_1rm(85))
    assert res.one_rm_kg == 135
    assert res.working_weight_kg == pytest.approx(114.75)
    assert res.prescribed_kg == 115.0  # nearest 0.5 kg, half-up
    assert res.load_line() == "115 kg (85% of front squat 1RM 135)"


def test_clean_3rm(calc):
    res = calc.prescribe("clean", Target.rep_max(3))
    assert res.one_rm_kg == 124
    assert res.working_weight_kg == pytest.approx(124 * 0.93)  # 115.32
    assert res.prescribed_kg == 115.5  # 115.32 -> nearest 0.5
    assert res.load_line() == "115.5 kg (93% of clean 1RM 124)"


def test_strict_press_rpe8_for_5(calc):
    res = calc.prescribe("strict_press", Target.rpe(reps=5, rpe=8))
    assert res.one_rm_kg == 70
    # 7RM -> 83% of 70 = 58.1 kg -> 58.0 loadable
    assert res.working_weight_kg == pytest.approx(58.1)
    assert res.prescribed_kg == 58.0
    assert res.notes  # RPE assumption surfaced


def test_half_up_rounds_quarter_up(calc):
    # push_press 72.25% = 100 * 0.7225 = 72.25 -> half-up to nearest 0.5 -> 72.5
    res = calc.prescribe("push_press", Target.percent_of_1rm(72.25))
    assert res.working_weight_kg == pytest.approx(72.25)
    assert res.prescribed_kg == 72.5


def test_lift_name_normalisation(calc):
    a = calc.prescribe("Front Squat", Target.percent_of_1rm(85))
    b = calc.prescribe("front_squat", Target.percent_of_1rm(85))
    assert a.one_rm_kg == b.one_rm_kg


def test_clean_and_jerk_is_off_the_limiter(calc):
    # plain jerk = split jerk 124, clean 124: the tie goes to the jerk
    res = calc.prescribe("Clean & Jerk", Target.percent_of_1rm(80))
    assert res.one_rm_kg == 124
    assert res.base == "split jerk 1RM 124, the limiter over clean 124"


@pytest.mark.parametrize("lift", ["Pause Snatch", "block_snatch", "snatch_pull_from_riser", "hang snatch"])
def test_full_snatch_variations_use_snatch(calc, lift):
    res = calc.prescribe(lift, Target.percent_of_1rm(80))
    assert res.one_rm_kg == 88
    assert res.base == "snatch 1RM 88"


@pytest.mark.parametrize("lift", ["power_snatch", "Block Power Snatch", "hang_power_snatch"])
def test_power_snatch_variations_use_power_snatch(calc, lift):
    res = calc.prescribe(lift, Target.percent_of_1rm(80))
    assert res.one_rm_kg == 82.5
    assert res.base == "power snatch 1RM 82.5"


@pytest.mark.parametrize("lift", ["clean_pull_from_riser", "pause_clean", "block clean"])
def test_full_clean_variations_use_clean(calc, lift):
    res = calc.prescribe(lift, Target.percent_of_1rm(80))
    assert res.one_rm_kg == 124
    assert res.base == "clean 1RM 124"


@pytest.mark.parametrize("lift", ["power_clean", "hang_power_clean", "block power clean"])
def test_power_clean_variations_use_power_clean(calc, lift):
    res = calc.prescribe(lift, Target.percent_of_1rm(80))
    assert res.one_rm_kg == 122
    assert res.base == "power clean 1RM 122"


def test_push_jerk_never_comes_from_split_jerk(calc):
    assert calc.prescribe("push_jerk", Target.percent_of_1rm(80)).one_rm_kg == 105
    assert calc.prescribe("split_jerk", Target.percent_of_1rm(80)).one_rm_kg == 124
    assert calc.prescribe("pause jerk", Target.percent_of_1rm(80)).base == "split jerk 1RM 124"


def test_clean_plus_push_jerk_is_off_the_push_jerk(calc):
    res = calc.prescribe("Power Clean + Push Jerk", Target.percent_of_1rm(75))
    assert res.base == "push jerk 1RM 105, the limiter over power clean 122"
    assert res.load_line() == "79 kg (75% of push jerk 1RM 105, the limiter over power clean 122)"


def test_full_clean_plus_split_jerk_uses_the_full_clean(calc):
    res = calc.prescribe("pause clean + pause split jerk", Target.percent_of_1rm(80))
    assert res.base == "split jerk 1RM 124, the limiter over clean 124"


def test_pause_front_squat_uses_front_squat(calc):
    res = calc.prescribe("pause_front_squat", Target.percent_of_1rm(55))
    assert res.base == "front squat 1RM 135"


def test_unknown_lift_raises(calc):
    with pytest.raises(KeyError):
        calc.prescribe("turkish_getup", Target.percent_of_1rm(80))
def test_test_fixture_maxes_are_readable():
    maxes = FixtureMaxesProvider(TEST_MAXES).all_maxes()
    assert maxes["back_squat"] == 165
    assert maxes["power_snatch"] == 82.5


def test_default_maxes_file_is_repo_root_data_maxes_json():
    assert DEFAULT_MAXES_PATH == REPO_ROOT / "data" / "maxes.json"
    assert DEFAULT_MAXES_PATH.is_file()


def test_default_provider_reads_the_coach_maxes_record():
    assert FixtureMaxesProvider().all_maxes()
