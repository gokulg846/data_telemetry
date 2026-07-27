with ranked as (
    select
        *,
        row_number() over (partition by machine_id order by event_ts desc) as recency_rank
    from {{ ref('int_machine_signals') }}
)
select
    machine_id,
    line_id,
    event_ts as latest_event_ts,
    status as latest_status,
    temperature_c,
    vibration_mm_s,
    pressure_bar,
    power_kw,
    vibration_20_event_avg,
    vibration_mm_s - vibration_10_events_ago as vibration_change_10_events,
    case
        when status = 'critical' then 100
        when status = 'warning' then 60
        when vibration_mm_s - vibration_10_events_ago >= 2 then 45
        else 10
    end as risk_score
from ranked
where recency_rank = 1
