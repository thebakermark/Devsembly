# ADR 0002 — Temporal Durable Workflow Engine

- **Status:** Accepted
- **Date:** 2026-07-30
- **Decision owners:** Devsembly Architecture
- **Applies to:** Genesis v0.1

## Context

Devsembly workflows must survive process restarts, support retries and timeouts, pause for human approval, enforce budgets and policy gates, preserve execution history, and escalate repeated failures without losing state.

A simple in-process job queue cannot reliably provide durable, long-running orchestration. Building a custom workflow engine would duplicate difficult infrastructure and create significant correctness risk.

## Decision

Use **Temporal** as the Genesis durable workflow engine through a Devsembly workflow-provider interface.

Temporal owns durable orchestration state, timers, retries, signals, and workflow history. Devsembly owns business policy, authorization, budget evaluation, approval rules, agent contracts, and audit records.

For Genesis, Temporal may run self-hosted on the same development host using PostgreSQL-backed persistence. Production topology remains configurable and may later use a managed Temporal-compatible service.

## Alternatives considered

### Custom PostgreSQL state machine

Lower initial dependency count, but rejected as the primary engine because durable timers, replay safety, retries, cancellation, signaling, and versioning are complex to implement correctly.

### Celery or RQ

Useful task queues, but not sufficient as the authoritative engine for long-running, human-in-the-loop workflows.

### Prefect or Dagster

Strong data-workflow platforms. Not selected because Devsembly requires general application orchestration and human approvals rather than primarily data pipelines.

### Archon as the durable system of record

Archon remains an integration and workflow-specification capability, but durable execution must sit behind a stable Devsembly provider contract so the platform is not coupled to one product.

## Consequences

### Positive

- durable execution across restarts;
- built-in retries, timers, cancellation, and signals;
- deterministic workflow histories;
- support for human approval pauses;
- easier recovery and operational inspection;
- avoids building a custom orchestration engine.

### Negative

- additional services and operational knowledge;
- workflow code must follow deterministic-execution rules;
- versioning requires disciplined rollout practices;
- local development consumes more memory than an in-process queue.

## Budget impact

The Genesis deployment will self-host Temporal on the existing development host, producing no separate subscription cost. Resource usage must be measured. If Temporal causes the project to exceed the active monthly budget, nonessential services must be reduced before increasing infrastructure.

## Security impact

- Temporal endpoints must not be publicly exposed.
- Worker identities use least-privilege credentials.
- Secrets must be passed to activities through secure references, never stored in workflow histories.
- Sensitive payloads require encryption or redaction through a payload codec.
- Devsembly audit records remain authoritative for business approvals and policy decisions.

## Implementation constraints

- All workflows must use a Devsembly workflow-provider interface.
- Business workflows must be deterministic and versioned.
- External calls occur only in activities, not workflow logic.
- Every activity defines timeout, retry, idempotency, and failure classification.
- Human approvals use signals and durable waiting states.
- Workflow history must correlate to project, initiative, budget, work item, and audit identifiers.
- A local test environment must support time-skipping workflow tests.

## Validation

This decision is validated when a Genesis workflow can start, pause for approval, survive worker and application restarts, resume, retry a controlled failure, enforce a budget gate, and finish with a complete correlated audit trail.

## Review triggers

Review if measured operating cost exceeds budget, Temporal cannot meet deployment constraints, or another engine demonstrates equivalent durability with materially lower complexity.
