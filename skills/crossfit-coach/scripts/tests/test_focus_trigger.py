import pytest


@pytest.mark.supabase
def test_focus_updated_at_bumps_on_update(db):
    with db.cursor() as cur:
        cur.execute("insert into focus (name) values ('ring_mu') returning updated_at")
        before = cur.fetchone()[0]
        cur.execute(
            "update focus set current_week = current_week + 1 "
            "where name = 'ring_mu' returning updated_at"
        )
        after = cur.fetchone()[0]
        assert after > before
    db.rollback()
