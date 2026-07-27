# Product Requirements Document: Factory Pulse

| Field | Detail |
|---|---|
| Product | Factory Pulse |
| Version | 1.0 |
| Status | Build complete; validation and pilot pending |
| Owner | Product / Data Platform |
| Primary users | Shift supervisors, reliability engineers |
| Supporting users | Plant managers, data platform engineers |

## 1. Executive summary

Factory Pulse is an industrial equipment health product that converts fragmented
sensor telemetry into a prioritized operating view. It tells a shift supervisor
where to intervene now, helps a reliability engineer identify degradation before
failure, and gives a plant manager an hourly view of production-line health.

The first release uses simulated equipment data to prove the complete product
and data architecture without requiring access to a factory network. The product
is built so the simulator can later be replaced by MQTT, an OPC-UA gateway, or
an existing historian export without changing downstream user experiences.

## 2. Problem statement

Industrial teams often have abundant sensor readings but limited decision
support. Raw temperature, vibration, and pressure streams are:

- distributed across machines and source systems;
- difficult to compare against a recent operating baseline;
- too noisy to review manually during a shift;
- not connected to line-level reliability objectives; and
- vulnerable to stale, duplicated, or malformed data.

As a result, supervisors may react late to critical conditions, reliability
engineers spend time assembling evidence, and plant leaders cannot distinguish
equipment risk from pipeline-data failure.

## 3. Product vision

Give every factory operations team a trustworthy, near-real-time answer to:

> What needs attention, why does it need attention, and is the underlying data
> current enough to act on?

## 4. Goals and non-goals

### Goals

1. Rank current machine risk across a production site.
2. Surface warning and critical events with enough context to triage them.
3. Detect short-horizon vibration degradation relative to recent machine history.
4. Show whether each line meets a 98% healthy-event service-level objective.
5. Make data freshness and pipeline health visible.
6. Preserve replayable raw data and enforce analytics data quality.
7. Support a laptop demo and a secure AWS deployment from the same codebase.

### Non-goals for v1

- Automatically stop equipment or write commands to industrial control systems.
- Diagnose a physical root cause or prescribe a maintenance procedure.
- Replace a CMMS, MES, SCADA, or historian.
- Train a predictive-maintenance machine-learning model.
- Provide multi-site tenancy, fine-grained access control, or mobile applications.
- Guarantee safety-critical alert delivery.

## 5. Users and jobs to be done

### Shift supervisor — primary

**Context:** Responsible for safe throughput across several machines during a
shift and cannot inspect every signal continuously.

**Job:** “When equipment behavior becomes abnormal, help me identify the machine
and severity quickly so I can decide whether to inspect, slow, or escalate it.”

**Pain points:** Alarm overload, scattered screens, unclear priority, limited
time to compare current readings with recent behavior.

### Reliability engineer — primary

**Context:** Investigates recurring warnings and plans maintenance.

**Job:** “When a machine begins degrading, show me the trend and supporting
signals so I can investigate before an unplanned outage.”

**Pain points:** Manual data exports, inconsistent timestamps, duplicate events,
and difficulty separating a spike from sustained degradation.

### Plant manager — secondary

**Context:** Reviews whether production lines are operating reliably.

**Job:** “Show which line is missing its operating-health objective so I can ask
the right team for corrective action.”

### Data platform engineer — supporting

**Context:** Owns pipeline reliability and data trust.

**Job:** “Tell me when ingestion, freshness, schema, or transformation quality
fails so users do not act on silently bad data.”

## 6. User journey

1. A supervisor opens Factory Pulse at the beginning of a shift.
2. Summary metrics show critical machines, warning machines, pipeline status,
   and the latest event timestamp.
3. The risk chart ranks machines, with status and degradation context.
4. The supervisor selects a high-risk machine and reviews its recent anomaly.
5. The anomaly queue explains whether temperature, vibration, or pressure
   crossed a threshold.
6. The supervisor checks line reliability to understand the broader effect.
7. If pipeline status or freshness is unhealthy, the supervisor treats the data
   as informational and escalates to the data platform owner.

## 7. Scope and requirements

Priority uses MoSCoW: Must, Should, Could, Won't in this release.

### Functional requirements

| ID | Priority | Requirement | Acceptance criterion |
|---|---|---|---|
| FR-01 | Must | Ingest equipment telemetry in scheduleable batches. | A configured run generates or receives a batch and assigns every event an immutable ID and UTC timestamp. |
| FR-02 | Must | Preserve raw batches. | Every accepted batch is written as a unique time-partitioned NDJSON object with count and schema metadata. |
| FR-03 | Must | Make retries idempotent. | Reprocessing the same event IDs creates no duplicate warehouse rows. |
| FR-04 | Must | Classify machine condition. | Every event is classified as healthy, warning, or critical using documented thresholds. |
| FR-05 | Must | Rank current machine risk. | The dashboard shows one current record per machine ordered by a 0–100 risk score. |
| FR-06 | Must | Provide anomaly triage. | Users can see recent warning/critical events, machine, line, time, anomaly type, and relevant readings. |
| FR-07 | Must | Show degradation. | Current vibration is compared with a recent value and rolling baseline for each machine. |
| FR-08 | Must | Measure line reliability. | Hourly healthy-event percentage and 98% SLO status are available for each line. |
| FR-09 | Must | Gate bad analytics data. | Pipeline fails when identifier, accepted-value, physical-range, uniqueness, or reliability-bound tests fail. |
| FR-10 | Must | Show pipeline trust signals. | Dashboard shows latest pipeline status and event timestamp; run history persists success/failure details. |
| FR-11 | Must | Alert on failure. | A configured webhook receives a concise message when the end-to-end flow fails. |
| FR-12 | Should | Detect additive schema changes. | Previously unseen or missing event keys produce a structured warning in pipeline logs. |
| FR-13 | Should | Deploy on AWS from code. | Terraform defines storage, warehouse, secrets, scheduled compute, logs, and an optional dashboard service. |
| FR-14 | Should | Run locally without cloud spend. | Docker Compose provides compatible object storage and PostgreSQL services. |
| FR-15 | Could | Filter by line, machine, and time. | Users can narrow all dashboard views without writing SQL. |
| FR-16 | Could | Link anomalies to maintenance work orders. | A triaged anomaly can create or reference a CMMS work order. |

### Non-functional requirements

| ID | Requirement | Initial target |
|---|---|---|
| NFR-01 | Freshness | New data visible within 15 minutes in a pilot; warn at 30 minutes and fail at 2 hours. |
| NFR-02 | Reliability | At least 99% successful scheduled pipeline runs during a 30-day pilot. |
| NFR-03 | Performance | Dashboard initial load under 3 seconds for 100,000 events. |
| NFR-04 | Recoverability | Any raw batch can be replayed without duplicating warehouse facts. |
| NFR-05 | Security | No credentials in source control; encrypted storage; private database; least-privilege task roles. |
| NFR-06 | Observability | Every run records start, finish, state, event count, raw key, and failure text. |
| NFR-07 | Accessibility | Status is expressed through labels and values, not color alone. |
| NFR-08 | Cost | Development environment remains manually destroyable and uses small resource classes. |

## 8. Decision logic

Initial thresholds are product hypotheses, not validated safety limits:

| Signal | Warning | Critical |
|---|---:|---:|
| Temperature | ≥ 82°C | ≥ 92°C |
| Vibration | ≥ 6 mm/s | ≥ 9 mm/s |
| Pressure | Outside 4.0–6.5 bar | Outside 3.5–7.0 bar |

Risk score:

- critical status: 100;
- warning status: 60;
- vibration increase of at least 2 mm/s over ten events: 45;
- otherwise: 10.

Before a real pilot, reliability engineering must calibrate thresholds per asset
class and operating mode. The product must never present these demo thresholds
as approved safety setpoints.

## 9. Success metrics

### North-star metric

**Actionable risks reviewed per operating week:** distinct warning or critical
machine conditions acknowledged or investigated by an operator.

This measures useful decisions rather than event volume or dashboard traffic.

### Pilot outcome metrics

| Metric | Definition | Target |
|---|---|---:|
| Median time to triage | Time from critical event availability to first operator review | < 10 min |
| Useful-alert rate | Reviewed alerts judged actionable / reviewed alerts | ≥ 60% |
| Degradation lead time | Time between degradation signal and maintenance/failure event | Establish baseline, then improve |
| Missed critical conditions | Valid critical conditions absent from product | 0 in labeled pilot set |
| Weekly active supervisors | Supervisors using product in at least two shifts / invited supervisors | ≥ 70% |
| Pipeline success rate | Successful scheduled runs / scheduled runs | ≥ 99% |
| Data freshness compliance | Runs visible within 15 minutes / successful runs | ≥ 95% |

### Guardrail metrics

- False-critical rate must not exceed 20% after threshold calibration.
- Dashboard use must not increase average shift-handoff time by more than five
  minutes.
- No raw telemetry or credentials may be exposed through a public bucket.
- Operators must not use Factory Pulse as an automated safety control.

## 10. Analytics instrumentation

The current system records pipeline events. A pilot product should add:

| Event | Properties | Purpose |
|---|---|---|
| `dashboard_viewed` | user_role, line_filter, timestamp | Adoption and workflow frequency |
| `machine_opened` | machine_id, risk_score, status | Whether ranking drives investigation |
| `anomaly_reviewed` | event_id, anomaly_type, age_minutes | Time-to-triage |
| `anomaly_dispositioned` | event_id, useful, action_type | Alert precision and product value |
| `line_slo_opened` | line_id, meets_slo | Manager workflow |
| `data_warning_seen` | warning_type, run_id | Whether trust indicators are noticed |

No personally sensitive data is required beyond a role or pseudonymous operator
identifier.

## 11. Prioritization

RICE uses Reach × Impact × Confidence / Effort. Scores are directional.

| Initiative | Reach | Impact | Confidence | Effort | RICE | Decision |
|---|---:|---:|---:|---:|---:|---|
| Risk-ranked machine view | 10 | 3.0 | 0.9 | 3 | 9.0 | Build v1 |
| Data freshness/run health | 10 | 2.0 | 0.9 | 2 | 9.0 | Build v1 |
| Anomaly triage queue | 8 | 3.0 | 0.8 | 3 | 6.4 | Build v1 |
| Line reliability SLO | 5 | 2.0 | 0.8 | 2 | 4.0 | Build v1 |
| Dashboard filters | 8 | 1.5 | 0.9 | 3 | 3.6 | Next |
| CMMS integration | 5 | 3.0 | 0.5 | 8 | 0.9 | Validate first |
| Predictive ML model | 5 | 3.0 | 0.3 | 13 | 0.3 | Defer |

## 12. Rollout plan

### Phase 0 — Technical validation

- Run deterministic and idempotency tests.
- Run dbt build and freshness checks on representative volumes.
- Validate Terraform plan in an AWS sandbox.
- Conduct a security review of IAM, networking, and secrets.

**Exit:** End-to-end pipeline succeeds repeatedly and failure paths are visible.

### Phase 1 — Shadow pilot

- Connect one non-critical line or replay historian data.
- Show insights to reliability engineering without changing operations.
- Label anomalies and calibrate per-asset thresholds.

**Exit:** At least 60% useful-alert rate and no missed labeled critical events.

### Phase 2 — Assisted operations pilot

- Invite two shift supervisors.
- Add acknowledgement/disposition instrumentation.
- Review metrics weekly with operations and reliability.

**Exit:** Median triage under ten minutes, 70% weekly adoption, and no safety or
workflow guardrail violations.

### Phase 3 — Scale decision

- Decide whether to integrate CMMS/MES and onboard more lines.
- Re-estimate infrastructure cost and support ownership.
- Define access controls, retention, disaster recovery, and formal SLOs.

## 13. Risks and mitigations

| Risk | Impact | Mitigation |
|---|---|---|
| Demo thresholds create false confidence | Unsafe interpretation | Label as hypotheses; require reliability sign-off before pilot |
| Sensor drift creates false alerts | Lost trust | Calibration, asset-specific baselines, disposition feedback |
| Stale data looks healthy | Bad decisions | Visible event freshness, dbt source freshness, pipeline state |
| Duplicate delivery inflates metrics | Incorrect prioritization | Deterministic IDs and database conflict handling |
| Schema changes silently drop fields | Data loss | Preserve raw payload and log schema drift |
| Alert fatigue | Product abandonment | Severity ranking, useful-alert metric, threshold iteration |
| Cloud cost persists after demos | Avoidable spend | Local-first path, optional dashboard, lifecycle policy, destroy guide |
| Public dashboard exposes operational data | Security incident | Private database, security groups, future HTTPS and authentication |

## 14. Dependencies and assumptions

- Source events include machine, line, UTC time, and expected sensor fields.
- Reliability engineering owns operational threshold approval.
- Data platform owns scheduled jobs, quality rules, and incident response.
- A production dashboard requires HTTPS and identity-aware access before real
  plant data is used.
- AWS deployment requires an account, container image push, cost approval, and
  region-specific review.

## 15. Open questions

1. Which decision should a supervisor take for each alert severity?
2. Should baselines be machine-specific, asset-class-specific, or operating-mode-specific?
3. What constitutes a useful alert in the maintenance workflow?
4. Which system is authoritative for machine and line metadata?
5. What retention is required for raw telemetry and investigation history?
6. Is fifteen-minute freshness sufficient for the first real use case?
7. Who owns after-hours response to pipeline failures?
8. Which authentication provider should protect a deployed dashboard?

## 16. Release acceptance checklist

- [ ] All unit, dbt, freshness, and integration checks pass.
- [ ] A repeated batch creates no duplicate warehouse events.
- [ ] Warning and critical scenarios appear in the correct dashboard views.
- [ ] Pipeline failures are recorded and delivered to a test webhook.
- [ ] Accessibility review confirms status is not color-only.
- [ ] Terraform plan is reviewed for security and cost.
- [ ] Dashboard is protected with HTTPS and authentication for real data.
- [ ] Reliability engineering approves thresholds for the pilot asset class.
- [ ] Product analytics events and anomaly disposition are implemented for pilot.
- [ ] Runbook owner and incident path are documented.

