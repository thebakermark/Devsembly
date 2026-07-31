# Memory and Context API v1

The Memory and Context API exposes a governed, project-scoped working-context view to agents while
keeping canonical project truth separate from generated context. Migration `0015_memory_context`
adds durable typed memory proposals and reproducible context-package manifests.

## Authority model

| Information | Authority |
|---|---|
| Source code, commits, pull requests, reviews, and CI evidence | GitHub |
| Effective project operating state | PIE PostgreSQL revision log |
| Portable repository snapshot | Generated `.devsembly/project-state.json` |
| Durable workflow recovery | Temporal history |
| Immutable artifacts and proof | Evidence storage |
| Agent working context | Rebuildable, non-authoritative context package |

Memory proposals never write to the PIE revision log. Approval permits retrieval but does not make
the proposal equal to canonical project state. A later reconciliation must explicitly promote any
approved fact into canonical state.

## Typed memory

`POST .../memory/proposals` creates a `working`, `episodic`, `semantic`, `procedural`, or
`reflection` record in `proposed` state. Records retain content checksum, source revision or URI,
assertion status, confidence, sensitivity, retention deadline, proposer, and version.

`POST .../memory/proposals/{id}/approve` and `/reject` require approval authority, expected-version
concurrency, a human principal, and a reason. `GET .../memory/records` returns the project-scoped
record history. Proposal and resolution transactions emit additive outbox events.

## Context Builder

`POST .../memory/context` accepts a task and token budget. Authorization occurs before the service
loads project state or memory. The builder:

1. Reads the latest canonical PIE revision.
2. Adds approved memory candidates.
3. Excludes proposed, rejected, disputed, expired, invalidated, superseded, confidential, and
   restricted records before ranking.
4. Contains common instruction-override and credential-exfiltration text as untrusted data by
   omitting the candidate and reporting `prompt_injection_risk`.
5. Ranks deterministically by canonical authority, approved-memory authority, task-term overlap,
   and stable identifier.
6. Applies a deterministic byte-based token estimate and reports every budget omission.
7. Persists the selected items, omissions, provenance, authority, assertion status, confidence,
   freshness, sensitivity, selection reason, token usage, and SHA-256 manifest.

`GET .../memory/context/{package_id}` reconstructs the stored package after process restart. A new
canonical PIE revision invalidates packages built from older revisions during the next build.
Rebuilding the same task and budget from unchanged inputs produces the same manifest checksum.

The first slice intentionally uses structured PostgreSQL state and deterministic lexical relevance.
It adds no vector database. Embeddings remain optional until retrieval evaluations demonstrate a
material precision or recall improvement.

## Events

- `genesis.memory.proposed`
- `genesis.memory.approved`
- `genesis.memory.rejected`
- `genesis.context.built`

Authorization decisions continue through the existing identity audit boundary. Memory and context
events share the existing transactional outbox commit boundary.
