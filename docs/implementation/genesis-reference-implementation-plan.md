# Devsembly Genesis Reference Implementation Plan

**Version:** 0.1  
**Status:** Implementation in progress  
**Target:** First deployable, end-to-end Devsembly reference implementation

## 1. Purpose

This plan converts the Devsembly architecture and roadmap into the smallest working release that proves the platform can accept an objective, apply organizational and budget constraints, plan work, execute a controlled software change, validate the result, and preserve the decision trail.

Genesis v0.1 is not a complete enterprise platform. It is the first coherent vertical slice of the Devsembly operating model.

## 2. Release mission

Genesis v0.1 must demonstrate this workflow:

```text
Create organization
  -> create initiative
  -> assign monthly budget
  -> capture objective and acceptance criteria
  -> generate a governed implementation plan
  -> create traceable source-control work
  -> execute a small software change
  -> run independent validation
  -> produce a pull request
  -> record cost, evidence, decisions, and outcome
```

A release is successful only when this path works end to end on a supported Development Host.

## 3. Current scaffold

The first runnable scaffold now provides:

- FastAPI control-plane API and health endpoints;
- Temporal client, workflow, and worker process;
- SQLAlchemy 2.x asynchronous database engine and session contract;
- Alembic configuration and an initial Genesis schema migration;
- organization, initiative, project, budget, decision, workflow-run, audit-event, and transactional-outbox tables;
- repository protocols, SQLAlchemy repository adapters, and an explicit asynchronous Unit of Work;
- versioned organization, initiative, project, and budget APIs with parent-path isolation;
- project-scoped workflow-run APIs with durable intent, lifecycle transitions, cancellation,
  retry lineage, ordered steps, completed attempts, and idempotent creation;
- immutable project cost evaluations with budget snapshots, fixed-precision option totals,
  deterministic lower-cost recommendations, and observe, warn, and block outcomes;
- proposed, approved, and rejected decision records with finality, declared human
  provenance, budget authorization snapshots, and optimistic concurrency;
- optimistic concurrency, database-enforced budget invariants, and atomic outbox writes;
- PostgreSQL-backed readiness checking;
- local PostgreSQL, Redis, MinIO, Temporal, API, worker, and migration services through Docker Compose;
- API, domain, schema, transaction, isolation, migration, and PostgreSQL integration tests;
- local-development and migration instructions.

This proves the selected runtime, organization-to-budget persistence path, durable
workflow intent before provider dispatch, and explicit cost-and-decision governance. It
does not yet complete Temporal dispatch, identity, actual usage ingestion, adaptive
forecasting, evidence, audit publication, or operator capabilities.

## 4. Mandatory capabilities

| Capability | Minimum v0.1 behavior |
|---|---|
| Organization registry | Create and retrieve one organization with mission, owner, policies, and active status |
| Initiative registry | Create an initiative linked to an organization with objective, priority, status, sponsor, and success criteria |
| Project registry | Link one or more repositories and execution targets to an initiative |
| Budget profile | Set monthly, one-time, AI, and infrastructure limits; report remaining and forecasted spend |
| Decision record | Store context, options, selected action, cost impact, risk, confidence, approver, and outcome |
| Agent registry | Register named agents with role, permissions, authority level, provider, and status |
| Governed workflow | Execute a durable workflow with explicit stages, retries, approval gates, and escalation |
| Source-control integration | Create or link a work item, branch, commit, pull request, and CI evidence |
| Validation | Run deterministic checks independently from the implementation agent |
| Memory and knowledge | Persist project context, decisions, evidence, summaries, and lessons in a searchable store |
| Audit events | Record who or what performed each meaningful action and when |
| Operator view | Show initiative status, budget health, workflow stage, approvals, evidence, and failures |

## 5. Budget-aware behavior

A project can be initialized with a constraint such as `$50/month`. The platform must:

1. Store the declared limit and allowed flexibility.
2. Estimate the monthly cost of recommended infrastructure, AI providers, and external services.
3. Reject or escalate a plan that exceeds the approved limit.
4. Offer a lower-cost alternative when one satisfies the acceptance criteria.
5. Reforecast when usage or project maturity changes.
6. Preserve the rationale behind every budget recommendation.

## 6. Explicitly deferred

- CompanyOS business modules
- Marketplace and third-party plugin distribution
- Multi-region or active-active deployment
- Kubernetes
- Enterprise SSO and SCIM
- Full accounting, CRM, HR, fleet, dispatch, or ERP capabilities
- Autonomous production releases without human approval
- Custom foundation models
- General-purpose knowledge graph infrastructure
- Complex chargeback and revenue recognition
- Native mobile applications
- Large-scale multi-tenant isolation

## 7. Reference architecture

Genesis v0.1 begins as a modular monolith plus workers, not a fleet of microservices.

```text
Operator UI / API
        |
Application Core
  - organizations
  - initiatives
  - projects
  - budgets
  - decisions
  - agents
  - approvals
        |
Workflow Runtime ---- Worker adapters ---- AI/tool providers
        |
PostgreSQL ---- Object storage ---- optional Redis
        |
Source-control provider and validation runners
```

PostgreSQL is authoritative for structured state. Temporal owns durable workflow execution. MinIO stores large evidence objects. Redis is limited to ephemeral caching and coordination.

## 8. Acceptance tests

Genesis v0.1 is complete when:

- a user can authenticate through the configured OIDC provider;
- a user can create an organization, initiative, and project;
- a user can set a `$50/month` project budget;
- recommendations include one-time and recurring estimates;
- a plan over the hard limit is blocked or escalated;
- a compliant lower-cost option is offered when available;
- material selections produce decision records;
- work begins from a traceable source-control item;
- implementation occurs in an isolated branch or workspace;
- implementation and validation use separate roles;
- workflow state survives process restart;
- evidence and immutable audit events are persisted;
- the final result links to source-control and validation artifacts.

## 9. Milestones

### G0 — Baseline locked

- Reference implementation plan approved
- Architecture decisions recorded
- Supported-host bootstrap remains green

### G1 — Domain foundation

- Runtime and local data-service scaffold — current
- Organization, initiative, project, budget, decision, workflow-run, workflow-step,
  step-attempt, audit, and outbox schema — current
- Repository, Unit of Work, organization, initiative, project, budget, cost-evaluation,
  decision, workflow-run, step-attempt, and outbox-write path — current
- Database migrations and round-trip validation — current
- API, unit, and PostgreSQL integration tests for registry, cost governance, decisions,
  and workflow persistence — current
- Cost evaluation, deterministic budget recommendations, decision finality, and
  transactional events — current
- OIDC authentication, organization membership, roles, delegations, and authorization —
  current
- Immutable evidence ingestion, authorized retrieval, retention metadata, and the MinIO
  object-storage adapter — current
- Append-only audit writers for state and authorization decisions — current
- Idempotent transactional-outbox publication, retry, recovery, and worker health —
  current
- Actual usage and adaptive forecasting — remaining

### G2 — Governed workflow skeleton

- Durable workflow intent, ordered steps, completed attempts, cancellation, and retry
  lineage — current
- Temporal dispatch, durable provider execution, approval gates, and evidence — remaining
- Mock implementation and validation agents
- Recovery and idempotency tests

### G3 — Source-control vertical slice

- Real provider adapter
- Work item, branch, commit, pull request, and CI evidence flow
- Independent validation role

### G4 — Budget-aware execution

- Cost estimate contract — current
- Explicit budget evaluation and observe, warn, and hard-stop behavior — current
- Deterministic lower-cost recommendation output — current
- Actual usage ingestion and adaptive monthly forecast — remaining
- Automatic governed-workflow admission and escalation — remaining

### G5 — Operator control surface

- Initiative and workflow status
- Approvals and escalation inbox
- Budget and cost view
- Audit and evidence view

### G6 — Genesis release candidate

- End-to-end demonstration on a fresh supported host
- Security review
- Backup and recovery test
- Operating runbook
- Known limitations and upgrade notes

## 10. Anti-overengineering constraints

Genesis v0.1 must not introduce the following without a separate approved ADR and measured need:

- Kubernetes or service mesh
- Multi-region architecture
- More than one durable source of truth for core records
- Event sourcing as the default persistence model
- A custom database, queue, workflow scheduler, identity provider, or secret manager
- Separate deployable service for every domain module
- Autonomous production mutation without a human-controlled policy gate
- A generalized ontology intended to model every possible business domain

Prefer direct, testable interfaces and reversible decisions.

## 11. Next implementation backlog

Completed in the issue #21 slice:

1. Repository and Unit of Work implementations over the SQLAlchemy session contract.
2. Organization, initiative, project, and monthly-budget services and APIs.
3. Atomic transactional-outbox writes for registry mutations.
4. PostgreSQL integration, migration round-trip, OpenAPI, isolation, and concurrency tests.
5. CI gates for migrations, linting, typing, tests, Compose, image builds, and stack health.

Completed in the issue #22 slice:

1. Persisted provider-neutral workflow intent before Temporal execution.
2. Added ordered workflow steps, immutable completed attempts, lifecycle transitions,
   cancellation, retry lineage, and optimistic concurrency.
3. Added exact idempotent create/retry replay and conflict handling.
4. Removed the direct unpersisted Temporal start API.
5. Added workflow migration, API, PostgreSQL, transition, isolation, and outbox tests.

Completed in the issue #23 slice:

1. Added immutable provider-neutral cost evaluations with budget and algorithm snapshots.
2. Derived one-time and monthly totals from decimal line items.
3. Added observe, warn, block, budget-revision, and acceptance-criteria approval guards.
4. Added deterministic lower-cost recommendations with preserved rationale.
5. Added proposed and final decision APIs with concurrency, finality, declared human
   provenance, and transactional outbox events.
6. Added migration, OpenAPI, isolation, idempotency, PostgreSQL, and `$50/month` tests.

Completed in the evidence lifecycle slice:

1. Added immutable Base64 evidence ingestion with server-generated, content-addressed
   object keys.
2. Added organization- and project-authorized metadata and content retrieval.
3. Added SHA-256 and size verification before content is returned.
4. Added server-derived transient, standard, compliance, and permanent retention
   metadata with database invariants.
5. Added compensating object cleanup, transactional outbox records, migration, API,
   storage, isolation, integrity, and retention tests.

Completed in the audit and event-publication slice:

1. Added correlated append-only audit records for important domain writes and explicit
   allow/deny authorization outcomes.
2. Added a leased PostgreSQL outbox publisher with bounded exponential retry scheduling
   and safe takeover after worker crashes.
3. Added the durable `published_events` feed, keyed by source event UUID, and atomic
   publication acknowledgement to prevent duplicate publication.
4. Added persisted worker heartbeats, a container health check, and API readiness
   reporting.
5. Added PostgreSQL idempotency, backoff, crash-recovery, heartbeat, audit-atomicity,
   migration, Compose, and live-stack validation.

Completed in the Temporal dispatch slice:

1. Added a durable consumer of committed workflow-run events from `published_events`.
2. Added stable Temporal workflow IDs, leased dispatch claims, bounded retry scheduling,
   and duplicate-start reconciliation through Temporal workflow-ID uniqueness.
3. Added an atomic PostgreSQL reservation that moves accepted runs to queued before the
   network call, preserving recovery when either PostgreSQL or the dispatcher restarts.
4. Added a provider-neutral committed-run Temporal workflow boundary, dispatcher
   heartbeat, container health check, and API readiness reporting.
5. Added PostgreSQL publication-gating, retry, lease takeover, post-start crash recovery,
   duplicate-prevention, migration, Compose, and live-stack validation.

Next:

1. Connect workflow admission to cost evaluation and decision state.
2. Add actual usage ingestion, adaptive forecasting, and the first complete
   end-to-end `$50/month` acceptance scenario.
3. Connect Temporal workflow signals and activities to persisted step attempts,
   cancellation, provider execution, and evidence.
