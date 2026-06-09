"""Tests for the SQLite logging layer."""

import pytest

from cfprog.calculator import LoadCalculator
from cfprog.logstore import LoggedSet, ReadinessEntry, SQLiteLogStore
from cfprog.models import Target


@pytest.fixture
def store():
    s = SQLiteLogStore(":memory:")
    yield s
    s.close()


def test_log_and_read_set(store):
    out = store.log_set(LoggedSet(lift="front_squat", weight_kg=115, reps=3, rpe=8))
    assert out.id == 1
    assert out.created_at is not None
    rows = store.sets()
    assert len(rows) == 1
    assert rows[0].lift == "front_squat"
    assert rows[0].weight_kg == 115
    assert rows[0].tonnage_kg == 345


def test_lift_name_normalised_on_log(store):
    store.log_set(LoggedSet(lift="Front Squat", weight_kg=100, reps=5))
    assert store.sets(lift="front_squat")[0].weight_kg == 100


def test_filter_by_lift_and_date(store):
    store.log_set(LoggedSet(lift="clean", weight_kg=100, reps=1, date="2026-01-01"))
    store.log_set(LoggedSet(lift="clean", weight_kg=110, reps=1, date="2026-02-01"))
    store.log_set(LoggedSet(lift="snatch", weight_kg=80, reps=1, date="2026-02-01"))
    assert len(store.sets(lift="clean")) == 2
    assert len(store.sets(since="2026-01-15")) == 2
    assert len(store.sets(lift="clean", since="2026-01-15")) == 1


def test_readiness_one_row_per_day_latest_wins(store):
    store.log_readiness(ReadinessEntry(tier="amber", date="2026-03-01", score=60))
    store.log_readiness(ReadinessEntry(tier="green", date="2026-03-01", score=80))
    rows = store.readiness()
    assert len(rows) == 1
    assert rows[0].tier == "green"
    assert rows[0].score == 80


def test_latest_readiness(store):
    store.log_readiness(ReadinessEntry(tier="red", date="2026-03-01"))
    store.log_readiness(ReadinessEntry(tier="green", date="2026-03-05"))
    assert store.latest_readiness().tier == "green"
    assert store.latest_readiness(on_date="2026-03-03").tier == "red"
    assert store.latest_readiness(on_date="2026-02-01") is None


def test_from_prescription_records_calculator_output(store):
    calc = LoadCalculator()
    res = calc.prescribe("front_squat", Target.percent_of_1rm(85))
    entry = store.log_set(
        LoggedSet.from_prescription(res, reps=3, rpe=8, readiness="green")
    )
    # weight defaults to the loadable weight the calculator produced
    assert entry.weight_kg == res.loadout.achieved_kg == 115.0
    assert entry.prescribed_weight_kg == pytest.approx(114.75)
    assert entry.target_desc == "85% of 1RM"
    assert entry.readiness == "green"


def test_persists_across_connections(tmp_path):
    db = tmp_path / "t.db"
    s1 = SQLiteLogStore(db)
    s1.log_set(LoggedSet(lift="deadlift", weight_kg=200, reps=2))
    s1.close()
    s2 = SQLiteLogStore(db)
    assert len(s2.sets(lift="deadlift")) == 1
    s2.close()


def test_validation():
    with pytest.raises(ValueError):
        LoggedSet(lift="clean", weight_kg=100, reps=0)
    with pytest.raises(ValueError):
        LoggedSet(lift="clean", weight_kg=100, reps=1, rpe=11)
    with pytest.raises(ValueError):
        ReadinessEntry(tier="purple")
