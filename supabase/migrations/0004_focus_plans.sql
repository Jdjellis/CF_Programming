-- The single active focus block (skill or strength) + program pointer + week.
create table if not exists focus (
  id           bigint generated always as identity primary key,
  name         text not null,
  program_ref  text,
  current_week integer not null default 1 check (current_week >= 1),
  started_on   date not null default current_date,
  is_active    boolean not null default true,
  updated_at   timestamptz not null default now()
);
-- Enforce at most one active focus at a time.
create unique index if not exists focus_one_active_idx on focus (is_active) where is_active;

-- Archived weekly plans; chat reads these to answer plan queries.
create table if not exists plans (
  week_of    date primary key,
  spec_json  jsonb not null,
  html       text,
  created_at timestamptz not null default now()
);
