-- Current 1RM per lift = the most recent max_event (by date, then id).
create or replace view current_maxes as
select distinct on (lift)
       lift, weight_kg, date, source
from max_events
order by lift, date desc, id desc;
