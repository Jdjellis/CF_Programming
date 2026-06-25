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
