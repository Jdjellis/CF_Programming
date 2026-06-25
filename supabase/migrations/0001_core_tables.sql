-- Append-only log of performed sets, any exercise category.
create table if not exists exercise_log (
  id            bigint generated always as identity primary key,
  date          date not null default current_date,
  created_at    timestamptz not null default now(),
  exercise      text not null,
  category      text not null check (category in ('barbell','gymnastics','accessory','other')),
  weight_kg     numeric,
  reps          integer,
  sets          integer,
  time_seconds  integer,
  rpe           numeric check (rpe is null or (rpe >= 1 and rpe <= 10)),
  assistance    text,
  added_load_kg numeric,
  is_focus_work boolean not null default false,
  note          text
);

-- Each change to a barbell 1RM; the current value is derived by a view (Task 2).
create table if not exists max_events (
  id         bigint generated always as identity primary key,
  lift       text not null,
  weight_kg  numeric not null check (weight_kg > 0),
  date       date not null default current_date,
  source     text not null default 'manual',
  created_at timestamptz not null default now()
);
create index if not exists max_events_lift_date_idx on max_events (lift, date desc, id desc);
