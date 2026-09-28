from datetime import datetime, timezone
import os
from pathlib import Path
import subprocess
import sys
import uuid

from prefect import flow, task
import psycopg
import requests

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPOSITORY_ROOT / "src"))

from telemetry_pipeline.config import Settings  # noqa: E402
from telemetry_pipeline.generator import generate_events  # noqa: E402
from telemetry_pipeline.storage import ensure_warehouse, land_raw_batch, load_events  # noqa: E402


@task(retries=3, retry_delay_seconds=[2, 5, 10])
def ingest_task(event_count: int, seed: int):
    settings = Settings()
    events = generate_events(event_count, seed=seed)
    key = land_raw_batch(events, settings)
    inserted = load_events(events, settings)
    return {"generated": len(events), "inserted": inserted, "object_key": key}


@task
def dbt_build_task() -> None:
    executable = REPOSITORY_ROOT / ".venv" / "bin" / "dbt"
    dbt = str(executable if executable.exists() else "dbt")
    environment = {**os.environ, "DBT_PROFILES_DIR": str(REPOSITORY_ROOT / "dbt_project")}
    for arguments in (["source", "freshness"], ["build"]):
        subprocess.run(
            [dbt, *arguments],
            cwd=REPOSITORY_ROOT / "dbt_project",
            env=environment,
            check=True,
        )


def record_run(run_id: uuid.UUID, started_at: datetime, status: str, **updates) -> None:
    settings = Settings()
    ensure_warehouse(settings)
    with psycopg.connect(settings.postgres_dsn) as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO raw.pipeline_runs (
                    run_id, started_at, finished_at, status, events_processed,
                    raw_object_key, error_message
                ) VALUES (%s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (run_id) DO UPDATE SET
                    finished_at = EXCLUDED.finished_at,
                    status = EXCLUDED.status,
                    events_processed = EXCLUDED.events_processed,
                    raw_object_key = EXCLUDED.raw_object_key,
                    error_message = EXCLUDED.error_message
                """,
                (
                    run_id,
                    started_at,
                    updates.get("finished_at"),
                    status,
                    updates.get("events_processed", 0),
                    updates.get("raw_object_key"),
                    updates.get("error_message"),
                ),
            )


def alert(message: str) -> None:
    url = Settings().alert_webhook_url
    if url:
        requests.post(url, json={"text": message}, timeout=10).raise_for_status()


@flow(name="industrial-telemetry-etl", log_prints=True)
def telemetry_flow(event_count: int = 500, seed: int = 42):
    run_id = uuid.uuid4()
    started_at = datetime.now(timezone.utc)
    record_run(run_id, started_at, "running")
    try:
        result = ingest_task(event_count, seed)
        dbt_build_task()
        record_run(
            run_id,
            started_at,
            "success",
            finished_at=datetime.now(timezone.utc),
            events_processed=result["inserted"],
            raw_object_key=result["object_key"],
        )
        if os.getenv("WORKFLOW_URL"):
            from telemetry_pipeline.workflow_events import enqueue_anomalies, publish_pending

            enqueue_anomalies()
            publish_pending()
        return result
    except Exception as exc:
        if os.getenv("WORKFLOW_URL"):
            try:
                from telemetry_pipeline.workflow_events import enqueue_failure, publish_pending

                enqueue_failure(run_id, started_at, "Pipeline/dbt/freshness execution failed; inspect run history.")
                publish_pending()
            except Exception:
                print("Workflow event publication failed; inspect pipeline history and retry publisher.")
        try:
            record_run(
                run_id,
                started_at,
                "failed",
                finished_at=datetime.now(timezone.utc),
                error_message=str(exc)[:1000],
            )
        except Exception as history_error:
            print(f"Could not persist failed run history: {history_error}")
        try:
            alert(f"Telemetry pipeline failed: {exc}")
        except Exception as alert_error:
            print(f"Could not deliver failure alert: {alert_error}")
        raise


if __name__ == "__main__":
    telemetry_flow()
