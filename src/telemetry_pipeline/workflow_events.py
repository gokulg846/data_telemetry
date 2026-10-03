"""Durable Project 3 event delivery. Run independently to retry pending events."""

import json
import os
import argparse
import time
import hashlib
from datetime import datetime, timezone, timedelta

import psycopg
from psycopg.rows import dict_row
from psycopg.types.json import Jsonb
import requests

from telemetry_pipeline.config import Settings


def ensure_outbox(conn):
    conn.execute("""CREATE TABLE IF NOT EXISTS raw.workflow_outbox (
        event_id text PRIMARY KEY, payload jsonb NOT NULL,
        created_at timestamptz NOT NULL DEFAULT now(),
        delivered_at timestamptz, last_error text,
        next_attempt_at timestamptz NOT NULL DEFAULT now(),
        attempts integer NOT NULL DEFAULT 0
    )""")
    conn.execute("ALTER TABLE raw.workflow_outbox ADD COLUMN IF NOT EXISTS next_attempt_at timestamptz NOT NULL DEFAULT now()")


def stage_event(conn, event):
    conn.execute("INSERT INTO raw.workflow_outbox (event_id, payload) VALUES (%s, %s) "
                 "ON CONFLICT DO NOTHING", (event["event_id"], Jsonb(event)))


def stage_failure(conn, run_id, observed_at, event_type="pipeline_failure"):
    ensure_outbox(conn)
    stage_event(conn, {
        "schema_version": 1, "event_id": f"pipeline-{run_id}",
        "event_type": event_type, "observed_at": observed_at.isoformat(),
        "machine_id": None, "line_id": None, "source_ref": f"raw.pipeline_runs:{run_id}",
        "description": "dbt build/freshness failed; investigate pipeline history."
        if event_type == "dbt_failure" else "Pipeline execution failed; investigate run history.",
    })


def stage_sensor(conn, row):
    if row["status"] not in ("warning", "critical"):
        return
    anomaly = ("high_temperature" if row["temperature_c"] >= 92 else
               "high_vibration" if row["vibration_mm_s"] >= 9 else
               "pressure_out_of_range" if not 3.5 <= row["pressure_bar"] <= 7 else
               "warning_threshold" if row["status"] == "warning" else "normal")
    stamp = row["event_ts"]
    stage_event(conn, {
        "schema_version": 1, "event_id": f"sensor-{row['event_id']}",
        "event_type": "sensor_anomaly", "observed_at": stamp.isoformat() if hasattr(stamp, "isoformat") else stamp,
        "machine_id": row["machine_id"], "line_id": row["line_id"],
        "source_ref": f"analytics.mart_anomaly_events:{row['event_id']}",
        "description": f"{anomaly}; observed status={row['status']}",
    })


def enqueue_anomalies():
    # Raw records survive dbt mart replacement and are also archived in object storage.
    with psycopg.connect(Settings().postgres_dsn, row_factory=dict_row) as conn:
        ensure_outbox(conn)
        rows = conn.execute("""SELECT a.* FROM raw.telemetry_events a
            LEFT JOIN raw.workflow_outbox o ON o.event_id = 'sensor-' || a.event_id::text
            WHERE o.event_id IS NULL AND a.status IN ('warning', 'critical')
            ORDER BY a.event_ts LIMIT 1000""").fetchall()
        for row in rows:
            stage_sensor(conn, row)
    return len(rows)


def enqueue_stale(stale_seconds=900):
    now = datetime.now(timezone.utc)
    with psycopg.connect(Settings().postgres_dsn, row_factory=dict_row) as conn:
        ensure_outbox(conn)
        # One event per equipment outage, keyed by the last real reading, not poll time.
        rows = conn.execute("""SELECT DISTINCT ON (machine_id) machine_id, line_id,
            event_id, event_ts FROM raw.telemetry_events ORDER BY machine_id, event_ts DESC""").fetchall()
        count = 0
        for row in rows:
            deadline = row["event_ts"] + timedelta(seconds=stale_seconds)
            if deadline > now:
                continue
            key = hashlib.sha256(f"{row['machine_id']}:{row['event_id']}:{stale_seconds}".encode()).hexdigest()
            stage_event(conn, {
                "schema_version": 1, "event_id": "stale-" + key,
                "event_type": "data_stale", "observed_at": deadline.isoformat(),
                "machine_id": row["machine_id"], "line_id": row["line_id"],
                "source_ref": f"raw.telemetry_events:{row['event_id']}",
                "description": f"No new telemetry within {stale_seconds} seconds after the last reading.",
            })
            count += 1
        # Fleet-wide absence before any machine has registered is a distinct incident.
        if not rows:
            stamp = conn.execute("SELECT min(started_at) AS stamp FROM raw.pipeline_runs").fetchone()["stamp"]
            if stamp and stamp + timedelta(seconds=stale_seconds) <= now:
                stage_event(conn, {"schema_version": 1, "event_id": "stale-empty-warehouse",
                    "event_type": "data_stale", "observed_at": (stamp + timedelta(seconds=stale_seconds)).isoformat(),
                    "machine_id": None, "line_id": None, "source_ref": "raw.telemetry_events:empty",
                    "description": "No telemetry has arrived since pipeline initialization."})
    return count


def publish_pending():
    url, token = os.getenv("WORKFLOW_URL", ""), os.getenv("WORKFLOW_TOKEN", "")
    if not url:
        return 0
    if not token:
        raise ValueError("WORKFLOW_TOKEN is required when WORKFLOW_URL is set")
    with psycopg.connect(Settings().postgres_dsn, row_factory=dict_row) as conn:
        ensure_outbox(conn)
        rows = conn.execute("SELECT event_id, payload FROM raw.workflow_outbox "
                            "WHERE delivered_at IS NULL AND next_attempt_at <= now() ORDER BY next_attempt_at, created_at LIMIT 100").fetchall()
    delivered = 0
    for row in rows:
        error = None
        try:
            response = requests.post(url.rstrip('/') + '/anomaly-events', json=row['payload'],
                                     headers={"Authorization": f"Bearer {token}"}, timeout=10)
            response.raise_for_status()
            if response.status_code not in (200, 202) or not response.json().get('job_id'):
                raise ValueError("Unexpected intake acknowledgement")
        except (requests.RequestException, ValueError):
            # Never persist a credential-bearing URL or raw HTTP response.
            error = "workflow_delivery_failed"
        with psycopg.connect(Settings().postgres_dsn) as conn:
            conn.execute("UPDATE raw.workflow_outbox SET attempts=attempts+1, last_error=%s, "
                         "delivered_at=CASE WHEN %s THEN now() ELSE delivered_at END "
                         " , next_attempt_at=now() + LEAST(3600, power(2, LEAST(attempts+1, 12))) * interval '1 second' "
                         "WHERE event_id=%s", (error, error is None, row['event_id']))
        delivered += error is None
    return delivered


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--watch", action="store_true", help="Continuously publish and detect stale data")
    parser.add_argument("--interval", type=int, default=30)
    parser.add_argument("--stale-seconds", type=int, default=900)
    args = parser.parse_args()
    if args.interval < 1 or args.stale_seconds < 1:
        parser.error("interval and stale-seconds must be positive")
    while True:
        counts = {}
        for name, action in [("delivered", publish_pending), ("queued", enqueue_anomalies),
                             ("stale", lambda: enqueue_stale(args.stale_seconds))]:
            try:
                counts[name] = action()
            except (psycopg.Error, requests.RequestException):
                counts[name] = "unavailable; retry scheduled"
        print(json.dumps(counts), flush=True)
        if not args.watch:
            break
        time.sleep(args.interval)


if __name__ == '__main__':
    main()
