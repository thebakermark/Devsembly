# ADR 0008 — Memory as a Platform Service

- **Status:** Accepted
- **Date:** 2026-07-30
- **Decision owners:** Devsembly Architecture
- **Applies to:** Knowledge and memory architecture

## Context

Agents and workflows need durable context, decisions, evidence, summaries, lessons, and
retrieval. Chat histories, model context windows, vector stores, or one database cannot
alone provide authority, provenance, access control, retention, correction, and recovery.

## Decision

Treat memory as a governed platform capability, called MemoryOS in the future-state
architecture. It exposes contracts for recording, retrieving, relating, summarizing,
retaining, correcting, and deleting knowledge under identity and policy.

Storage systems are providers. Genesis begins with relational metadata, versioned
documents, object evidence, and provider search as appropriate. A graph or vector
database is optional and deferred until evidence demonstrates need.

## Consequences

Memory becomes shareable, attributable, and policy-controlled across agents and
applications. Provenance, retention, indexing, and correction add complexity. Retrieval
quality must not be confused with source authority.

## Alternatives considered

- **Agent-local memory:** rejected as non-authoritative and inaccessible to governance.
- **Vector database as memory:** rejected because similarity search does not supply
  authority or lifecycle.
- **Full knowledge graph immediately:** deferred as unnecessary for Genesis.

## Security impact

Memory records require classification, organization scope, least-privilege retrieval,
redaction, retention, deletion, poisoning resistance, and audit. Summaries must not leak
restricted source content.

## Budget impact

Genesis reuses PostgreSQL, object storage, and repository documents. Dedicated search,
vector, or graph services require measured value and explicit budget approval.

## Implementation constraints

- Every durable knowledge object records source, owner, version, time, confidence, and
  access policy.
- Generated summaries link to sources and can be invalidated.
- Retrieval treats external and generated content as untrusted input.
- Agent context remains a cache reconstructed from canonical sources.

## Validation criteria

A decision can be stored with provenance, retrieved only in authorized scope, corrected
without erasing history, linked to evidence, and reconstructed after process restart.

## Review triggers

Review when scale, semantic retrieval quality, graph traversal, legal deletion, or
regulated retention requires a new provider or data model.

## References

- [Memory services](../../genesis/kernel/memory-services.md)
- [Book 0 — Philosophy](../../genesis/book-0-philosophy.md)
- [ADR 0004](0004-postgresql-persistence-contracts.md)
