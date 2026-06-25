import pytest


@pytest.mark.supabase
def test_neglected_lifts_flags_and_clears(db):
    with db.cursor() as cur:
        cur.execute("insert into max_events (lift, weight_kg) values ('strict_press', 70)")
        # never logged -> neglected
        cur.execute("select lift from neglected_lifts(14)")
        assert ('strict_press',) in cur.fetchall()
        # log it today -> clears
        cur.execute("insert into exercise_log (exercise, category, weight_kg, reps) "
                    "values ('strict_press', 'barbell', 60, 5)")
        cur.execute("select lift from neglected_lifts(14)")
        assert ('strict_press',) not in cur.fetchall()
    db.rollback()
