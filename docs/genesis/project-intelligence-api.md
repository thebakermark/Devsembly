# Project Intelligence API v1

The first PIE API provides an authorized immutable project-state revision log beneath an existing
organization, initiative, and project.

- `GET .../project-intelligence/state` returns the latest revision.
- `GET .../project-intelligence/revisions` returns ordered history.
- `GET .../project-intelligence/revisions/{version}` reproduces one version.
- `POST .../project-intelligence/revisions` reconciles a source observation.

The request includes `expected_version`, `idempotency_key`, `schema_version`, canonical `state`,
`source`, and `assertion`. Initial creation expects version `0`. Retrying the same key and request is
safe. Reusing the key for different content or writing a stale version returns `409`.

Assertion status is `verified`, `inferred`, or `disputed`. Confidence is zero through one and needs
an explanation. SHA-256 and the parent link make history reproducible. Reconciliation atomically
commits the revision, audit record, and `genesis.project-intelligence.state-reconciled` outbox event.

## Current projections

Every new revision also rebuilds a disposable relational projection in the same transaction. The
projection carries its source revision and exposes:

- `GET .../project-intelligence/projection` for the complete projection checkpoint, work hierarchy,
  and both graphs.
- `GET .../project-intelligence/work-items` for normalized roadmap, milestone, epic, feature, task,
  and current-sprint items.
- `GET .../project-intelligence/graphs/{graph_kind}` where `graph_kind` is `capability` or
  `dependency`.
- `POST .../project-intelligence/projection/rebuild` with a latest revision `version` to recover the
  current projection from immutable history.

Work items retain canonical PIE IDs, optional parent IDs, source revision, item-level provenance,
assertion status, confidence, and provider aliases. An alias is scoped by provider, account,
external kind, and external ID; it never becomes a canonical primary key. Graph nodes retain the
same provenance and assertion contract. Edges use the initial relationship vocabulary:
`parent_of`, `depends_on`, `implements`, `validates`, `evidences`, `blocks`, `supersedes`, and
`derived_from`.

Reconciliation fails with `422` before any write when IDs or aliases are duplicated, a parent or
edge endpoint is missing from the project projection, the work hierarchy violates its type rules,
or a hierarchy or graph is cyclic. Rebuilding a non-latest version returns `409`, preventing an
operator from accidentally publishing a stale current projection. A successful rebuild atomically
emits `genesis.project-intelligence.projection-rebuilt` with source revision and projection counts.

The projection is a read model, not a second source of truth. It may be deleted and rebuilt from the
revision log without changing canonical history.

## Assurance projections

`GET .../project-intelligence/assurance` returns an executive roll-up of evidence-backed validation
claims, stale or superseded claims, open risk exposure, and technical-debt principal and interest.
Supporting records are exposed by `GET .../validation-results`, `GET .../risks`, and
`GET .../technical-debt`.

A conclusive validation status (`passed` or `failed`) MUST include at least one opaque project
evidence identifier. Claims without evidence MUST be `unverified`; stale and superseded metadata
remains visible. Risks retain owner, likelihood, impact, mitigation, trigger, review state,
provenance, confidence, and capability/dependency impacts. Technical debt retains owner, principal,
interest, impact, retirement criteria, provenance, confidence, and the same impact links.

These endpoints inherit the organization, initiative, and project authorization boundary. Impact
identifiers must resolve inside that project projection, and responses expose evidence identifiers
rather than evidence contents. Evidence content remains behind the separately authorized evidence
API. Migration `0014_pie_assurance` adds durable JSONB projection caches; rebuilds derive them from
the selected immutable project-state revision.

The governed agent-facing retrieval surface is documented separately in the
[Memory and Context API](memory-context-api.md). Context packages cite this revision log and never
overwrite it.
