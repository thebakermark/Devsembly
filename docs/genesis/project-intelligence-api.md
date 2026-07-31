# Project Intelligence State API v1

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
