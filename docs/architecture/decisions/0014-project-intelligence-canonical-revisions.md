# ADR-0014: Project Intelligence Uses Canonical Immutable Revisions

- Status: Accepted
- Date: 2026-07-31

## Context

Agents currently reconstruct state from repository files, GitHub, and session context. Those sources
have different authority, may arrive out of order, and cannot reproduce one trusted point-in-time
view. Genesis already supplies isolation, authorization, audit, evidence, outbox, and workflows.

## Decision

PIE will store an immutable project-scoped revision log in PostgreSQL. Each revision contains a
schema-versioned JSON state, SHA-256 checksum, parent link, idempotency key and request fingerprint,
source observation, assertion status, confidence, and explanation. Controlled reconciliation uses
optimistic concurrency and atomically emits existing audit and outbox records. Provider data is
synchronized through aliases and projections; it is not the canonical key space.

The initial implementation keeps state whole. Later normalized entity, edge, alias, and projection
tables may be added without changing the revision contract.

## Rationale

Immutable revisions provide reproducibility, auditability, deterministic rebuilds, safe replay, and
a clear boundary between verified fact and inference. PostgreSQL avoids premature graph or streaming
infrastructure. Whole-document storage makes the first slice coherent while the ontology evolves.

## Alternatives

- GitHub Projects as canonical state: rejected because it is a provider and cannot represent all
  governance, memory, evidence, cost, and forecast semantics.
- Mutable current-state rows only: rejected because point-in-time provenance would be incomplete.
- Event sourcing every entity immediately: deferred due to premature operational complexity.
- Graph database first: deferred; relational edges are sufficient for expected Genesis scale.
- Repository YAML only: retained as bootstrap/export, rejected as runtime concurrency boundary.

## Consequences

- Writes require idempotency, provenance, assertion, and expected-version metadata.
- State documents consume more storage until measured need justifies delta storage.
- Schema migration and projection rebuild tooling are required as the contract evolves.
- Agents cannot silently promote inference to fact.

## Security and budget impact

Existing OIDC authorization and parent paths apply. Audit/outbox payloads contain IDs and hashes, not
raw state or secrets. PostgreSQL is reused, so the slice adds no paid service.

## Validation

- API tests cover version chains, replay, idempotency conflicts, and stale writes.
- PostgreSQL tests cover constraints, atomic audit/outbox writes, isolation, and concurrency.
- JSON Schema validates the bootstrap state.
- Alembic upgrade, downgrade, single-head, and model parity checks run in CI.

## Review triggers

Review if state documents exceed practical PostgreSQL limits, graph traversal misses objectives,
retention requires selective deletion, or consumers require entity-level streams.
