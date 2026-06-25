-- e1RM over time for each barbell lift.
create or replace view e1rm_trend as
select exercise as lift, date, est_1rm
from exercise_log
where category = 'barbell' and est_1rm is not null;

-- PR / max progression per lift, from the max_events history.
create or replace view pr_history as
select lift, date, weight_kg as one_rm_kg, source
from max_events;

-- Volume & balance over the last 28 days, per exercise.
create or replace view volume_balance as
select exercise,
       category,
       count(*)                                                as sessions,
       coalesce(sum(reps * coalesce(sets, 1)), 0)              as total_reps,
       coalesce(sum(weight_kg * reps * coalesce(sets, 1)), 0)  as tonnage_kg
from exercise_log
where date >= current_date - interval '28 days'
group by exercise, category;
