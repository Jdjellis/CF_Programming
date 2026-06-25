import psycopg
import pytest


@pytest.mark.supabase
def test_chat_remote_can_log_and_read_views(db):
    with db.cursor() as cur:
        cur.execute("set role chat_remote")
        cur.execute("insert into exercise_log (exercise, category, weight_kg, reps) "
                    "values ('front_squat','barbell',100,3)")
        cur.execute("select count(*) from current_maxes")
        assert cur.fetchone()[0] is not None
        cur.execute("reset role")
    db.rollback()


@pytest.mark.supabase
def test_chat_remote_cannot_delete_or_read_raw_maxes(db):
    with db.cursor() as cur:
        cur.execute("set role chat_remote")
        cur.execute("savepoint sp")
        with pytest.raises(psycopg.errors.InsufficientPrivilege):
            cur.execute("delete from exercise_log")
        cur.execute("rollback to savepoint sp")
        with pytest.raises(psycopg.errors.InsufficientPrivilege):
            cur.execute("select * from max_events")
        cur.execute("rollback to savepoint sp")
        cur.execute("reset role")
    db.rollback()
