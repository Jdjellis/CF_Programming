import pytest


@pytest.mark.supabase
def test_focus_status_reports_active_focus_and_drift(db):
    with db.cursor() as cur:
        cur.execute("insert into focus (name, program_ref, current_week, started_on) "
                    "values ('ring_mu', 'drills/ring-mu-kipping.md', 3, current_date - 20)")
        # a focus-work log 5 days ago
        cur.execute("insert into exercise_log (exercise, category, reps, is_focus_work, date) "
                    "values ('ring_muscle_up', 'gymnastics', 3, true, current_date - 5)")
        cur.execute("select name, current_week, days_since_focus_work from focus_status")
        name, week, drift = cur.fetchone()
        assert name == 'ring_mu' and week == 3 and drift == 5
    db.rollback()
