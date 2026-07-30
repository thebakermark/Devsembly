# Architecture Decision Records

Architecture Decision Records (ADRs) document significant, durable technical decisions for Devsembly.

## Status values

- **Proposed** — under active review and not yet binding.
- **Accepted** — approved for implementation.
- **Superseded** — replaced by a later ADR.
- **Deprecated** — retained for history but no longer recommended.

## Required sections

Each ADR records status, date, context, decision, alternatives, consequences, budget impact, security impact, implementation constraints, validation, and review triggers.

## Genesis decisions

| ADR | Decision | Status |
|---|---|---|
| [0001](0001-python-fastapi-modular-monolith.md) | Python and FastAPI modular monolith | Accepted |
| [0002](0002-temporal-durable-workflow-engine.md) | Temporal durable workflow engine | Accepted |
| [0003](0003-oidc-external-identity.md) | OIDC-based external identity | Accepted |
| [0004](0004-postgresql-persistence-contracts.md) | PostgreSQL persistence contracts | Accepted |

ADRs are immutable after acceptance except for status and links to superseding decisions. Material changes require a new ADR.