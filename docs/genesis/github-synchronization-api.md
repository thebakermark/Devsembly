# GitHub Synchronization API

`POST /api/v1/internal/projects/{project_id}/github/events` accepts GitHub webhook deliveries.
The caller must provide `X-GitHub-Delivery`, `X-GitHub-Event`, and
`X-Hub-Signature-256`. Genesis verifies the SHA-256 HMAC against
`DEVSEMBLY_GITHUB_WEBHOOK_SECRET` before parsing or persisting provider content.

## Contract and authority

- Provider identities are `github:{repository_id}:{entity_kind}:{node_id-or-id}`. Display names,
  repository renames, issue numbers, and URLs are aliases, not identities.
- `(repository_id, delivery_id)` is the delivery idempotency boundary. Exact redelivery returns the
  recorded result and never emits another audit or outbox event.
- Entity ordering uses the provider's entity timestamp. Older events are retained as observations,
  marked out of order, and schedule snapshot reconciliation instead of overwriting current state.
- `approved > verified > inferred`. Lower-authority input cannot overwrite a higher-authority fact.
  Different payloads at the same provider position create an open reconciliation conflict.
- Each entity records `observed_at` and `stale_after`. The initial freshness objective is 30 minutes;
  a scheduled snapshot reconciler will refresh or flag expired sources.

Successful processing atomically updates the source cursor and conflict queue and writes an audit
record plus `genesis.project-intelligence.github-event-ingested` to the transactional outbox. A
delivery is committed as `received` before projection work begins, so a crash can resume it without
relying on GitHub redelivery. Failed or received deliveries are retryable; uniqueness constraints
prevent duplicate state and events under concurrent at-least-once delivery.

This slice normalizes Issues, pull requests, reviews, workflow runs/jobs, milestones, checks, refs,
and commits.

`POST /api/v1/internal/projects/{project_id}/github/snapshot-reconciliations` accepts an
authenticated provider snapshot page of up to 500 entities. Each entity receives a deterministic
synthetic delivery ID derived from its canonical provider payload, so retrying a page after a
timeout is safe. Entities commit independently: a later retry resumes after partial failure without
duplicating successful audit or outbox records. The service applies the same ordering, authority,
and conflict rules as webhook ingestion, then flags sources whose freshness deadline has expired.
Stale detection never changes canonical facts; it emits
`genesis.project-intelligence.github-sources-stale` once when repair first becomes required.

The Temporal worker registers `GitHubSnapshotWorkflow` and its page-reconciliation Activity. The
Activity reads `DEVSEMBLY_GITHUB_TOKEN` only during execution, sends it to the configured GitHub API
origin, follows only same-origin `rel="next"` links, and never records the credential in workflow
history or persistence. Each page is reconciled independently, so Temporal retries safely replay a
partially completed snapshot through deterministic delivery identities.

The workflow covers issues, pull requests, milestones, branches, commits, and Actions runs. After a
complete pass it waits for the configured interval and continues as new, bounding workflow history.
Schedulers use `genesis-github-snapshot-{project_id}-{repository_id}` as the workflow ID so two
schedulers cannot create competing reconciliation loops.

## Governed conflict queue

Authorized project members read the queue at
`GET /api/v1/organizations/{organization_id}/initiatives/{initiative_id}/projects/{project_id}/project-intelligence/github-conflicts`.
The `conflict_status` query parameter selects `open` (the default) or `resolved` records. Parent
organization and initiative IDs are validated with the project, preventing cross-tenant UUID reads.

Approvers resolve an item through `POST .../github-conflicts/{conflict_id}/resolve` with a required
reason and either `keep_current` or `accept_incoming`. The normal authorization layer maps this
endpoint to the `approve` permission; operators and viewers cannot decide conflicts unless an
active, project-scoped approval delegation permits it. The actor is derived from the verified OIDC
principal and is never accepted from the request body.

Resolution locks both the conflict and canonical source. It refuses stale decisions if canonical
state changed after the conflict was recorded. Accepting incoming state requires the original
retained delivery as evidence. Either decision promotes the selected fact to `approved`, records
the reason and principal, and atomically emits an audit record plus
`genesis.project-intelligence.github-conflict-resolved` through the transactional outbox. Exact
replay by the same principal is idempotent; a different second decision is rejected. The source's
repair flag clears only after its last open conflict is resolved and it remains fresh.
