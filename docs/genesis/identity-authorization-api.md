# Identity and Authorization API

**Status:** Current Genesis v0.1 contract

**Version:** 1.0

## Boundary

Human API requests use short-lived OIDC bearer tokens. The configured issuer's discovery
document supplies the JWKS URI; verification requires a valid signature, issuer, audience,
issued-at time, expiry, and subject. Devsembly stores no passwords or bearer tokens.

Issuer plus subject maps to one stable internal principal. Authentication proves identity
but grants no tenant permission. Active organization membership, role permissions, and
active bounded delegations are evaluated inside Devsembly and deny by default.

## Roles

| Role | Read | Write | Approve | Manage membership |
| --- | --- | --- | --- | --- |
| Owner | Yes | Yes | Yes | Yes |
| Administrator | Yes | Yes | Yes | Yes |
| Operator | Yes | Yes | No | No |
| Approver | Yes | No | Yes | No |
| Viewer | Yes | No | No | No |

Suspended or revoked membership grants nothing. A delegation cannot restore access to an
inactive member. Delegations name one permission, may be project-scoped, have explicit
start and expiry times, and can be revoked immediately.

## Endpoints

- `GET /api/v1/me` returns the authenticated internal principal.
- `POST /api/v1/organizations` bootstraps the creator as the first owner.
- `GET /api/v1/organizations` returns only active memberships.
- `GET|POST /api/v1/organizations/{organization_id}/memberships` lists or creates
  memberships for authorized administrators.
- `PUT /api/v1/organizations/{organization_id}/memberships/{membership_id}` changes role
  or status while preserving at least one active owner.
- `POST /api/v1/organizations/{organization_id}/delegations` creates bounded authority.
- `POST /api/v1/organizations/{organization_id}/delegations/{delegation_id}/revoke`
  revokes it.

All existing organization, initiative, project, budget, workflow, cost, and decision
routes use the same dependency. Cross-tenant denial returns the same `404` shape as an
unknown resource. Decision resolution requires `approve`; `decided_by` is derived from the
authenticated internal principal rather than caller input.

The internal step-attempt endpoint uses `DEVSEMBLY_INTERNAL_CONTROL_TOKEN`, not a human
OIDC token. This is an interim machine boundary; workload identity and rotation automation
remain later work.

## Configuration

- `DEVSEMBLY_OIDC_ISSUER`: exact discovery issuer.
- `DEVSEMBLY_OIDC_AUDIENCE`: API audience.
- `DEVSEMBLY_INTERNAL_CONTROL_TOKEN`: separate internal-control bearer credential.

If identity configuration is absent, protected human APIs fail closed with `503`.
Missing or invalid credentials return stable `401`; authorization denial returns `404`.
Authentication and authorization audits contain principal IDs, issuer, permission, and
outcome, never tokens or provider secrets.

## Deferred

Interactive browser authorization-code flow with PKCE, provider-specific login UI,
refresh-token storage, account linking, workload identity, SCIM, SAML, customer-managed
identity, and break-glass operations remain separate slices.
