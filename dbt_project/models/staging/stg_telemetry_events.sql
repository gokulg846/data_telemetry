select
    event_id,
    event_ts,
    machine_id,
    line_id,
    temperature_c,
    vibration_mm_s,
    pressure_bar,
    power_kw,
    lower(status) as status,
    schema_version,
    ingested_at
from {{ source('raw', 'telemetry_events') }}
