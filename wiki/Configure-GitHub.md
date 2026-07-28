# Configure GitHub

## Repository baseline

Each product repository should include:

- README, SECURITY, CONTRIBUTING, and CODEOWNERS
- issue templates
- pull-request template
- GitHub Actions validation
- branch protection
- release and rollback documentation

## Branch policy

Protect `main` and require:

- pull requests
- successful required checks
- conversation resolution
- at least one independent review for high-risk changes
- no force pushes
- no branch deletion

## Agent permissions

Agents may create issues, branches, commits, and draft pull requests. They may not bypass branch protection, change repository security settings, or merge high-risk changes without human approval.

## Standard branch names

```text
feature/COS-123-short-description
fix/COS-456-short-description
docs/COS-789-short-description
security/COS-321-short-description
```
