# Configure Coolify

Coolify manages deployment after code reaches GitHub.

## Environments

Create separate environments for:

- preview pull requests
- development integration
- staging
- production

## Minimum configuration

1. Install Coolify on its management server.
2. Add the staging server through SSH.
3. Connect the GitHub repository.
4. Configure build settings or Docker Compose.
5. add environment variables through the dashboard.
6. Configure domains and HTTPS.
7. Configure health checks.
8. Configure deployment notifications.
9. Configure off-server database backups.

## Deployment rules

- Pull requests may deploy automatically to preview.
- Merges to `main` may deploy automatically to staging.
- Production requires explicit approval.
- Every production release must have rollback instructions.
