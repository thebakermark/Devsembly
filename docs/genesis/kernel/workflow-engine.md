# Workflow Engine Contract

**Status:** Binding boundary; business workflow implementation planned
**Version:** 0.1.0

## Ownership boundary

Devsembly owns workflow definitions, organization policy, budgets, approvals, decision
records, and audit. The workflow provider owns durable execution, history, timers,
signals, retries, and task delivery.

Temporal is the accepted Genesis adapter under
[ADR 0002](../../architecture/decisions/0002-temporal-durable-workflow-engine.md).

## Required operations

The contract supports register definition, start, inspect, signal, request cancellation,
terminate under authority, query status, list correlated executions, and obtain sanitized
execution evidence.

## Start contract

A start request includes workflow type and version, workflow and idempotency IDs,
organization, initiative and project correlations, principal and delegation, budget
context, input schema version, timeout, retry policy, and trace context.

## Execution rules

- Workflow logic is deterministic where the provider requires replay.
- External effects occur through idempotent activities.
- Every activity defines start-to-close timeout, retry classification, heartbeat when
  needed, and cancellation behavior.
- Human approvals use durable waits and bind the exact action under approval.
- Cost and retry limits can stop or escalate work.
- Workflow history never stores raw secrets.

## Portability

Devsembly persists provider-neutral workflow correlation and business decisions.
Provider-specific run IDs remain correlations. Export and migration may resume at a safe
business checkpoint rather than reproduce proprietary execution history.

## Validation

Contract tests cover start idempotency, signal, approval wait, restart, activity retry,
timeout, cancellation, duplicate effect prevention, version rollout, unavailable
provider, and correlated audit evidence.
