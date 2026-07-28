# ADR 0001: GitHub is the authoritative source of truth

## Status

Accepted

## Decision

Requirements, source code, architecture decisions, reviews, test results, releases and change history will be anchored in GitHub. Agent memory and chat history may assist work but cannot replace versioned records.

## Consequences

Every material change must link to an issue and pull request. Automated agents require repository-scoped identities and cannot bypass protected-branch controls.
