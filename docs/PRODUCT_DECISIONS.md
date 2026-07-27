# Product Decisions and Learning Log

This document makes product judgment visible and gives future contributors a
place to record why priorities change.

## Decision 001 — Use a deterministic simulator for v1

- **Status:** Accepted
- **Context:** Public APIs do not reliably produce industrial failure patterns.
- **Decision:** Simulate reproducible machine behavior, including two degrading
  assets and rare anomalies.
- **Benefit:** Demonstrable user scenarios and reliable test fixtures.
- **Cost:** No evidence that thresholds generalize to real equipment.
- **Revisit when:** Labeled historian or gateway data becomes available.

## Decision 002 — Optimize for three decisions

- **Status:** Accepted
- **Decision:** Limit the MVP to anomaly triage, degradation, and line SLO.
- **Reason:** A small number of coherent workflows is more useful and easier to
  validate than a broad monitoring dashboard.
- **Revisit when:** Pilot users repeatedly request an adjacent decision.

## Decision 003 — Defer predictive maintenance ML

- **Status:** Accepted
- **Reason:** There are no labeled failure outcomes, asset-class baselines, or
  feedback loops. A model would create unearned precision.
- **Trigger to revisit:** Sufficient labeled outcomes and a baseline showing
  rules cannot meet agreed precision/recall.

## Decision 004 — Treat freshness as a product feature

- **Status:** Accepted
- **Reason:** Operators can make a worse decision from stale “healthy” data than
  from an explicit unavailable state.
- **Implementation:** dbt source freshness, latest event time, pipeline status,
  run history, and failure alerts.

## Decision 005 — Keep the database private

- **Status:** Accepted
- **Reason:** Operational data and credentials should not be exposed for the
  convenience of a hosted dashboard.
- **Tradeoff:** Dashboard deployment requires a VPC-connected service.

## Decision 006 — Make cloud dashboard deployment opt-in

- **Status:** Accepted
- **Reason:** A load balancer and continuously running task create ongoing cost.
- **Implementation:** Terraform defaults `deploy_dashboard` to false.
- **Trigger:** Enable only after an image exists and a demo/pilot window is
  approved.

## Assumption register

| Assumption | Risk if false | Validation method | Status |
|---|---|---|---|
| Supervisors struggle to prioritize alarms | Product adds little value | Interviews and shift observation | Unvalidated |
| A 10-event vibration comparison is useful | Degradation signal is noisy | Replay labeled data | Unvalidated |
| 98% healthy-event SLO maps to line health | Aggregate metric misleads | Workshop with plant leadership | Unvalidated |
| 15-minute freshness is sufficient | Alerts arrive too late | Workflow and hazard analysis | Unvalidated |
| Users will disposition anomalies | Learning loop remains incomplete | Assisted pilot | Unvalidated |

## Backlog

### Now

- Validate code and infrastructure.
- Calibrate demo behavior and capture screenshots.
- Protect any public deployment with HTTPS and authentication.

### Next

- Add line, machine, status, and time filters.
- Add anomaly acknowledgement and disposition.
- Add asset metadata and operating-mode context.
- Instrument product analytics defined in the PRD.

### Later

- Connect MQTT/OPC-UA or historian source.
- Integrate approved alerts with CMMS.
- Add asset-specific baselines.
- Evaluate predictive models against the rules baseline.
- Add multi-site tenancy and role-based access control.

