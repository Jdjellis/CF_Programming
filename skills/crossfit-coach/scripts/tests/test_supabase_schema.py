import pytest


@pytest.mark.supabase
def test_exercise_log_roundtrip(db):
    with db.cursor() as cur:
        cur.execute(
            "insert into exercise_log (exercise, category, weight_kg, reps) "
            "values ('front_squat', 'barbell', 122, 3) returning id, date"
        )
        row_id, the_date = cur.fetchone()
        assert row_id is not None and the_date is not None
    db.rollback()


@pytest.mark.supabase
def test_max_events_roundtrip(db):
    with db.cursor() as cur:
        cur.execute(
            "insert into max_events (lift, weight_kg) values ('back_squat', 165) returning id"
        )
        assert cur.fetchone()[0] is not None
    db.rollback()


@pytest.mark.supabase
def test_current_maxes_latest_wins(db):
    with db.cursor() as cur:
        cur.execute("insert into max_events (lift, weight_kg, date) values ('clean', 120, '2025-01-01')")
        cur.execute("insert into max_events (lift, weight_kg, date) values ('clean', 124, '2025-06-01')")
        cur.execute("select weight_kg from current_maxes where lift = 'clean'")
        assert float(cur.fetchone()[0]) == 124.0
    db.rollback()


@pytest.mark.supabase
def test_est_1rm_column_barbell_only(db):
    with db.cursor() as cur:
        # barbell triple at 122 -> 3RM = 93% -> 122/0.93 = 131.18
        cur.execute(
            "insert into exercise_log (exercise, category, weight_kg, reps) "
            "values ('front_squat', 'barbell', 122, 3) returning est_1rm"
        )
        assert float(cur.fetchone()[0]) == pytest.approx(131.18, abs=0.01)
        # gymnastics sets get no est_1rm
        cur.execute(
            "insert into exercise_log (exercise, category, reps) "
            "values ('strict_hspu', 'gymnastics', 5) returning est_1rm"
        )
        assert cur.fetchone()[0] is None
    db.rollback()
