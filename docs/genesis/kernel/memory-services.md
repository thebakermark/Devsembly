# Memory Services

**Status:** Proposed platform contract
**Version:** 0.1.0

## Memory classes

| Class | Example | Authority |
|---|---|---|
| Working | Task context and intermediate notes | Non-authoritative, short-lived |
| Episodic | Workflow and interaction history | Evidence subject to retention |
| Semantic | Policies, definitions, decisions, and validated knowledge | Versioned canonical source |
| Procedural | Approved workflows, runbooks, and skills | Executable only under authority |
| Evidence | Test result, artifact, log, approval, or checksum | Immutable reference where required |

## Knowledge object

Every durable object records stable ID, type, organization, owner, source and provenance,
content or object reference, checksum, schema and semantic version, confidence, status,
classification, access policy, created and effective times, retention, superseding links,
and relationships.

## Required operations

Record, get by ID, query by structured filters, retrieve ranked candidates, relate,
summarize with citations, correct through successor, invalidate derived content, apply
retention, and request authorized deletion.

## Retrieval

Access policy filters before content reaches ranking or generation. Results preserve
source, authority, freshness, and confidence separately from relevance. Generated
summaries cite their source objects and are invalidated when controlling sources change.

## Storage posture

Genesis may use PostgreSQL for metadata, versioned repository documents for canonical
text, and object storage for large evidence. Search, vector, and graph implementations
are replaceable providers and are not required for Genesis.

## Safety and validation

Memory input is untrusted and scanned for secrets, malware where applicable, prompt
injection, classification, and provenance. Tests cover organization isolation,
provenance, correction, retention, denied retrieval, stale summary invalidation, checksum
failure, and reconstruction after restart.
