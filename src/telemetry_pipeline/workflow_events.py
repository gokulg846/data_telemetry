"""Durable Project 3 event delivery. Run independently to retry pending events."""

import json
import os
from datetime import datetime, timezone

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
        attempts integer NOT NULL DEFAULT 0
    )""")


def enqueue_failure(run_id, started_at, description):
    event = {
        "schema_version": 1, "event_id": f"pipeline-{run_id}",
        "event_type": "pipeline_failure", "observed_at": started_at.isoformat(),
        "machine_id": None, "line_id": None,
        "source_ref": f"raw.pipeline_runs:{run_id}",
        "description": description[:2000],
    }
    with psycopg.connect(Settings().postgres_dsn) as conn:
        ensure_outbox(conn)
        conn.execute("INSERT INTO raw.workflow_outbox (event_id, payload) VALUES (%s, %s) "
                     "ON CONFLICT DO NOTHING", (event["event_id"], Jsonb(event)))


def enqueue_anomalies():
    """Catch up undispatched mart rows in bounded batches; event identity is stable."""
    with psycopg.connect(Settings().postgres_dsn, row_factory=dict_row) as conn:
        ensure_outbox(conn)
        rows = conn.execute("""SELECT a.* FROM analytics.mart_anomaly_events a
            LEFT JOIN raw.workflow_outbox o ON o.event_id = 'sensor-' || a.event_id::text
            WHERE o.event_id IS NULL ORDER BY a.event_ts LIMIT 1000""").fetchall()
        for row in rows:
            event = {
                "schema_version": 1, "event_id": f"sensor-{row['event_id']}",
                "event_type": "sensor_anomaly", "observed_at": row["event_ts"].isoformat(),
                "machine_id": row["machine_id"], "line_id": row["line_id"],
                "source_ref": f"analytics.mart_anomaly_events:{row['event_id']}",
                "description": f"{row['anomaly_type']}; observed status={row['status']}",
            }
            conn.execute("INSERT INTO raw.workflow_outbox (event_id, payload) VALUES (%s, %s) "
                         "ON CONFLICT DO NOTHING", (event["event_id"], Jsonb(event)))
    return len(rows)


def publish_pending():
    url, token = os.getenv("WORKFLOW_URL", ""), os.getenv("WORKFLOW_TOKEN", "")
    if not url:
        return 0
    if not token:
        raise ValueError("WORKFLOW_TOKEN is required when WORKFLOW_URL is set")
    with psycopg.connect(Settings().postgres_dsn, row_factory=dict_row) as conn:
        ensure_outbox(conn)
        rows = conn.execute("SELECT event_id, payload FROM raw.workflow_outbox "
                            "WHERE delivered_at IS NULL ORDER BY created_at LIMIT 100").fetchall()
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
                         "WHERE event_id=%s", (error, error is None, row['event_id']))
        delivered += error is None
    return delivered


def main():
    # Retry the outbox even if the mart is temporarily unavailable.
    delivered = publish_pending()
    queued = enqueue_anomalies()
    delivered += publish_pending()
    print(json.dumps({"queued": queued, "delivered": delivered,
                      "at": datetime.now(timezone.utc).isoformat()}))


if __name__ == '__main__':
    main()
