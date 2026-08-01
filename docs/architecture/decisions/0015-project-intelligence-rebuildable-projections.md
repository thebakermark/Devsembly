# ADR-0015: Project Intelligence Uses Rebuildable Relational Projections

- Status: Accepted
- Date: 2026-07-31

## Context

ADR-0014 established immutable whole-state revisions as PIE's canonical write model. Agents and
operators also need efficient hierarchy and graph reads, stable provider identity mapping, and a
recovery path that does not reinterpret chat history or call external providers.

## Decision

PIE will derive project-scoped current read models for work items, provider aliases, capability
nodes and edges, and dependency nodes and edges from each accepted revision. Reconciliation will
validate the complete candidate projection before atomically writing the revision, projection,
audit, and outbox event. A checkpoint identifies the exact source revision, version, and rebuild
time even when every projected collection is empty.

Provider aliases are scoped by provider, account, external kind, and external ID and resolve to a
canonical PIE ID. Work parents and graph endpoints must resolve inside the same project. Work-item
kind rules and cycle checks are enforced before persistence. Only the latest immutable revision may
replace the current projection. PostgreSQL adjacency lists remain the graph implementation.

## Rationale

Rebuildable projections preserve one canonical history while providing bounded, indexed reads for
agents and APIs. Whole-projection replacement is deterministic and simple at current Genesis scale.
It also makes partial projection failure recoverable without mutating or replaying provider state.

## Alternatives

- Query JSON revisions for every read: rejected because hierarchy, alias, and graph queries would be
  inefficient and difficult to constrain.
- Mutable entity tables as a second write model: rejected because drift and conflict authority would
  become ambiguous.
- Incremental projection patches only: deferred until scale data justifies the extra recovery logic.
- Graph database: deferred because PostgreSQL satisfies the current traversal and budget needs.
- Provider IDs as primary keys: rejected because provider migration and multi-provider identity would
  leak into the canonical model.

## Consequences

- Projection rows are disposable and never authoritative without their source revision.
- Reconciliation cost grows with projected state size until an incremental strategy is justified.
- Alias, parent, endpoint, relationship, and cycle errors reject the entire candidate revision.
- Historical revisions remain readable but cannot accidentally displace the current projection.

## Security and budget impact

Existing parent-path authorization applies to all reads and rebuild commands. Cross-project
references are rejected before write. No new service or paid graph infrastructure is introduced.

## Implementation constraints

- Replacement and rebuild occur inside the existing Unit of Work.
- Projection events contain identifiers and counts, not raw project state.
- Schema and service validation must agree on stable IDs, aliases, and relationship vocabulary.
- A later incremental projector must retain deterministic full-rebuild parity.

## Validation

- API tests cover hierarchy and graph reads, aliases, full replacement, and rebuild recovery.
- Domain tests reject invalid parents, cycles, unknown endpoints, and duplicate aliases.
- PostgreSQL tests cover revision/checkpoint linkage and projected row persistence.
- Alembic upgrade, downgrade, and model parity remain CI gates.

## Review triggers

Review when full replacement exceeds latency targets, projections need independent retention,
recursive PostgreSQL queries miss objectives, or a second canonical writer is proposed.
