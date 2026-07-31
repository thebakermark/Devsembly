# Devsembly Genesis Library

**Library version:** 0.1.7
**Status:** Active foundation
**North Star:** **Engineer organizations that learn faster than the world changes.**

The Genesis Library is Devsembly's coherent, versioned governance and architecture
system. It defines why Devsembly exists, who holds authority, how the platform is
structured, how work is engineered and operated, and how organizations are modeled.

The library governs both human and agent work. It describes contracts and required
behavior; it does not claim that every described capability is implemented.

## Authority order

When two artifacts conflict, the higher artifact controls:

1. [Book 0 — Philosophy](book-0-philosophy.md)
2. [Book I — Constitution](book-1-constitution.md)
3. [Accepted ADRs](../architecture/decisions/README.md)
4. [Book II — Architecture](book-2-architecture.md)
5. [Book III — Engineering Standards](book-3-engineering-standards.md)
6. [Book IV — Operations Manual](book-4-operations-manual.md)
7. [Book V — Agent Handbook](book-5-agent-handbook.md)
8. [Book VI — Organizational Genome](book-6-organizational-genome.md)
9. Product and module specifications
10. Implementation

A lower-level artifact MUST NOT contradict a higher-level artifact. Discovery of a
conflict stops the affected decision or change until the conflict is resolved at the
proper authority level.

## Status language

| Label | Meaning |
|---|---|
| **Binding** | Approved and required for the stated scope |
| **Current** | Implemented and validated in the repository |
| **Proposed** | Designed for review but not approved as binding |
| **Deferred** | Intentionally outside the current delivery scope |
| **Example** | Illustrative and nonbinding |

The accepted Genesis v0.1 ADRs and
[reference implementation plan](../implementation/genesis-reference-implementation-plan.md)
are binding for Genesis. Broader Kernel, Executive Core, MemoryOS, knowledge-graph,
plugin-marketplace, and business-module designs are future-state specifications unless
an accepted ADR and implementation evidence say otherwise.

## Library map

| Area | Purpose |
|---|---|
| [Books](#authority-order) | Philosophy, governance, architecture, standards, operations, agents, and organization models |
| [ADR map](adr/README.md) | Genesis decision sequence mapped to canonical repository ADR numbers |
| [Kernel](kernel/README.md) | Future-state platform boundary and component contracts |
| [Provider SDK](provider-sdk/README.md) | Stable capability and provider contracts |
| [Schemas](schemas/README.md) | Machine-readable contract schemas |
| [Ontologies](ontologies/README.md) | Canonical concepts and relationships |
| [Reference models](reference-models/README.md) | Nonbinding examples and current-state mappings |
| [Registry API v1](api-reference.md) | Current organization, initiative, project, and budget HTTP contract |
| [Workflow Run API v1](workflow-run-api.md) | Current workflow intent, lifecycle, step, attempt, cancellation, and retry contract |
| [Cost Governance API v1](cost-governance-api.md) | Current cost evaluation, budget recommendation, and decision-record contract |
| [Evidence API v1](evidence-api.md) | Current immutable ingestion, authorized retrieval, integrity, and retention contract |
| [Project Intelligence API v1](project-intelligence-api.md) | Current immutable project-state contract plus rebuildable work, alias, and graph projections |
| [GitHub Synchronization API](github-synchronization-api.md) | Signed event ingestion, delivery deduplication, freshness, conflicts, and recovery |
| [Capability catalog](capability-catalog.md) | Capability ownership, maturity, and provider boundaries |
| [Traceability matrix](traceability-matrix.md) | Requirements-to-decision-to-evidence mapping |
| [Glossary](glossary.md) | Canonical terms |

## Change rules

- Changes to Book 0 or Book I require the constitutional amendment process.
- Accepted ADRs are immutable except for status and superseding links.
- Normative changes to Books II–VI require a linked work item, impact analysis,
  independent review, validation evidence, and human approval.
- Schemas and provider contracts use semantic versions and preserve compatibility or
  publish an explicit migration path.
- Examples MUST identify their nonbinding status.
- Secrets, access tokens, personal credentials, and machine-specific values MUST NOT
  appear in the library.

## Version history

| Version | Date | Change |
|---|---|---|
| 0.1.7 | 2026-07-31 | Added GitHub event ingestion and durable reconciliation state |
| 0.1.6 | 2026-07-31 | Added canonical work items, provider aliases, capability/dependency projections, and rebuild recovery |
| 0.1.5 | 2026-07-31 | Added Project Intelligence architecture, canonical state schema, and immutable revision API |
| 0.1.4 | 2026-07-30 | Added evidence ingestion, authorized retrieval, integrity verification, and retention policy |
| 0.1.3 | 2026-07-30 | Added cost evaluation, budget recommendations, and governed decisions |
| 0.1.2 | 2026-07-30 | Added persisted workflow intent, lifecycle, steps, attempts, cancellation, and retry |
| 0.1.1 | 2026-07-30 | Added the current Genesis Registry API and persistence evidence |
| 0.1.0 | 2026-07-30 | Initial coherent Genesis Library |
