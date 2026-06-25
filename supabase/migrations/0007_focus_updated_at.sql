-- Stamp updated_at on every UPDATE. clock_timestamp() (not now()) so the bump is
-- observable even within a single transaction, and reflects real modification time.
create or replace function set_updated_at()
returns trigger language plpgsql as $$
begin
  new.updated_at = clock_timestamp();
  return new;
end;
$$;

drop trigger if exists focus_set_updated_at on focus;
create trigger focus_set_updated_at
  before update on focus
  for each row execute function set_updated_at();
