# ADR 0006 — Kernel-First Platform Boundary

- **Status:** Accepted
- **Date:** 2026-07-30
- **Decision owners:** Devsembly Architecture
- **Applies to:** Platform architecture

## Context

Applications and business modules need shared identity, policy, capability discovery,
provider lifecycle, workflows, events, memory, configuration, and observability. If each
application assembles these independently, governance fragments and replacement becomes
unsafe. A prematurely separate microkernel service would conflict with the Genesis
modular-monolith decision.

## Decision

Define a Devsembly Kernel as the logical inward-facing platform boundary before expanding
applications. The Kernel owns stable ports and governance for shared platform
capabilities. Genesis implements these boundaries inside the modular monolith; it does
not require a separate service or dynamic plugin runtime.

Applications depend on Kernel contracts. Kernel contracts do not depend on applications
or provider implementations.

## Consequences

Shared governance and dependency direction become explicit, and later extraction remains
possible. Up-front contract work is required, and the Kernel must resist accumulating
business-module policy or becoming a universal abstraction.

## Alternatives considered

- **Application-first shared libraries:** rejected because policy and lifecycle would
  fragment.
- **Separate microkernel now:** deferred due to operational cost and lack of measured
  need.
- **Provider framework as the Kernel:** rejected because providers are replaceable
  infrastructure, not governance authority.

## Security impact

Central policy and provider boundaries create consistent enforcement and audit points.
The Kernel becomes security-sensitive and requires strict interfaces, least privilege,
input validation, and independent review.

## Budget impact

Logical boundaries add no service cost. A separate deployment, broker, or plugin sandbox
requires a future budget-aware ADR.

## Implementation constraints

- Preserve ADR 0001's modular monolith.
- Keep domain policy outside provider and framework code.
- Avoid dynamic loading until signing, permissions, isolation, lifecycle, and rollback
  are designed.
- Every Kernel component defines ownership, data authority, failure, and observability.

## Validation criteria

Dependency checks show applications and providers pointing toward Kernel ports without
reverse imports, and Genesis can run the contracts in one deployable application.

## Review triggers

Review when independent scaling, isolation, release ownership, or plugin distribution
justifies a process boundary.

## References

- [Kernel specification](../../genesis/kernel/kernel-specification.md)
- [ADR 0001](0001-python-fastapi-modular-monolith.md)
- [Book II — Architecture](../../genesis/book-2-architecture.md)
