# ADR 0001: GitHub is the authoritative source of truth

## Status

Superseded by [ADR 0012 — GitHub Is a Provider](../architecture/decisions/0012-github-is-a-provider.md).

## Decision

Requirements, source code, architecture decisions, reviews, test results, releases and change history will be anchored in GitHub. Agent memory and chat history may assist work but cannot replace versioned records.

## Consequences

Every material change must link to an issue and pull request. Automated agents require repository-scoped identities and cannot bypass protected-branch controls.
