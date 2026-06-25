import pytest


@pytest.mark.supabase
def test_authenticator_can_assume_chat_remote(db):
    with db.cursor() as cur:
        cur.execute(
            "select 1 from pg_auth_members m "
            "join pg_roles r on m.roleid = r.oid "
            "join pg_roles mem on m.member = mem.oid "
            "where r.rolname = 'chat_remote' and mem.rolname = 'authenticator'"
        )
        assert cur.fetchone() is not None
    db.rollback()
