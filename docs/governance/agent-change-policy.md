# Agent Change Policy

## Core rules

1. No agent may push directly to `main`.
2. No agent may approve its own work.
3. Every change must be associated with an issue or documented task.
4. Every code change must include appropriate validation.
5. Agent-created pull requests begin as drafts.
6. Production deployments require explicit human approval.
7. Agents may not disable security controls or required checks.
8. Agents may not receive production credentials.
9. Destructive commands require human approval.
10. All agent actions must be auditable.

## Required separation of duties

The implementation agent and final-review agent must be different sessions or models.

## High-risk changes

The following always require human review:

- authentication or authorization
- database migrations
- billing or accounting
- secret handling
- production infrastructure
- dependency major-version upgrades
- deletion or irreversible data operations
