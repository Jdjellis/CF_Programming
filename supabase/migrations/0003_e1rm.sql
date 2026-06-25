-- Rep-max -> %1RM, verbatim from cfprog.targets.REP_MAX_PCT, clamped to [1,10].
create or replace function cf_rep_max_pct(reps integer)
returns numeric language sql immutable as $$
  select case greatest(1, least(10, reps))
    when 1 then 100.0 when 2 then 95.0 when 3 then 93.0 when 4 then 90.0
    when 5 then 87.0  when 6 then 85.0 when 7 then 83.0 when 8 then 80.0
    when 9 then 77.0  when 10 then 75.0
  end;
$$;

-- e1RM = weight / fraction. RPE -> RIR = round_half_up(10 - rpe); effective reps
-- = reps + RIR (cf_rep_max_pct clamps). Postgres round() is half-away-from-zero,
-- which equals round-half-up for (10 - rpe) >= 0.
create or replace function cf_est_1rm(weight_kg numeric, reps integer, rpe numeric default null)
returns numeric language sql immutable as $$
  select round(
    weight_kg / (
      cf_rep_max_pct(reps + case when rpe is null then 0 else round(10 - rpe)::int end) / 100.0
    ),
    2
  );
$$;

-- Stored estimate, only for barbell sets carrying weight + reps.
alter table exercise_log
  add column if not exists est_1rm numeric
  generated always as (
    case when category = 'barbell' and weight_kg is not null and reps is not null
         then cf_est_1rm(weight_kg, reps, rpe)
    end
  ) stored;
