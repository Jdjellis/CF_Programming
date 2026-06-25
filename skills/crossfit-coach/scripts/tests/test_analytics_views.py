import pytest


@pytest.mark.supabase
def test_e1rm_trend_lists_barbell_estimates(db):
    with db.cursor() as cur:
        cur.execute("insert into exercise_log (exercise, category, weight_kg, reps, date) "
                    "values ('front_squat','barbell',120,3,'2026-06-01')")
        cur.execute("insert into exercise_log (exercise, category, weight_kg, reps, date) "
                    "values ('front_squat','barbell',124,3,'2026-06-15')")
        cur.execute("select count(*), max(est_1rm) from e1rm_trend where lift = 'front_squat'")
        n, best = cur.fetchone()
        assert n == 2 and float(best) == pytest.approx(133.33, abs=0.01)
    db.rollback()


@pytest.mark.supabase
def test_volume_balance_groups_recent_work(db):
    with db.cursor() as cur:
        cur.execute("insert into exercise_log (exercise, category, weight_kg, reps, sets) "
                    "values ('front_squat','barbell',100,5,3)")
        cur.execute("select sessions, total_reps, tonnage_kg from volume_balance "
                    "where exercise = 'front_squat'")
        sessions, total_reps, tonnage = cur.fetchone()
        assert sessions == 1 and total_reps == 15 and float(tonnage) == 1500.0
    db.rollback()
