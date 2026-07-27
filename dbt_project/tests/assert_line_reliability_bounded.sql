select *
from {{ ref('mart_line_reliability') }}
where healthy_event_pct not between 0 and 100
