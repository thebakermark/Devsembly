# Genesis Workflow Run API v1

**Status:** Current
**Version:** 1.0.0
**Implementation issue:** [#22](https://github.com/thebakermark/Devsembly/issues/22)

This API persists provider-neutral workflow intent and lifecycle state before a workflow
provider can execute work. It extends the
[Genesis Registry API](api-reference.md) and uses the same repository, Unit of Work,
organization-isolation, optimistic-concurrency, and transactional-outbox boundaries.

Temporal dispatch consumes only the durable published-event feed. The former direct
`POST /runs` start route remains removed so uncommitted workflow intent cannot bypass
governance. The dispatcher correlates committed `accepted` runs to Temporal without
making Temporal the business-state authority.

## Resource hierarchy

Workflow runs belong to the complete registry path:

```text
Organization
└── Initiative
    └── Project
        └── Workflow run
            └── Ordered step
                └── Completed attempt
```

Every operation resolves the organization, initiative, and project before reading or
changing a workflow run. A valid identifier presented under a different parent path
returns `404`.

## Operations

The project run base path is:

```text
/api/v1/organizations/{organization_id}/initiatives/{initiative_id}/projects/{project_id}/workflow-runs
```

| Operation | Method and suffix | Result |
|---|---|---|
| Create or replay | `POST` base path | `201` for a new run; `200` for an exact idempotent replay |
| List project runs | `GET` base path | Ordered project run summaries |
| Inspect run | `GET /{workflow_run_id}` | Run, ordered steps, and attempts |
| Advance status | `PUT /{workflow_run_id}/status` | Versioned legal transition |
| Request cancellation | `POST /{workflow_run_id}/cancel` | `cancellation_requested` state |
| Create or replay retry | `POST /{workflow_run_id}/retry` | New run linked through `retry_of_run_id` |

Workers record completed step attempts through the internal control-plane path:

```text
POST /api/v1/internal/organizations/{organization_id}/initiatives/{initiative_id}/projects/{project_id}/workflow-runs/{workflow_run_id}/steps/{workflow_step_id}/attempts
```

The internal path is an application boundary, not an authorization claim. It MUST remain
private until service identity and authorization are implemented.

## Create and idempotency contract

A create request supplies:

- `workflow_kind`, a provider-neutral workflow definition name;
- `idempotency_key`, unique within the project;
- structured `input_payload`;
- one to 100 ordered steps with unique keys.

The database guarantees uniqueness of `(project_id, idempotency_key)`. Repeating the
same request returns the original run and does not write another outbox event. Reusing
the key with different workflow type, input, steps, or retry source returns `409` with
code `idempotency_conflict`.

New runs begin in `accepted`. Their provider correlation is `null`, proving that business
intent exists before Temporal or another provider receives work. After the creation
event reaches `published_events`, the dispatcher reserves the stable provider correlation
`genesis-run-<workflow_run_id>` and moves the run to `queued`.

## Run lifecycle

| Current state | Allowed next state |
|---|---|
| `accepted` | `queued`, `cancellation_requested` |
| `queued` | `running`, `failed`, `cancellation_requested` |
| `running` | `succeeded`, `failed`, `cancellation_requested` |
| `cancellation_requested` | `cancelled`, `failed` |
| `succeeded` | None |
| `failed` | None; create a retry run |
| `cancelled` | None; create a retry run |

Advancing to `queued` requires a nonblank `temporal_workflow_id`. Once recorded, that
provider correlation is immutable. Terminal transitions record `completed_at`, while
the first transition to `running` records `started_at`.

`cancellation_requested` is available only through the cancellation operation. A run
cannot become `succeeded` until every step is `succeeded` or `skipped`.

Illegal transitions return `409` with code `invalid_transition`.

## Concurrency and retry contract

Run status changes and cancellation requests require `expected_version`. Step attempts
require `expected_step_version`. A successful change increments the matching version.
A stale writer receives `409` with code `stale_version` and MUST reload before retrying.

Only `failed` or `cancelled` runs can be retried. A retry:

- has a new project-scoped idempotency key;
- starts in `accepted`;
- links to the source through `retry_of_run_id`;
- copies the provider-neutral workflow type, input, estimated cost, and ordered steps;
- does not copy provider IDs, timestamps, step state, or attempts.

Repeating the exact retry request returns the same retry run without duplicate events.

## Step attempt contract

An attempt is an immutable completed result. Its number is assigned in order within the
step. A failed step can receive a later attempt; succeeded, cancelled, or skipped steps
cannot.

- `succeeded` requires `result_payload` and forbids `error_payload`.
- `failed` requires `error_payload`.
- `cancelled` may include normalized result or error metadata.
- `completed_at` cannot precede `started_at`.

Recording an attempt, updating the step status and version, and writing the outbox event
occur in one transaction.

## Transaction and event contract

Successful operations emit:

- `genesis.workflow_run.created`;
- `genesis.workflow_run.status_changed`;
- `genesis.workflow_run.cancellation_requested`;
- `genesis.workflow_run.retry_created`;
- `genesis.workflow_step.attempt_recorded`.

Domain records, correlated audit records, and their events commit together. The outbox
publisher delivers committed events idempotently to the durable PostgreSQL event feed.

## Temporal dispatch and recovery

The dispatcher materializes leased `workflow_dispatches` records only from published
`genesis.workflow_run.created` and `genesis.workflow_run.retry_created` events. It never
scans uncommitted or unpublished run rows as an alternate start path.

Before the network call, the dispatcher atomically reserves the deterministic Temporal
workflow ID and changes the run from `accepted` to `queued`. A process restart at that
point leaves a recoverable pending dispatch. If the process stops after Temporal accepts
the start but before PostgreSQL acknowledges it, a replacement retries the same workflow
ID. Temporal rejects the duplicate start, which the dispatcher treats as confirmation
of the original start before marking the dispatch complete.

Claims expire for safe takeover, failures use bounded exponential backoff, and terminal
runs that were never dispatched are marked skipped. The dispatcher publishes a persisted
heartbeat used by container and API readiness checks.

## Current boundary

These endpoints do not start Temporal directly or automatically evaluate budgets. They
write audit and outbox records atomically, publish committed events through the outbox
worker, dispatch those events through the recovery-safe Temporal boundary, and enforce
organization authorization. Explicit evaluation and decision operations are available through the
[Cost Governance API](cost-governance-api.md); automatic workflow admission based on
those records remains a later integration slice.
