# Kernel Specification

**Status:** Proposed
**Contract version:** 0.1.0

## Purpose

The Kernel gives applications one governed path to shared capabilities without owning
application-specific business rules. It preserves dependency direction and provider
independence while Genesis remains a modular monolith.

## Responsibilities

The Kernel defines ports for:

- capability registration and resolution;
- provider configuration, lifecycle, health, and conformance;
- identity, authorization, delegation, and policy decisions;
- durable workflow coordination;
- domain and integration events;
- memory and knowledge operations;
- typed configuration and secret references;
- logging, metrics, tracing, audit, and cost signals;
- plugin manifests, permissions, and lifecycle.

## Non-responsibilities

The Kernel does not own product UX, business-module policy, tenant objectives, provider
implementation details, organization-specific decisions, or workflow-engine internals.
It does not grant human authority or make itself the source of all application data.

## Dependency rules

1. Applications and modules depend on Kernel and domain contracts.
2. Kernel contracts may depend on canonical domain value types.
3. Provider adapters depend on Kernel and Provider SDK contracts.
4. Kernel and domain contracts do not depend on provider SDKs, frameworks, ORM entities,
   deployment systems, or applications.
5. Cross-boundary data uses versioned DTOs and stable error contracts.

## Core context

Every material call carries:

- correlation and causation identifiers;
- organization and principal identifiers;
- delegation or approval reference when required;
- capability and contract version;
- policy and budget context;
- idempotency key for mutating operations;
- deadline or timeout;
- classification and observability attributes that contain no secrets.

## Invariants

- Missing high-risk authority fails closed.
- Provider access cannot bypass identity, policy, audit, or budget.
- Events emitted from domain writes use the same transaction through the outbox.
- Unsupported provider behavior fails explicitly.
- All retries are bounded and safe for the operation's idempotency model.
- Health does not imply authorization or conformance.
- Kernel services remain usable with static configuration during Genesis.

## Error classes

`invalid_request`, `unauthenticated`, `unauthorized`, `policy_denied`,
`budget_denied`, `conflict`, `not_found`, `unsupported`, `rate_limited`,
`timeout`, `unavailable`, `integrity_failure`, and `internal_failure` are stable
categories. Adapters retain sanitized provider details as evidence without exposing them
to callers by default.

## Compatibility

Contracts use semantic versions. Additive optional fields may be backward compatible.
Removing or changing required behavior requires a major version, migration guide,
coexistence window where practical, and rollback.

## Genesis acceptance

The initial Kernel boundary is accepted when application services can use typed ports
for workflow, providers, policy, memory, and events inside one deployable service, with
dependency tests and no requirement for a separate runtime.
