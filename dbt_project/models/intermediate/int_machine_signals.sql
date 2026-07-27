select
    *,
    avg(vibration_mm_s) over (
        partition by machine_id
        order by event_ts
        rows between 19 preceding and current row
    ) as vibration_20_event_avg,
    avg(temperature_c) over (
        partition by machine_id
        order by event_ts
        rows between 19 preceding and current row
    ) as temperature_20_event_avg,
    lag(vibration_mm_s, 10) over (
        partition by machine_id order by event_ts
    ) as vibration_10_events_ago
from {{ ref('stg_telemetry_events') }}
