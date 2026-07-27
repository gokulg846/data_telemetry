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
