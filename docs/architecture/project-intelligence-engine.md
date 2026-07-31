# Project Intelligence Engine Architecture

Status: accepted direction; first vertical slice implemented by ADR-0014.

## Purpose and boundaries

The Project Intelligence Engine (PIE) is the canonical, governed project-state service for Genesis.
It provides every authorized Product, Project, Architecture, Engineering, QA, Security, Finance,
Compliance, Operations, and Executive agent with one coherent project model. PIE does not execute
tools, replace source control, or replace Temporal. It records what the project is, what evidence
supports that state, what remains uncertain, and what work should happen next.

PIE extends the existing modular monolith and reuses PostgreSQL, OIDC authorization, organization
and project isolation, audit records, evidence, cost governance, the transactional outbox, durable
event publication, and Temporal dispatch.

## Domain boundaries

| Boundary | Responsibility | Excludes |
|---|---|---|
| Canonical State | Versioned project facts, assertions, identities, and relationships | Provider API calls |
| Ingestion | Normalize source events and observations | Deciding business truth |
| Reconciliation | Authority comparison, conflict detection, revision creation | Silent last-write-wins |
| Projection | Agent context, dashboards, roadmaps, graphs, forecasts | Canonical mutation |
| Intelligence | Recommendations, confidence, risk, and forecasts | Unexplained autonomous approval |
| Integration | GitHub, Temporal, model, cost, and future provider adapters | Provider-owned primary keys |

## Canonical model

The logical aggregate is `ProjectIntelligenceState`. Material changes create immutable
`ProjectStateRevision` records linked to the prior revision. A revision contains the schema version,
canonical JSON document, content checksum, source observation, assertion status, and explainable
confidence. Later normalized tables project frequently queried entities and graph edges from the
revision log.

Core entity families are intent (vision, requirement, decision, policy); structure (capability,
component, dependency, repository, environment); planning (roadmap item, milestone, epic, feature,
task, sprint); assurance (acceptance criterion, validation, evidence, risk, technical debt);
economics (budget, token usage, cost actual and forecast); intelligence (memory, recommendation,
confidence, completion forecast); and provenance (source, external identity, observation,
transformation, actor, evidence link).

All canonical entities use a PIE ID. Provider IDs are aliases scoped by provider and account. Edges
are typed and directed, with `parent_of`, `depends_on`, `implements`, `validates`, `evidences`,
`blocks`, `supersedes`, and `derived_from` as the initial vocabulary.

## Authority and reconciliation

Source authority is field-specific: law and constitutional controls; approved human decisions;
accepted ADRs, policy, requirements, and budgets; repository commits, CI, and immutable evidence;
synchronized issue and workflow state; agent observations; then inference and forecasts.

Higher authority does not overwrite lower-authority history; it supersedes the effective projection.
Same-authority conflicts become `disputed` assertions and require a policy rule or authorized human
resolution. Inferred state is never returned as verified fact.

Each delivery has provider, kind, external event ID, provider occurrence time, observation time, and
idempotency key. A request fingerprint prevents reuse of an idempotency key with different content.
Optimistic version checks prevent stale writes. Provider sequence is retained when available;
otherwise PIE orders by event time, observation time, then stable event ID and flags ambiguity.

Periodic full reconciliation compares provider snapshots with PIE aliases and checksums. Missing
events, stale projections, duplicates, and partial failures produce findings rather than silent
repair. Reprocessing is safe because revision, audit, and outbox writes commit atomically.

## Projection and graph strategy

Immutable revisions are the write model. PostgreSQL projection tables serve current state, work
hierarchy, capability and dependency graphs, dashboards, and agent context. Projections carry their
source revision and can be rebuilt. Relational adjacency lists and recursive queries are the first
graph implementation; a graph database requires measured need and a new ADR.

## Agent interfaces and memory

Agents never write tables directly. They read current or historical revisions, future graph and
dashboard projections, and scoped context packages; they write controlled reconciliation commands
or proposals. PIE supplies project memory while MemoryOS supplies governed storage and retrieval.
Retrieval filters tenant, project, role, sensitivity, retention, and freshness before ranking.
Context Builder budgets tokens, prefers authoritative fresh sources, includes provenance, and reports
omissions. Summaries remain derived artifacts and cannot replace sources.

## Provenance, evidence, authorization, and governance

PIE adapts W3C PROV's Entity, Activity, and Agent concepts as source, observation or transformation,
and responsible actor metadata. Material assertions reference evidence when available. Writes use
OIDC or workload identity, tenant and project authorization, delegation limits, policy and budget
checks, and approval gates. Secrets, hidden model reasoning, and unrestricted transcripts are
prohibited state. Cross-tenant paths continue to return stable `404` responses.

## Cost and usage telemetry

Usage records provider, model or tool, operation, agent, workflow, project, input, cached, output and
reasoning tokens where supplied, quantity, versioned price, currency, estimate, actual, and billing
reconciliation status. Forecasts use remaining work, historical consumption, retry and review rates,
and scenario ranges. The Budget Engine evaluates work before admission; actuals reconcile estimates.

## Confidence and completion forecasting

Confidence is structured, not a model claim. Initial factors are source authority (30%), evidence
coverage (25%), freshness (15%), cross-source agreement (15%), validation quality (10%), and forecast
calibration (5%). Disputes cap the score. Each score retains factors, evidence, explanation,
algorithm version, and time.

Completion forecasting uses dependency-aware Monte Carlo simulation over remaining effort,
throughput, risks, validation rework, and capacity. It returns P50/P80/P95 ranges, assumptions,
excluded work, confidence, and model version. Sparse history produces explicitly low-confidence
heuristics. Recommendations carry expected value, urgency, readiness, risk, effort, cost, confidence,
rationale, and evidence; policy filters precede ranking and sensitive work requires approval.

## GitHub and Temporal integration

Authenticated GitHub webhooks normalize provider events and deduplicate delivery IDs; scheduled
polling repairs missed deliveries. Commits, branches, PRs, reviews, issues, milestones, dependencies,
and Actions remain evidence-producing provider records. PIE owns stable identity and effective state.

Temporal runs long-lived synchronization, reconciliation, forecast recomputation, and approval
flows. Workflow IDs derive from project and idempotency key. Activities perform idempotent provider
I/O. PIE database transactions are the business commit boundary; Temporal history is execution and
recovery evidence.

## Observability, recovery, and contracts

Ingestion emits correlation IDs, structured logs, metrics, audit events, and outbox events. Service
levels cover event lag, freshness, backlog, conflict age, forecast calibration, and stale sources.
Operators can replay checkpoints, rebuild projections, or run full reconciliation; checksums expose
drift. The canonical schema is
`docs/genesis/schemas/project-intelligence-state.schema.json`. The initial additive event is
`genesis.project-intelligence.state-reconciled`; consumers deduplicate by event ID and ignore unknown
fields.

## Rollout

1. Immutable state revision API and repository bootstrap document.
2. Normalized work items, aliases, graph edges, and projections.
3. GitHub webhook ingestion, polling reconciliation, and conflict queue.
4. Validation, evidence, sprint, risk, and debt projections.
5. Token usage, actual cost, forecasting, and budget admission integration.
6. MemoryOS context views and multi-agent proposals.
7. Recommendations, completion forecasting, executive dashboard, and Genesis project template.

The existing YAML session file remains a bootstrap aid until imported into a registered project; it
is not silently treated as a database fact.
