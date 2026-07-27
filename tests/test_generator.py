from datetime import datetime, timezone

from telemetry_pipeline.generator import STATUSES, classify_status, generate_events
from telemetry_pipeline.storage import detect_schema_drift


def test_generator_is_deterministic_and_schema_is_stable():
    start = datetime(2026, 1, 1, tzinfo=timezone.utc)
    first = generate_events(20, seed=7, start_at=start)
    second = generate_events(20, seed=7, start_at=start)

    assert first == second
    assert len({event["event_id"] for event in first}) == 20
    assert {event["status"] for event in first}.issubset(STATUSES)
    assert detect_schema_drift(first) == (set(), set())


def test_status_thresholds():
    assert classify_status(70, 2, 5) == "healthy"
    assert classify_status(83, 2, 5) == "warning"
    assert classify_status(93, 2, 5) == "critical"
