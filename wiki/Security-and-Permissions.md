# Security and permissions

## Non-negotiable controls

- Least-privilege service accounts
- Separate development, staging, and production secrets
- Protected main branches
- Independent review and CI
- Secret scanning before commit and in CI
- No agent self-approval
- No production data in development
- Logged agent actions
- Reviewed third-party skills and plugins

## High-risk actions requiring human approval

- Production deployment
- Destructive database migration
- Permission or authentication changes
- Secret rotation
- Repository security-setting changes
- Infrastructure deletion
- Disabling required tests or security checks
