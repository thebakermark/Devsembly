# Identity and Policy

**Status:** Binding boundary; implementation planned
**Version:** 0.1.0

## Principal model

Humans, agents, services, and providers are distinct principal types with stable internal
IDs. External identities map by issuer and subject. Email, provider login, and agent name
are attributes, not primary identity.

## Authentication

External OIDC establishes human identity under
[ADR 0003](../../architecture/decisions/0003-oidc-external-identity.md). Machine
identities use separate short-lived credentials or workload identity. Authentication
does not imply organization membership or permission.

## Authorization context

Decisions evaluate principal, organization, role and assignment, active delegation,
action, resource, data scope, environment, risk, budget, time, approval, and applicable
policy versions.

The result is `allow`, `deny`, or `requires_approval`, with decision ID, matched policy,
reason code, obligations, expiry, and audit correlation. Missing high-risk context denies
access.

## Delegation

A delegation records grantor, recipient, actions, resources, data, environment, financial
limit, risk limit, conditions, start, expiry, delegability, and revocation. Agents cannot
self-delegate.

## Policy precedence

Law and regulation, Constitution, tenant governance, department policy, position
procedure, workflow instruction, and task instruction apply in descending order. A lower
level cannot override a higher denial.

## Validation

Tests cover issuer and subject mapping, organization isolation, expired and revoked
delegation, approval binding, budget ceiling, conflicting policy, agent versus human
identity, break-glass audit, and denied-by-default behavior.
