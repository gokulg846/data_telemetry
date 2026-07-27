# Factory Pulse: Product Case Study

## Portfolio summary

I designed Factory Pulse to explore a common industrial product failure mode:
companies collect high-volume telemetry but still make maintenance decisions
through fragmented screens and manual exports. I treated the data pipeline as a
product capability, not the final outcome. The product outcome is a trustworthy,
prioritized workflow for deciding where operational attention is needed.

**Role represented:** Product manager working across operations, reliability,
data engineering, and cloud infrastructure.

**Artifact set:** PRD, user journeys, prioritization, metrics framework,
architecture, working product code, infrastructure-as-code, monitoring design,
and rollout plan.

## The opportunity

The initial brief asked for an end-to-end telemetry data pipeline and dashboard.
That solution space could easily become a technology showcase with ten charts
and no clear user decision. I narrowed it to three questions:

1. Which machine needs attention now?
2. Which machine appears to be degrading?
3. Which production line is missing its reliability objective?

This focus shaped the data marts, dashboard hierarchy, quality checks, and
success metrics.

## Discovery assumptions

Because this is a portfolio build without live plant access, I made explicit
hypotheses that would require validation:

- supervisors lose time prioritizing alarms across machines;
- reliability engineers value short-horizon degradation context;
- plant managers need an aggregate line-health indicator;
- stale or malformed data is a product trust problem, not only an engineering
  incident;
- the first release should advise humans, never control equipment.

### Discovery plan for a real engagement

I would conduct:

- five supervisor interviews across day and night shifts;
- three reliability-engineer workflow observations;
- analysis of three months of alarms and maintenance work orders;
- a terminology and threshold workshop with controls and safety teams;
- a review of current handoff, escalation, and CMMS workflows.

Key questions would probe the last real intervention, signals used, time lost,
false alarms, escalation criteria, and what evidence makes a recommendation
trustworthy.

## Product strategy

### Target segment

The beachhead is a single plant with instrumented rotating equipment, an
existing telemetry source, and a reliability team able to label alert outcomes.
This creates a contained feedback loop before expanding to multi-site analytics.

### Value proposition

For shift supervisors and reliability engineers who need to act on noisy
equipment data, Factory Pulse ranks current operational risk and explains the
underlying signal while exposing data freshness. Unlike raw sensor dashboards,
it organizes the experience around intervention decisions and maintains a
traceable, quality-tested data path.

### Strategic choice

I chose deterministic simulation over a public weather or sensor API. That
reduced external dependency risk and enabled repeatable critical, warning, and
degradation scenarios. The tradeoff is that product-market evidence remains
hypothetical until a shadow pilot uses real labeled data.

## From user needs to product architecture

| User need | Product behavior | Data capability |
|---|---|---|
| “Tell me where to look first.” | Ranked risk chart | Current-state mart with explainable score |
| “Show why this machine is risky.” | Anomaly queue with readings | Tested anomaly classification |
| “Is this a spike or a trend?” | Rolling baseline and change | Windowed intermediate model |
| “Is the whole line struggling?” | Hourly 98% SLO view | Line reliability mart |
| “Can I trust this screen?” | Latest event and pipeline state | Freshness checks and run history |

This mapping is the central product decision: infrastructure work is justified
only when it supports a user decision or trust requirement.

## MVP prioritization

I used directional RICE scoring and made two deliberate exclusions:

- **Predictive ML was deferred.** A model without labeled failures, an operator
  workflow, or alert feedback would add novelty but not validated value.
- **CMMS integration was deferred.** It may be high impact, but the correct
  workflow and system of record should be learned during a pilot.

The MVP therefore includes risk ranking, anomaly triage, degradation context,
line reliability, freshness, and pipeline status.

## UX rationale

The dashboard follows progressive detail:

1. Four summary signals establish urgency and trust.
2. Machine risk ranking answers where to focus.
3. Reliability and anomaly mix provide operating context.
4. A detailed queue supports investigation.
5. Pipeline run history remains available but does not dominate the operator UI.

Status uses text alongside color. A real pilot would add cross-filtering,
acknowledgement, anomaly disposition, and asset metadata.

## Metrics and learning agenda

The north-star metric is **actionable risks reviewed per operating week**. This
avoids vanity metrics such as event volume and page views.

The most important early learning metric is useful-alert rate. If fewer than 60%
of reviewed alerts are considered actionable, the team should improve
thresholds and context before adding users or features. Median time-to-triage
measures workflow speed, while missed critical conditions and false-critical
rate serve as safety and trust guardrails.

## Delivery approach

I separated delivery into reversible layers:

- local MinIO/Postgres before billable cloud infrastructure;
- immutable raw data before evolving transformations;
- dbt contracts before dashboard queries;
- a human decision-support tool before automation;
- optional dashboard infrastructure before continuous cloud spend.

The same application boundary maps from local services to S3, RDS, and
ECS/Fargate. This keeps early product learning inexpensive without creating a
throwaway technical prototype.

## Key tradeoffs

### Rules versus machine learning

Rules are explainable and demonstrable without labeled failure data. They are
also crude across asset types. I chose rules for v1 and made calibration an
explicit pilot activity.

### Direct warehouse queries versus an API

Direct queries reduce MVP surface area and keep transformations in dbt. They
couple the dashboard to mart schemas and are not ideal for broad external use.
An authenticated API becomes worthwhile with multiple clients or write actions.

### Streamlit versus a custom frontend

Streamlit accelerates product learning and keeps effort on decision design. A
custom frontend would offer richer interaction and access control but is not
required to test the initial workflow.

### Private RDS versus simple public connectivity

A private database makes deployment more involved but avoids normalizing an
unsafe architecture. The dashboard therefore runs optionally inside the same
VPC behind a load balancer.

## Risks I would surface to leadership

The largest product risk is not pipeline scale; it is false confidence.
Synthetic anomalies prove behavior, not predictive validity. Before real use,
thresholds need reliability-engineering approval, the dashboard needs
authentication and HTTPS, and the product must clearly state that it is not a
safety control.

The second risk is alert fatigue. The rollout therefore begins in shadow mode
and requires disposition data before assisted operations.

## Outcome and current evidence

The repository contains the full code path and deployment definitions:
ingestion, raw retention, warehouse contracts, dbt models and tests,
orchestration, alerts, dashboard, local infrastructure, and secure cloud
infrastructure.

Runtime validation, user research, threshold calibration, cloud deployment,
and a real pilot are intentionally listed as pending evidence. This distinction
matters in a PM portfolio: shipped code is not proof of adoption or value.

## What I would do next

1. Validate the end-to-end build and failure paths.
2. Conduct discovery with supervisors and reliability engineers.
3. Add dashboard filters plus anomaly acknowledgement/disposition.
4. Replay labeled historian data and calibrate thresholds.
5. Run a two-week shadow pilot on one non-critical line.
6. Review useful-alert rate and missed conditions.
7. Decide whether CMMS integration or broader rollout is justified.

## Interview prompts this case supports

- How I narrowed a broad data-platform brief to three user decisions.
- Why I deferred predictive ML despite its portfolio appeal.
- How product trust influenced freshness, quality, and run-history requirements.
- How I balanced local speed, cloud credibility, security, and cost.
- Which evidence is implemented versus which evidence still requires a pilot.

