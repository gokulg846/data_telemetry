select *
from {{ ref('stg_telemetry_events') }}
where temperature_c not between -40 and 180
   or vibration_mm_s < 0
   or pressure_bar < 0
   or power_kw < 0
