-- Restricted role the chat connector authenticates as. Views run with their
-- owner's privileges, so granting SELECT on the views lets chat_remote read
-- analytics without direct access to the underlying max_events/exercise_log.
do $$
begin
  if not exists (select 1 from pg_roles where rolname = 'chat_remote') then
    create role chat_remote nologin;
  end if;
end
$$;

grant usage on schema public to chat_remote;
grant select on current_maxes, e1rm_trend, pr_history, volume_balance, plans to chat_remote;
grant insert on exercise_log to chat_remote;
grant update (current_week, is_active, updated_at) on focus to chat_remote;

-- Role-MEMBERSHIP grant (not a privilege grant): lets the postgres role SET ROLE
-- into chat_remote. Required because Supabase's postgres is not a superuser, so the
-- tests (and local psql) cannot assume chat_remote without membership. This does NOT
-- widen chat_remote's own privileges.
-- NOTE: granting membership to the Supabase `authenticator` (PostgREST) role is how
-- the chat connector will assume chat_remote in production; that connector wiring is
-- deferred to Plan 3, so it is intentionally not granted here.
grant chat_remote to postgres;
