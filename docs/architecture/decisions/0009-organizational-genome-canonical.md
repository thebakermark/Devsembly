# ADR 0009 — Organizational Genome Is Canonical

- **Status:** Accepted
- **Date:** 2026-07-30
- **Decision owners:** Devsembly Architecture
- **Applies to:** Organizational modeling

## Context

Roles, departments, authority, policies, skills, workflows, budgets, and agent
assignments otherwise become duplicated across applications and tenants. Reusable
reference knowledge also needs provenance and licensing separation from live tenant data.

## Decision

The Organizational Genome is the canonical model for reusable organization structure,
capability, responsibility, authority, policy, process, competency, knowledge, objective,
initiative, project, budget, assignment, evidence, and audit concepts.

Canonical templates are immutable and versioned. Tenant operational data uses overlays
and assignments that reference canonical versions without mutating them.

## Consequences

Applications share terminology and governance, and reusable knowledge can improve
without rewriting tenant history. Schema governance and mapping effort increase.
Canonical models must remain extensible without attempting to encode every industry in
the core.

## Alternatives considered

- **Application-specific organization models:** rejected as fragmenting authority.
- **Tenant records promoted automatically:** rejected due to privacy, provenance, and
  quality risk.
- **Universal ontology before use cases:** rejected; expand through validated needs.

## Security impact

Tenant operational data remains isolated. Canonical promotion requires de-identification,
provenance, license review, and approval. Assignments never infer permission without
active authority grants.

## Budget impact

Shared templates reduce repeated modeling and training cost. Runtime graph infrastructure
is deferred to preserve the Genesis budget.

## Implementation constraints

- Stable IDs, semantic versions, lifecycle, effective dates, provenance, and superseding
  links are required.
- Tenant overlays cannot mutate canonical records.
- Existing Phase 1 schemas remain authoritative until versioned successors exist.
- Capability grades, roles, and positions do not grant technical permissions.

## Validation criteria

Schemas validate canonical records and tenant overlays separately; historical assignments
resolve immutable versions; provenance and license rules block invalid promotion.

## Review triggers

Review when new industries require extension, schema evolution becomes incompatible, or
privacy and licensing rules require stronger package boundaries.

## References

- [Book VI — Organizational Genome](../../genesis/book-6-organizational-genome.md)
- [Organizational Genome foundation](../organizational-genome/README.md)
