# Release workflow

## Readiness checks

- Required CI checks passed
- Acceptance criteria verified
- Security findings resolved or formally accepted
- Documentation updated
- Database migration reviewed
- Backup confirmed
- Rollback procedure documented

## Deployment

1. Create release notes and a version tag.
2. Deploy to staging.
3. Run smoke and end-to-end tests.
4. Request human production approval.
5. Deploy through Coolify.
6. Verify health, errors, queues, database connectivity, and critical workflows.
7. Monitor the release and create an incident automatically if thresholds are exceeded.
