# Genesis Cost Governance API v1

**Status:** Current
**Version:** 1.0.0
**Implementation issue:** [#23](https://github.com/thebakermark/Devsembly/issues/23)

This API evaluates provider-neutral cost options against a project's current monthly
budget, preserves deterministic lower-cost recommendations, and records material
decisions. It extends the [Registry API](api-reference.md) and uses the same repository,
Unit of Work, project-isolation, optimistic-concurrency, and transactional-outbox
boundaries.

The API evaluates caller-declared estimates. Actual provider billing, usage ingestion,
forecast learning, and chargeback are later capabilities.

## Resource hierarchy

```text
Organization
└── Initiative
    └── Project
        ├── Budget
        ├── Workflow run
        ├── Cost evaluation
        └── Decision
```

Every operation resolves the complete organization, initiative, and project path.
Optional workflow-run and cost-evaluation references must belong to that same project.
A valid identifier under the wrong parent path returns `404`.

## Operations

The project base path is:

```text
/api/v1/organizations/{organization_id}/initiatives/{initiative_id}/projects/{project_id}
```

| Resource | Operation | Method and suffix |
|---|---|---|
| Cost evaluation | Create or exact replay | `POST /cost-evaluations` |
| Cost evaluation | List | `GET /cost-evaluations` |
| Cost evaluation | Inspect | `GET /cost-evaluations/{evaluation_id}` |
| Decision | Propose | `POST /decisions` |
| Decision | List | `GET /decisions` |
| Decision | Inspect | `GET /decisions/{decision_id}` |
| Decision | Approve or reject | `POST /decisions/{decision_id}/resolve` |

A new evaluation returns `201`; an exact idempotent replay returns `200`. Other
successful creates return `201`, and reads or transitions return `200`.

## Cost option contract

An evaluation supplies one selected option and up to 20 alternatives. Each option has:

- a project-request-local unique key and name;
- an explicit statement that it satisfies the acceptance criteria;
- one to 100 line items;
- a `one_time` or `monthly` cadence for each line item;
- a positive decimal quantity and nonnegative decimal unit cost.

The service derives all totals using decimal arithmetic rounded to four places. Caller
totals are neither accepted nor trusted. An option that exceeds the supported
`Numeric(14,4)` range returns `422`.

Every evaluation snapshots the budget identifier, version, currency, monthly limit, and
enforcement mode. Later budget changes do not rewrite historical evaluation results.

## Budget outcomes

The selected option's monthly total is compared with the active project budget:

| Condition | Mode | Outcome | Selection behavior |
|---|---|---|---|
| Monthly total is within the limit | Any | `within_budget` | May be approved |
| Monthly total exceeds the limit | `observe` | `observed_overage` | May be approved with the overage recorded |
| Monthly total exceeds the limit | `warn` | `approval_required` | Requires an explicit decision resolution |
| Monthly total exceeds the limit | `block` | `blocked` | Cannot be approved while the hard limit remains exceeded |

The database verifies the recorded overage, outcome, budget limit, and enforcement mode
are mathematically consistent.

Approval uses the current project budget as well as the historical evaluation. A budget
that becomes stricter after evaluation cannot be bypassed. A historically blocked
evaluation can be approved only after the same budget is revised to a newer version
whose currency matches and whose limit covers the selected monthly cost. The approval
record snapshots the authorizing budget version and limit.

## Recommendation contract

The `genesis-cost-v1` algorithm considers only supplied alternatives that:

1. satisfy the acceptance criteria;
2. cost less per month than the selected option; and
3. fit the snapshotted monthly budget.

It selects the lowest monthly cost, then the lowest one-time cost, then the
lexicographically lowest option key. The result preserves the option key, monthly and
one-time savings, budget fit, human-readable rationale, and algorithm version.

No recommendation is fabricated when the request supplies no qualifying alternative.
A recommendation is advisory: the caller must submit a new evaluation with that option
selected before it can become the subject of an approved decision.

## Idempotency contract

`idempotency_key` is unique within a project. The request fingerprint covers workflow
correlation, the selected option, alternatives, line items, cadences, quantities, costs,
and acceptance declarations. Repeating the same request returns the original immutable
evaluation without another outbox event. Reusing the key for different intent returns
`409` with code `idempotency_conflict`.

## Decision contract

New decisions begin in `proposed`. A proposal preserves:

- context, selected option, and alternatives;
- currency plus one-time and monthly cost impact;
- risk, confidence, and proposal rationale;
- optional cost-evaluation provenance.

When linked to an evaluation, the option, alternatives, currency, and costs are derived
from the immutable evaluation rather than accepted from the caller. A direct decision
must supply those values explicitly.

Resolution requires `expected_version`, `approved` or `rejected`, a declared decision
maker, decision note, and outcome. A successful resolution increments the version and
records the timestamp. Approved and rejected records are final; attempts to rewrite
them return `409` with code `invalid_transition`. Stale writers receive `409` with code
`stale_version`.

An evaluated option that does not satisfy the acceptance criteria cannot be approved.
Current hard-budget rules also apply to direct decisions so omitting an evaluation does
not bypass a `block` policy.

## Transaction and event contract

Successful writes emit:

- `genesis.cost_evaluation.created`;
- `genesis.decision.proposed`;
- `genesis.decision.approved`;
- `genesis.decision.rejected`.

The domain record and matching outbox event commit or roll back together. Publication
remains the responsibility of a later idempotent outbox worker.

## Current authority and security boundary

`decided_by` is a declared identifier recorded for provenance; it is not yet an
authenticated identity or authorization proof. The API does not claim that the caller
has budget authority. External OIDC, organization membership, delegation, approval
limits, and audit writers remain required before production multi-tenant exposure.
