"""Initialize the shared local warehouse and its restricted investigation account."""
import os
import subprocess
import psycopg
from psycopg import sql
from telemetry_pipeline.config import Settings
from telemetry_pipeline.storage import ensure_warehouse
from telemetry_pipeline.workflow_events import ensure_outbox


def main():
    settings = Settings()
    ensure_warehouse(settings)
    with psycopg.connect(settings.postgres_dsn) as conn:
        ensure_outbox(conn)
        if not conn.execute("SELECT 1 FROM pg_roles WHERE rolname='workflow_reader'").fetchone():
            conn.execute(sql.SQL("CREATE ROLE workflow_reader LOGIN PASSWORD {}")
                         .format(sql.Literal(os.environ["WAREHOUSE_READER_PASSWORD"])))
        conn.execute("GRANT USAGE ON SCHEMA public, analytics, raw TO workflow_reader")
        conn.execute("GRANT SELECT ON raw.telemetry_events TO workflow_reader")
        conn.execute("GRANT SELECT (run_id, started_at, finished_at, status, events_processed) ON raw.pipeline_runs TO workflow_reader")
        conn.execute("ALTER DEFAULT PRIVILEGES IN SCHEMA public, analytics GRANT SELECT ON TABLES TO workflow_reader")
        conn.execute("GRANT SELECT ON ALL TABLES IN SCHEMA public, analytics TO workflow_reader")
    # Create empty marts without generating sample data or invoking dbt tests.
    subprocess.run(["dbt", "run", "--project-dir", "dbt_project"], check=True)


if __name__ == "__main__":
    main()
