-- The active focus + drift signals the planner reads to steward it.
create or replace view focus_status as
select f.name,
       f.program_ref,
       f.current_week,
       f.started_on,
       (current_date - f.started_on) as days_in,
       (select max(e.date) from exercise_log e where e.is_focus_work) as last_focus_log,
       (current_date - coalesce(
          (select max(e.date) from exercise_log e where e.is_focus_work),
          f.started_on)) as days_since_focus_work
from focus f
where f.is_active;

-- Chat may answer "what's my focus / am I behind on it?".
grant select on focus_status to chat_remote;
