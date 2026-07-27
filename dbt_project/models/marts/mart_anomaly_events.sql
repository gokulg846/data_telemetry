select
    event_id,
    event_ts,
    machine_id,
    line_id,
    status,
    temperature_c,
    vibration_mm_s,
    pressure_bar,
    power_kw,
    case
        when temperature_c >= 92 then 'high_temperature'
        when vibration_mm_s >= 9 then 'high_vibration'
        when pressure_bar not between 3.5 and 7.0 then 'pressure_out_of_range'
        when status = 'warning' then 'warning_threshold'
        else 'normal'
    end as anomaly_type
from {{ ref('int_machine_signals') }}
where status in ('warning', 'critical')
