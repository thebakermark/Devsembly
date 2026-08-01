# Trust Model

## Required controls

- Least-privilege credentials per agent and environment
- No production credentials on development machines
- Protected default branches
- Pull-request-only changes
- Independent status checks
- Immutable audit events for orchestration decisions
- Secret scanning before commit and in CI
- Network isolation between development and production
- Human approval for production, destructive, financial and security-policy actions
- Reviewed third-party agent skills and plugins
- Bounded retries with escalation

## Untrusted execution boundary

Agent-produced code and repository validation commands are untrusted input. They must not inherit
worker credentials. The current worker therefore gives validation a minimal explicit environment,
uses argument-vector execution without shell interpretation, enforces normalized repository path
boundaries, and terminates timed-out or cancelled validation process groups. Non-idempotent delivery
execution is not automatically retried.

A temporary checkout is filesystem organization, not a security sandbox. Before a credentialed live
delivery proof, coding and validation must run as a non-root identity inside an ephemeral container or
microVM with restricted egress, resource limits, a bounded writable filesystem, and no worker control
plane credentials. Until that boundary is implemented, use only disposable repositories and test
credentials and treat the external-provider milestone as blocked.

## Credential classes

| Class | Intended access |
|---|---|
| Development agent | Development repositories, branches and disposable services |
| Review agent | Read-only code and diff access; review comments |
| CI identity | Build/test resources and artifact publishing |
| Deployment agent | Preview and staging deployment triggers |
| Release approver | Explicit production promotion only |

## Prohibited defaults

Agents must not receive organization-owner access, billing access, production root SSH, permission to disable checks, permission to force-push protected branches, or unrestricted access to customer data.
