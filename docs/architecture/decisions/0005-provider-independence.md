# ADR 0005 — Provider Independence

- **Status:** Accepted
- **Date:** 2026-07-30
- **Decision owners:** Devsembly Architecture
- **Applies to:** Platform-wide

## Context

Devsembly depends on source control, work tracking, LLMs, coding agents, identity,
databases, storage, workflow orchestration, containers, infrastructure, deployment, and
monitoring. Embedding provider APIs in domain policy would make provider cost, outages,
contract changes, and replacement platform-wide risks.

## Decision

External systems implement versioned Devsembly capability contracts through adapters.
Domain and application policy depends on those contracts, not provider products.
Provider selection is configuration governed by capability fit, permissions, health,
security, cost, data handling, support evidence, and exit behavior.

An initial provider may be authoritative for records it creates, but it does not become
the authority for unrelated organization policy, workflow, memory, budget, or decisions.

## Consequences

Provider replacement and testing become tractable, and provider-specific risk remains
localized. Contract design, adapters, conformance suites, normalized errors, and
migration support add work. A leaky abstraction must be corrected rather than hidden.

## Alternatives considered

- **Direct provider integration:** faster for one path but spreads lock-in and policy
  coupling.
- **Lowest-common-denominator contract:** rejected because it would erase useful
  capability; contracts may expose optional declared features.
- **Build every dependency:** rejected as costly and contrary to Genesis scope.

## Security impact

Credentials remain inside adapters and use least privilege. Contracts must declare data
scope, secret handling, permissions, audit events, failure modes, and revocation.
Switching providers requires a security and data-remanence review.

## Budget impact

Provider cost and exit cost become selection inputs. Self-hosted or lower-cost providers
may satisfy the Genesis `$50/month` constraint. An adapter must not silently enable paid
features or exceed an authorized limit.

## Implementation constraints

- Provider contracts use semantic versions.
- Adapters normalize timeouts, errors, idempotency, health, lifecycle, events, and
  observability.
- Domain models do not use provider identifiers as primary identities.
- Supported status requires current conformance evidence and replacement guidance.

## Validation criteria

At least one provider adapter must pass its capability contract suite, and a conforming
fake or alternate adapter must run the same application behavior without domain changes.

## Review triggers

Review when contracts repeatedly leak provider semantics, replacement requires core
policy changes, or a capability cannot be represented without material performance or
security loss.

## References

- [Book II — Architecture](../../genesis/book-2-architecture.md)
- [Provider SDK](../../genesis/provider-sdk/README.md)
- [Capability and provider model](../capability-provider-model.md)
