# Factory Pulse Product Implementation Plan

## Purpose

Factory Pulse turns industrial equipment telemetry into three decisions:

1. Which machines need attention now?
2. Which machines are showing early degradation?
3. Which production lines are missing their reliability target?

This plan makes the product easy to run, easy to understand, and honest about
what has been implemented versus what has been proven to work.

## Status definitions

- `[ ] Planned` — requirement or evidence does not exist yet.
- `[~] Implemented, verification pending` — code or documentation exists, but
  the acceptance test has not been run and captured.
- `[x] Complete` — implementation exists and the acceptance evidence has been
  captured in the repository.

No requirement should move to `[x]` based only on code review.

## Product users and useful contexts

### Shift supervisor

Use Factory Pulse during a shift to prioritize which equipment to inspect. The
product is useful when one supervisor is responsible for several machines and
raw alarms do not provide a clear order of attention.

### Reliability engineer

Use Factory Pulse to distinguish isolated spikes from worsening vibration and
to assemble evidence for maintenance investigation.

### Plant manager

Use the hourly line-reliability view to identify production lines below the 98%
healthy-event target and direct follow-up to the correct team.

### Data platform engineer

Use pipeline history, freshness checks, dbt tests, and failure alerts to decide
whether operational users can trust the current dashboard.

### Appropriate and inappropriate uses

Factory Pulse is appropriate for portfolio demonstrations, data-platform
learning, shadow-mode operational pilots, and non-safety-critical decision
support. It is not an approved safety system, an equipment controller, or a
replacement for SCADA, MES, a historian, or a CMMS. Demo thresholds require
asset-specific approval before use with real equipment.

## Product requirements checklist

### A. First-run experience and usability

- [ ] **PR-01 — One-command demo.** A new user can start infrastructure,
  generate data, build analytics, and launch the dashboard with one documented
  command.
  - Acceptance: succeeds from a fresh clone on a supported machine.
  - Evidence: terminal transcript and populated-dashboard screenshot.
- [ ] **PR-02 — Automated readiness checks.** Startup checks Docker, ports,
  environment variables, database readiness, and object-store readiness, then
  provides a specific recovery message for each failure.
  - Acceptance: each simulated missing prerequisite produces an actionable
    message and non-zero exit status.
  - Evidence: captured healthy and failing preflight outputs.
- [~] **PR-03 — Safe configuration.** A committed example environment file
  documents every setting while real secrets remain ignored.
  - Acceptance: every runtime setting appears in `.env.example` with a safe
    local default or explanation.
  - Evidence: configuration audit.
- [~] **PR-04 — Run guide.** The README explains prerequisites, setup, local
  execution, stopping services, preserving/resetting data, troubleshooting,
  cloud boundaries, and expected outputs.
  - Acceptance: an unfamiliar user completes the guide without oral help.
  - Evidence: reviewer walkthrough notes.
- [ ] **PR-05 — Demo data reset.** Users can reset only this project's local
  data through an explicit documented command with a confirmation guard.
  - Acceptance: reset removes project volumes and a subsequent demo starts
    cleanly.
  - Evidence: before/after event counts and volume listing.

### B. Telemetry ingestion

- [~] **PR-06 — Representative telemetry.** The simulator emits deterministic
  temperature, vibration, pressure, and power readings, including normal,
  warning, critical, and degradation scenarios.
  - Acceptance: a fixed seed produces stable events and every intended state.
  - Evidence: unit-test output and sample fixture.
- [~] **PR-07 — Immutable raw storage.** Every batch lands in a unique,
  time-partitioned NDJSON object in MinIO locally or S3 in AWS.
  - Acceptance: two runs create two objects without overwriting history.
  - Evidence: object listing and metadata screenshot.
- [~] **PR-08 — Idempotent warehouse loading.** Retrying the same deterministic
  events does not duplicate warehouse facts.
  - Acceptance: the second load inserts zero duplicate event IDs.
  - Evidence: before/after SQL counts and integration test.
- [~] **PR-09 — Schema-change visibility.** Added or missing source keys are
  preserved in raw data and logged for investigation.
  - Acceptance: a modified event produces a structured drift warning.
  - Evidence: captured log and automated test.

### C. Trusted analytics

- [~] **PR-10 — Layered models.** dbt provides staging, intermediate, and mart
  layers with documented lineage.
  - Acceptance: `dbt build` succeeds and lineage contains all product marts.
  - Evidence: command output and lineage screenshot.
- [~] **PR-11 — Quality gates.** Tests enforce key uniqueness, required values,
  accepted statuses, physical sensor ranges, and bounded reliability metrics.
  - Acceptance: valid data passes and deliberately invalid data fails.
  - Evidence: passing run and one controlled failure.
- [~] **PR-12 — Freshness protection.** Stale data warns after 30 minutes and
  fails after two hours.
  - Acceptance: current and stale fixtures produce the expected states.
  - Evidence: dbt freshness output.
- [~] **PR-13 — Decision marts.** Analytics expose current machine health,
  anomaly events, and hourly line reliability.
  - Acceptance: each mart returns expected deterministic results.
  - Evidence: golden-result integration tests or SQL snapshots.

### D. Operator product experience

- [~] **PR-14 — Trust summary.** The dashboard shows critical count, warning
  count, latest pipeline state, and latest event time before analytic charts.
  - Acceptance: values match the warehouse for a known dataset.
  - Evidence: screenshot plus validating SQL output.
- [~] **PR-15 — Risk prioritization.** Machines are ordered by explainable risk
  and show status, temperature, vibration, line, and degradation context.
  - Acceptance: known critical and degrading machines have expected priority.
  - Evidence: deterministic-data screenshot.
- [~] **PR-16 — Anomaly triage.** Users can review anomaly type, severity,
  machine, line, time, and relevant readings.
  - Acceptance: every warning/critical demo event has a classification.
  - Evidence: triage screenshot and source comparison.
- [~] **PR-17 — Line reliability.** Users can compare hourly healthy-event
  percentages against a visible 98% target.
  - Acceptance: displayed values match the reliability mart.
  - Evidence: chart screenshot and SQL comparison.
- [ ] **PR-18 — Exploration controls.** Users can filter by line, machine,
  status, and time window without writing SQL.
  - Acceptance: all charts and the triage table respond to filters.
  - Evidence: interaction recording.
- [ ] **PR-19 — Empty and error states.** The dashboard explains no-data,
  unavailable-database, stale-data, and failed-pipeline states with a next step.
  - Acceptance: each controlled state renders guidance instead of a stack trace
    or misleading healthy view.
  - Evidence: four state screenshots.
- [ ] **PR-20 — Accessible status communication.** Severity uses labels and
  symbols in addition to color and meets basic contrast and keyboard checks.
  - Acceptance: manual accessibility checklist passes.
  - Evidence: completed checklist.

### E. Orchestration and operations

- [~] **PR-21 — End-to-end orchestration.** One Prefect flow owns ingestion,
  freshness, dbt build, and run-history recording.
  - Acceptance: a successful run records event count and raw object key.
  - Evidence: Prefect screenshot and database record.
- [~] **PR-22 — Retry and failure handling.** Transient ingestion failures retry
  with bounded backoff; final failures are recorded and optionally alerted.
  - Acceptance: controlled transient and permanent failures behave as designed.
  - Evidence: run logs and webhook capture.
- [~] **PR-23 — Scheduleability.** The flow has an hourly local deployment and
  an opt-in AWS schedule.
  - Acceptance: a schedule definition triggers one successful run.
  - Evidence: local or cloud schedule screenshot.
- [ ] **PR-24 — Operational runbook.** Documentation covers common failures,
  diagnosis, recovery, replay, escalation, and safe teardown.
  - Acceptance: a reviewer resolves three injected failures using only it.
  - Evidence: drill notes.

### F. Deployment, security, and cost

- [~] **PR-25 — Reproducible local environment.** Docker Compose provides
  isolated PostgreSQL and MinIO services with health checks.
  - Acceptance: services become healthy on supported Docker versions.
  - Evidence: Compose status output.
- [~] **PR-26 — Container packaging.** Separate non-root images package the
  pipeline and dashboard.
  - Acceptance: both images build and start with documented configuration.
  - Evidence: build logs and container status.
- [~] **PR-27 — Secure cloud foundation.** Terraform defines encrypted and
  versioned S3, private RDS, managed secrets, least-privilege roles, CloudWatch,
  ECR, Fargate, and EventBridge scheduling.
  - Acceptance: format, validation, security review, and sandbox plan pass.
  - Evidence: sanitized plan and review checklist.
- [~] **PR-28 — Cost-safe defaults.** Scheduling and the continuously running
  dashboard are disabled until explicitly enabled.
  - Acceptance: the default Terraform plan shows both disabled.
  - Evidence: sanitized plan excerpt.
- [ ] **PR-29 — Production web protections.** A real-data deployment uses HTTPS,
  authentication, authorization, and restricted access logs.
  - Acceptance: unauthenticated HTTP access cannot reach operational data.
  - Evidence: security test and deployment diagram.

### G. Product and portfolio evidence

- [~] **PR-30 — Product rationale.** The PRD defines users, jobs, scope,
  requirements, success metrics, guardrails, risks, and rollout.
  - Acceptance: every feature maps to a user problem and metric.
  - Evidence: requirements traceability review.
- [~] **PR-31 — Honest delivery status.** Documentation distinguishes code,
  runtime validation, cloud deployment, and user-value evidence.
  - Acceptance: no portfolio claim exceeds captured evidence.
  - Evidence: delivery-status review.
- [ ] **PR-32 — Portfolio proof pack.** The repository contains dashboard,
  Prefect, dbt lineage, MinIO, and Terraform-plan screenshots plus a demo script
  and evidence index.
  - Acceptance: a reviewer understands problem, solution, and proof in under
    five minutes.
  - Evidence: completed `docs/evidence/` index.
- [ ] **PR-33 — Automated continuous integration.** Pull requests run linting,
  unit tests, and appropriate static validation.
  - Acceptance: a clean PR passes and an intentional defect fails CI.
  - Evidence: GitHub Actions links.

## Implementation phases

### Phase 1 — Make the first run effortless

Requirements: PR-01 through PR-05.

Deliverables:

- `make demo` or equivalent one-command first run;
- preflight/readiness script with actionable errors;
- complete environment-variable reference;
- expanded run, stop, reset, and troubleshooting documentation;
- guarded local-data reset command.

Exit criterion: a new user reaches a populated dashboard from a fresh clone
without project-specific guidance.

### Phase 2 — Prove the data path

Requirements: PR-06 through PR-13 and PR-21 through PR-23.

Deliverables:

- deterministic sample fixture and integration-test harness;
- proof for raw storage, idempotency, schema drift, dbt tests, freshness, marts,
  retries, alerts, and scheduling;
- explicit expected outputs for each verification command.

Exit criterion: one dataset is traceable from raw object to dashboard mart, and
both happy and failure paths have recorded evidence.

### Phase 3 — Make the dashboard product-ready

Requirements: PR-14 through PR-20.

Deliverables:

- coherent filters across all views;
- helpful empty, error, failed, and stale states;
- accessibility review and improvements;
- screenshot-ready deterministic demo scenario.

Exit criterion: an operator can identify the highest-risk machine, understand
why it is risky, and recognize whether the data is trustworthy.

### Phase 4 — Operationalize and secure deployment

Requirements: PR-24 through PR-29 and PR-33.

Deliverables:

- operational runbook;
- container and Terraform static validation;
- sanitized cloud plan and cost notes;
- documented HTTPS/authentication design for real data;
- expanded CI checks.

Exit criterion: a reviewer can deploy, operate, diagnose, and safely tear down
the product using repository documentation.

### Phase 5 — Assemble portfolio evidence

Requirements: PR-30 through PR-32.

Deliverables:

- `docs/evidence/README.md` linking every claim to proof;
- five core screenshots and a 60–90 second demo script;
- portfolio-ready summary, role, decisions, limitations, and next steps;
- final requirement checklist with verified boxes.

Exit criterion: every public claim is backed by visible evidence and clearly
separated from future pilot outcomes.

## Verification policy

For each requirement:

1. Implement the smallest complete feature.
2. Run its acceptance check.
3. Save evidence or link to CI output.
4. Change `[~]` or `[ ]` to `[x]` only after evidence exists.
5. Record meaningful deviations in `docs/PRODUCT_DECISIONS.md`.

## Immediate work order

1. Implement PR-01 and PR-02: one-command demo plus preflight checks.
2. Complete PR-03 and PR-04: configuration audit and novice run guide.
3. Implement PR-05: guarded reset workflow.
4. Add the deterministic integration harness for PR-06 through PR-13.
5. Improve the dashboard for PR-18 through PR-20.
6. Add the runbook and evidence pack.
7. Run validation and tick requirements only as proof is captured.
