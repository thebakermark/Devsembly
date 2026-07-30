# Genesis Registry API v1

**Status:** Current
**Version:** 1.0.0
**Implementation issue:** [#21](https://github.com/thebakermark/Devsembly/issues/21)

This API is the first executable Organizational Genome slice. It provides versioned
create, retrieve, list, and update operations for organizations, initiatives, projects,
and project budgets. The generated OpenAPI document remains the machine-readable
contract.

## Resource hierarchy

Every child operation resolves the complete parent path:

```text
Organization
└── Initiative
    └── Project
        └── Budget
```

A child identifier presented under the wrong organization, initiative, or project
returns `404`. This prevents a caller from using a valid identifier to cross an
organization boundary.

## Operations

The base path is `/api/v1`.

| Resource | Create and list | Retrieve and update |
|---|---|---|
| Organization | `POST/GET /organizations` | `GET/PUT /organizations/{organization_id}` |
| Initiative | `POST/GET /organizations/{organization_id}/initiatives` | `GET/PUT /organizations/{organization_id}/initiatives/{initiative_id}` |
| Project | `POST/GET /organizations/{organization_id}/initiatives/{initiative_id}/projects` | `GET/PUT /organizations/{organization_id}/initiatives/{initiative_id}/projects/{project_id}` |
| Budget | `POST/GET .../projects/{project_id}/budgets` | `GET/PUT .../projects/{project_id}/budgets/{budget_id}` |

Creates return `201`. Reads and updates return `200`. Validation failures return `422`.
Missing or incorrectly scoped resources return `404`. Duplicate resources and stale
updates return `409`.

## Update and concurrency contract

Updates are full `PUT` operations and require `expected_version`. A successful update
increments `version`. If another transaction has already changed the resource, the API
returns:

```json
{
  "code": "stale_version",
  "detail": "budget changed after version 1; reload it and retry",
  "resource": "budget",
  "expected_version": 1
}
```

Clients MUST reload the current representation before retrying. The API does not silently
overwrite concurrent changes.

## Budget contract

- `monthly_limit` MUST be positive and use fixed-precision decimal input.
- `currency` defaults to `USD` and is normalized to an uppercase three-letter code.
- `enforcement_mode` is `observe`, `warn`, or `block`; the default is `warn`.
- Genesis v0.1 permits one budget per project.
- `$50/month` is the reference operating posture, not an automatic limit on every
  project.

## Transaction and event contract

Application services depend on repository and Unit of Work protocols. SQLAlchemy
adapters map ORM records to explicit domain data objects. Each successful write and its
outbox event commit in one PostgreSQL transaction. Leaving a Unit of Work without an
explicit commit rolls both back.

Create and update operations emit `genesis.<resource>.created` or
`genesis.<resource>.updated`. The outbox writer is current; delivery and consumer
idempotency remain a later capability.

## Current security boundary

Parent-path validation and repository scoping enforce object isolation. Authentication,
organization membership, role evaluation, and delegated authority are not yet
implemented. Until the OIDC and authorization slice lands, this API MUST NOT be exposed
as a production multi-tenant service.
