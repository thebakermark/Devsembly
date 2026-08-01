# ADR 0012 — GitHub Is a Provider

- **Status:** Accepted
- **Date:** 2026-07-30
- **Decision owners:** Devsembly Architecture
- **Applies to:** Source control and work tracking

## Context

Genesis uses GitHub repositories, issues, branches, pull requests, reviews, checks, and
releases. Treating GitHub as the whole system of record would place organizational
policy, memory, budgets, workflows, and identity behind one vendor's model.

## Decision

GitHub is the initial source-control and work-tracking provider and the authoritative
system of evidence for records it produces. Devsembly depends on source-control and work
tracking capability contracts, stores provider-neutral correlations, and retains its own
organization, policy, workflow, budget, decision, memory, and audit authority.

GitHub-specific IDs, permissions, webhooks, rate limits, and commands remain inside the
adapter and provider guide.

## Consequences

Genesis can use GitHub's mature delivery controls while keeping future replacement
possible. Correlation, event reconciliation, and normalized provider behavior add work.
Some GitHub features may remain optional extensions.

## Alternatives considered

- **GitHub as the Devsembly brain:** rejected due to domain mismatch and lock-in.
- **Build source control and work tracking:** rejected as unnecessary and unaffordable.
- **Avoid provider-specific features:** rejected; optional features may be declared
  without leaking into core contracts.

## Security impact

The adapter uses least-privilege app or token scopes, verifies webhook signatures,
redacts credentials, protects branches, and audits writes. Repository access does not
grant organization, budget, or production authority.

## Budget impact

The initial plan uses available GitHub features without requiring a new managed service.
Paid features require explicit cost and capability review. Export and replacement costs
must remain visible.

## Implementation constraints

- Store internal stable IDs plus provider correlations.
- Make writes idempotent and reconcile webhook delivery.
- Normalize rate-limit, permission, conflict, and unavailable errors.
- Preserve source-control evidence links and immutable commit identifiers.
- Keep provider commands out of domain services.

## Validation criteria

Contract tests cover work item, branch, commit, pull request, review, status, webhook,
permission, rate-limit, and idempotency behavior, with a conforming fake for application
tests.

## Review triggers

Review when GitHub cost, availability, customer requirements, data location, or feature
gaps justify another provider.

## References

- [Source-control provider example](../../genesis/provider-sdk/examples/source-control-provider.json)
- [Capability and provider model](../capability-provider-model.md)
- [ADR 0005](0005-provider-independence.md)
