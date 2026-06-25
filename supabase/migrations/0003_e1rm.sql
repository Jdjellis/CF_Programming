-- Rep-max -> %1RM, verbatim from cfprog.targets.REP_MAX_PCT, clamped to [1,10].
create or replace function cf_rep_max_pct(reps integer)
returns numeric language sql immutable as $$
  select case greatest(1, least(10, reps))
    when 1 then 100.0 when 2 then 95.0 when 3 then 93.0 when 4 then 90.0
    when 5 then 87.0  when 6 then 85.0 when 7 then 83.0 when 8 then 80.0
    when 9 then 77.0  when 10 then 75.0
  end;
$$;

-- Round half-to-even (banker's rounding) to 2 decimals, matching Python's
-- round(x, 2) used by cfprog.estimate. Postgres's built-in round(numeric, 2) is
-- half-away-from-zero and diverges from cfprog by one cent on exact half-cent
-- ties (e.g. 82.5 / 0.80 = 103.125 -> cfprog 103.12, half-away 103.13). e1RM
-- inputs are non-negative; sign()/abs() keep it correct for any input regardless.
-- All arithmetic is exact numeric (the `= 0.5` tie test has no float hazard, and
-- numeric `%` avoids any integer-cast overflow).
create or replace function cf_round_half_even(v numeric)
returns numeric language sql immutable as $$
  select sign(v) * case
    when abs(v) * 100 - floor(abs(v) * 100) = 0.5
      then (case when floor(abs(v) * 100) % 2 = 0
                 then floor(abs(v) * 100)
                 else floor(abs(v) * 100) + 1 end) / 100.0
    else round(abs(v), 2)
  end;
$$;

-- e1RM = weight / fraction. RPE -> RIR = round_half_up(10 - rpe); effective reps
-- = reps + RIR (cf_rep_max_pct clamps). RIR uses Postgres round() (half-away),
-- which equals round-half-up for (10 - rpe) >= 0. The final 2-dp rounding uses
-- cf_round_half_even so the mirror matches Python's round() in cfprog exactly;
-- Postgres's half-away round() would diverge by a cent on exact half-cent ties.
create or replace function cf_est_1rm(weight_kg numeric, reps integer, rpe numeric default null)
returns numeric language sql immutable as $$
  select cf_round_half_even(
    weight_kg / (
      cf_rep_max_pct(reps + case when rpe is null then 0 else round(10 - rpe)::int end) / 100.0
    )
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
