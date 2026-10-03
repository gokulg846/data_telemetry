from datetime import datetime, timezone
import json
import logging
import os
from typing import Dict, Iterable, List, Tuple
import uuid

import boto3
from botocore.config import Config
from botocore.exceptions import ClientError
import psycopg
from tenacity import retry, stop_after_attempt, wait_exponential

from .config import Settings

LOGGER = logging.getLogger(__name__)
EXPECTED_KEYS = {
    "event_id", "event_ts", "machine_id", "line_id", "temperature_c",
    "vibration_mm_s", "pressure_bar", "power_kw", "status", "schema_version",
}

BOOTSTRAP_SQL = """
CREATE SCHEMA IF NOT EXISTS raw;
CREATE SCHEMA IF NOT EXISTS analytics;
CREATE TABLE IF NOT EXISTS raw.telemetry_events (
    event_id UUID PRIMARY KEY,
    event_ts TIMESTAMPTZ NOT NULL,
    machine_id TEXT NOT NULL,
    line_id TEXT NOT NULL,
    temperature_c DOUBLE PRECISION NOT NULL,
    vibration_mm_s DOUBLE PRECISION NOT NULL,
    pressure_bar DOUBLE PRECISION NOT NULL,
    power_kw DOUBLE PRECISION NOT NULL,
    status TEXT NOT NULL,
    schema_version INTEGER NOT NULL,
    raw_payload JSONB NOT NULL,
    ingested_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE TABLE IF NOT EXISTS raw.pipeline_runs (
    run_id UUID PRIMARY KEY,
    started_at TIMESTAMPTZ NOT NULL,
    finished_at TIMESTAMPTZ,
    status TEXT NOT NULL,
    events_processed INTEGER NOT NULL DEFAULT 0,
    raw_object_key TEXT,
    error_message TEXT
);
"""


def detect_schema_drift(events: Iterable[Dict]) -> Tuple[set, set]:
    seen = set().union(*(event.keys() for event in events))
    return seen - EXPECTED_KEYS, EXPECTED_KEYS - seen


def s3_client(settings: Settings):
    options = {
        "endpoint_url": settings.s3_endpoint_url or None,
        "region_name": settings.s3_region,
        "config": Config(retries={"max_attempts": 4, "mode": "adaptive"}),
    }
    # Local MinIO uses explicit credentials. In AWS, omit them so boto3 uses
    # the ECS task role rather than long-lived keys.
    if settings.s3_endpoint_url:
        options.update(
            aws_access_key_id=settings.s3_access_key,
            aws_secret_access_key=settings.s3_secret_key,
        )
    return boto3.client("s3", **options)


@retry(stop=stop_after_attempt(4), wait=wait_exponential(multiplier=1, min=1, max=8), reraise=True)
def ensure_warehouse(settings: Settings) -> None:
    """Create raw contracts for both fresh Docker and fresh RDS databases."""
    with psycopg.connect(settings.postgres_dsn) as connection:
        for statement in BOOTSTRAP_SQL.split(";"):
            if statement.strip():
                connection.execute(statement)


@retry(stop=stop_after_attempt(4), wait=wait_exponential(multiplier=1, min=1, max=8), reraise=True)
def land_raw_batch(events: List[Dict], settings: Settings) -> str:
    extra, missing = detect_schema_drift(events)
    if extra or missing:
        LOGGER.warning("Schema drift detected: extra=%s missing=%s", sorted(extra), sorted(missing))

    client = s3_client(settings)
    try:
        client.head_bucket(Bucket=settings.s3_bucket)
    except ClientError:
        client.create_bucket(Bucket=settings.s3_bucket)

    now = datetime.now(timezone.utc)
    key = (
        f"year={now:%Y}/month={now:%m}/day={now:%d}/hour={now:%H}/"
        f"batch-{uuid.uuid4()}.ndjson"
    )
    body = "\n".join(json.dumps(event, separators=(",", ":")) for event in events) + "\n"
    client.put_object(
        Bucket=settings.s3_bucket,
        Key=key,
        Body=body.encode(),
        ContentType="application/x-ndjson",
        Metadata={"event-count": str(len(events)), "schema-version": "1"},
    )
    return key


@retry(stop=stop_after_attempt(4), wait=wait_exponential(multiplier=1, min=1, max=8), reraise=True)
def load_events(events: List[Dict], settings: Settings) -> int:
    ensure_warehouse(settings)
    statement = """
        INSERT INTO raw.telemetry_events (
            event_id, event_ts, machine_id, line_id, temperature_c,
            vibration_mm_s, pressure_bar, power_kw, status, schema_version, raw_payload
        ) VALUES (
            %(event_id)s, %(event_ts)s, %(machine_id)s, %(line_id)s, %(temperature_c)s,
            %(vibration_mm_s)s, %(pressure_bar)s, %(power_kw)s, %(status)s,
            %(schema_version)s, %(raw_payload)s
        )
        ON CONFLICT (event_id) DO NOTHING
    """
    rows = [{**event, "raw_payload": json.dumps(event)} for event in events]
    with psycopg.connect(settings.postgres_dsn) as connection:
        with connection.cursor() as cursor:
            cursor.executemany(statement, rows)
            inserted = cursor.rowcount
            if os.getenv("WORKFLOW_URL"):
                from .workflow_events import ensure_outbox, stage_sensor

                ensure_outbox(connection)
                for row in events:
                    stage_sensor(connection, row)
            return inserted
