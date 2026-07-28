# Configure Archon workflows

Archon defines the repeatable process agents must follow.

## Initial workflows

- Feature development
- Bug fix
- CI repair
- Documentation synchronization
- Security remediation
- Release

## Required workflow stages

1. Read the issue and authoritative documentation.
2. Create an isolated worktree.
3. Produce or verify the implementation plan.
4. Implement the smallest valid change.
5. Add or update tests.
6. Run local validation.
7. Run independent agent review.
8. Update documentation.
9. Open a draft pull request.
10. Allow GitHub Actions to validate independently.
11. Deploy a preview environment when applicable.
12. Request human approval at defined gates.

Workflow definitions live under `workflows/` in this repository.
