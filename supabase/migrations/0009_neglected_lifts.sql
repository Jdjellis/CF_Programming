-- Barbell lifts with a current max but no barbell log within `days` (or never).
create or replace function neglected_lifts(days integer default 14)
returns table(lift text, last_logged date)
language sql stable as $$
  select m.lift, max(e.date) as last_logged
  from current_maxes m
  left join exercise_log e
    on e.exercise = m.lift and e.category = 'barbell'
  group by m.lift
  having max(e.date) is null
      or max(e.date) < current_date - make_interval(days => days);
$$;
