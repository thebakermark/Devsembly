# ADR 0010 — Executive Core Governs Workflow

- **Status:** Accepted
- **Date:** 2026-07-30
- **Decision owners:** Devsembly Architecture
- **Applies to:** Work coordination and policy

## Context

Durable workflow engines coordinate tasks and state but should not decide organizational
purpose, authority, budget, risk acceptance, provider choice, or success. Placing those
rules inside a workflow product would couple governance to one provider.

## Decision

The proposed Executive Core, also called the Mayor, owns authorized objective
interpretation, policy and budget evaluation, plan coordination, capability selection,
approval requests, escalation, and decision provenance. It invokes workflows through a
provider-independent contract.

The workflow provider owns durable mechanics such as history, timers, retries, signals,
and task delivery. Human authority remains final. Genesis implements Executive Core
behavior incrementally in application services and governed Temporal workflows rather
than as a separate service.

## Consequences

Organizational policy remains portable and explainable. The boundary between business
coordination and workflow mechanics requires discipline and correlation across stores.

## Alternatives considered

- **Workflow definitions own all policy:** rejected due to provider lock-in and weak
  organizational modeling.
- **LLM agent as executive authority:** rejected because inference cannot create
  authority.
- **Separate Executive Core service now:** deferred under the modular-monolith decision.

## Security impact

Every action must carry principal, delegation, organization, policy decision, budget,
risk, and correlation context. The Executive Core cannot approve its own high-risk work
or enlarge its permissions.

## Budget impact

Policy evaluates estimated and actual provider cost before execution. Bounded retries,
tool calls, and escalation protect the active budget. No separate service is required
for Genesis.

## Implementation constraints

- Preserve Temporal behind `WorkflowProvider`.
- Keep external calls in activities or adapters.
- Record material plan and policy decisions in Devsembly.
- Use deterministic, versioned workflows and idempotent activities.
- Require human signals for actions outside delegated authority.

## Validation criteria

A workflow can pause for policy, budget, and human gates; survive restart; resume without
duplicate effects; and produce correlated decision and audit evidence independent of
Temporal's internal history.

## Review triggers

Review when coordination requires independent scaling, a different workflow provider, or
new authority models.

## References

- [ADR 0002](0002-temporal-durable-workflow-engine.md)
- [Workflow engine contract](../../genesis/kernel/workflow-engine.md)
- [Book V — Agent Handbook](../../genesis/book-5-agent-handbook.md)
