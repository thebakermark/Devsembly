# ADR 0007 — Organizations Before Applications

- **Status:** Accepted
- **Date:** 2026-07-30
- **Decision owners:** Devsembly Architecture
- **Applies to:** Domain and product modeling

## Context

Devsembly coordinates work for organizations with purpose, people, agents, capabilities,
authority, policy, budgets, knowledge, and evidence. If applications become the root
model, identity, policy, cost, and learning fragment by interface or product.

## Decision

Organization is the primary governance and tenancy boundary. Applications and business
modules are interaction and capability surfaces operating within an organization's
authority, policy, data, and budget scope.

Genesis therefore creates an organization before initiatives, projects, budgets,
workflows, provider selections, and applications.

## Consequences

Governance and learning remain coherent across products. Every tenant-scoped record must
carry organization ownership, and application onboarding must resolve organization
context. This adds organization-aware authorization to otherwise simple features.

## Alternatives considered

- **Application as tenant:** rejected because one organization may use many applications.
- **User as root:** rejected because organizational authority and shared records outlive
  individual users.
- **Repository as root:** rejected because an initiative may span repositories and
  non-software work.

## Security impact

Organization scope is mandatory in authorization, data access, provider configuration,
audit, and evidence. Cross-organization access is denied by default and tested.

## Budget impact

Costs and forecasts can be allocated consistently by organization, initiative, project,
capability, and provider. Shared services require explicit allocation rules.

## Implementation constraints

- Tenant-scoped identifiers include organization ownership.
- Membership and delegation are internal Devsembly records.
- Applications may not create parallel organization authority models.
- Bootstrap and recovery preserve an accountable human owner.

## Validation criteria

Genesis can create an organization, reject access outside it, attach initiatives,
projects, budgets, providers, workflows, and audit records to it, and report organization
scope consistently.

## Review triggers

Review for personal single-user workspaces, cross-organization collaboration, legal
entity separation, or regulated isolation requirements.

## References

- [Book VI — Organizational Genome](../../genesis/book-6-organizational-genome.md)
- [Genesis reference implementation plan](../../implementation/genesis-reference-implementation-plan.md)
