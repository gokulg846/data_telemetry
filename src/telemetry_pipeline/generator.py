from datetime import datetime, timedelta, timezone
import math
import random
import uuid
from typing import Dict, List, Optional


STATUSES = ("healthy", "warning", "critical")


def classify_status(temperature: float, vibration: float, pressure: float) -> str:
    critical = temperature >= 92 or vibration >= 9 or not 3.5 <= pressure <= 7.0
    warning = temperature >= 82 or vibration >= 6 or not 4.0 <= pressure <= 6.5
    return "critical" if critical else "warning" if warning else "healthy"


def generate_events(
    count: int = 500,
    *,
    seed: int = 42,
    start_at: Optional[datetime] = None,
    machine_count: int = 12,
) -> List[Dict]:
    """Generate deterministic, realistic telemetry with periodic degradation."""
    rng = random.Random(seed)
    start = start_at or datetime.now(timezone.utc) - timedelta(minutes=count)
    events: List[Dict] = []

    for index in range(count):
        machine_number = index % machine_count + 1
        machine_id = f"M-{machine_number:03d}"
        line_id = f"LINE-{(machine_number - 1) // 4 + 1}"
        event_ts = start + timedelta(minutes=index)
        cycle = math.sin(index / 18)
        degrading = machine_number in (3, 9)
        degradation = max(0, index - count * 0.45) / count * 7 if degrading else 0

        temperature = 68 + cycle * 4 + rng.gauss(0, 1.8) + degradation * 1.8
        vibration = 2.5 + abs(cycle) + rng.gauss(0, 0.45) + degradation
        pressure = 5.2 + rng.gauss(0, 0.3)
        power = 38 + cycle * 5 + rng.gauss(0, 2.0) + degradation * 1.4

        # Rare spikes make the anomaly mart useful even in a small demo batch.
        if rng.random() < 0.025:
            temperature += rng.uniform(15, 25)
            vibration += rng.uniform(4, 7)

        status = classify_status(temperature, vibration, pressure)
        identity = f"{event_ts.isoformat()}:{machine_id}:{seed}"
        event = {
            "event_id": str(uuid.uuid5(uuid.NAMESPACE_URL, identity)),
            "event_ts": event_ts.isoformat(),
            "machine_id": machine_id,
            "line_id": line_id,
            "temperature_c": round(temperature, 2),
            "vibration_mm_s": round(max(0, vibration), 2),
            "pressure_bar": round(pressure, 2),
            "power_kw": round(max(0, power), 2),
            "status": status,
            "schema_version": 1,
        }
        events.append(event)

    return events
