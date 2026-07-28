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
