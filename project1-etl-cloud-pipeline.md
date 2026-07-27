# Project 1: Data ETL/ELT Pipeline + Cloud Architecture + Dashboard
### 7 focused AI-assisted sessions

**Domain:** Real-time industrial/IoT sensor telemetry (extends your Accenture IIoT + wafer yield pipeline work) — ingest sensor/equipment data, transform, surface actionable insights on a dashboard. Swap domain if you want (finance data, public API) — architecture stays identical.

**Stack:** Source API/simulator → S3 (raw) → dbt (transform) → Postgres/Snowflake (warehouse) → Prefect (orchestration) → Next.js or Streamlit (dashboard) → Terraform (IaC)

---

**Session 1 — Architecture & Scope (1.5-2 hrs)**
Define: data source (real API like a public sensor/weather dataset, or a synthetic generator mimicking equipment telemetry), the 2-3 "actionable insights" the dashboard must surface (e.g. anomaly flags, trend degradation, SLA breach), and draw the architecture diagram. Deliverable: `architecture.md` with diagram + tech choices justified.
*AI prompt starting point:* "Here's my background [paste]. Help me design a portfolio-grade ETL architecture for [domain] that's ambitious enough to show cloud fluency but buildable in ~15 hours total."

**Session 2 — Ingestion Layer**
Build the extraction script(s): pull from source API or simulator, land raw files in S3 (or MinIO locally if avoiding cloud cost early). Handle pagination, retries, schema drift logging.
Deliverable: working ingestion job producing raw files on a schedule-able trigger.

**Session 3 — Transformation Layer (dbt)**
Build staging → intermediate → mart models in dbt. Add dbt tests (not_null, unique, accepted_values, custom). This is your "data quality" story for interviews.
Deliverable: dbt project with passing tests, lineage graph.

**Session 4 — Orchestration**
Wire ingestion + dbt run into Prefect (or Airflow) flow. Add retries, failure alerting (email/Slack webhook), scheduling.
Deliverable: orchestrated pipeline running end-to-end on a schedule.

**Session 5 — Cloud Infra as Code**
Terraform the warehouse + compute (RDS/Snowflake + ECS/Lambda for the orchestrator, or equivalent). Even a minimal Terraform footprint proves the skill — you don't need a huge footprint.
Deliverable: `terraform apply` stands up the infra from scratch.

**Session 6 — Frontend Dashboard**
Build the dashboard (Next.js+charting lib, or Streamlit if you want speed) hitting the warehouse directly. Focus on 2-3 insight views, not 10 mediocre ones.
Deliverable: deployed dashboard (Vercel/Streamlit Cloud) showing live-ish data.

**Session 7 — Data Quality & Monitoring + Polish**
Add a monitoring layer: pipeline run history, data freshness check, a simple alert on dbt test failure. Write README with architecture diagram, screenshots, "what I'd do with more time." Push to GitHub, add to portfolio.
Deliverable: polished repo + README + live demo link.

---
**Interview story this buys you:** "I built and deployed a full ETL pipeline — raw ingestion through Terraform-managed cloud infra, dbt-tested transforms, orchestrated and monitored, surfaced on a live dashboard." Directly answers MES/data-pipeline and industrial-AI JDs.
