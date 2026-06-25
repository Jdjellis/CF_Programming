import pytest


@pytest.mark.supabase
def test_only_one_active_focus(db):
    with db.cursor() as cur:
        cur.execute("insert into focus (name, program_ref) values ('ring_mu', 'drills/ring-mu-kipping.md')")
        cur.execute("savepoint sp")
        with pytest.raises(Exception):  # unique partial index on is_active
            cur.execute("insert into focus (name) values ('hspu')")
        cur.execute("rollback to savepoint sp")
    db.rollback()


@pytest.mark.supabase
def test_plans_upsert_by_week(db):
    with db.cursor() as cur:
        cur.execute("insert into plans (week_of, spec_json) values ('2026-06-08', '{\"v\":1}')")
        cur.execute(
            "insert into plans (week_of, spec_json) values ('2026-06-08', '{\"v\":2}') "
            "on conflict (week_of) do update set spec_json = excluded.spec_json"
        )
        cur.execute("select spec_json->>'v' from plans where week_of = '2026-06-08'")
        assert cur.fetchone()[0] == '2'
    db.rollback()
