select
    date_trunc('hour', event_ts) as event_hour,
    line_id,
    count(*) as event_count,
    count(*) filter (where status = 'healthy') as healthy_event_count,
    round(
        count(*) filter (where status = 'healthy')::numeric / nullif(count(*), 0) * 100,
        2
    ) as healthy_event_pct,
    (
        count(*) filter (where status = 'healthy')::numeric / nullif(count(*), 0)
    ) >= 0.98 as meets_slo
from {{ ref('stg_telemetry_events') }}
group by 1, 2
