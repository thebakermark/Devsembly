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
| [0005](0005-provider-independence.md) | Provider independence | Accepted |
| [0006](0006-kernel-first.md) | Kernel-first platform boundary | Accepted |
| [0007](0007-organizations-before-applications.md) | Organizations before applications | Accepted |
| [0008](0008-memory-as-platform-service.md) | Memory as a platform service | Accepted |
| [0009](0009-organizational-genome-canonical.md) | Organizational Genome is canonical | Accepted |
| [0010](0010-executive-core-governs-workflow.md) | Executive Core governs workflow | Accepted |
| [0011](0011-capability-based-architecture.md) | Capability-based architecture | Accepted |
| [0012](0012-github-is-a-provider.md) | GitHub is a provider | Accepted |
| [0013](0013-human-authority-final.md) | Human authority is final | Accepted |
| [0014](0014-project-intelligence-canonical-revisions.md) | Project Intelligence uses canonical immutable revisions | Accepted |

ADRs are immutable after acceptance except for status and links to superseding decisions. Material changes require a new ADR.

The issue #20 logical ADR sequence 0001–0009 maps to canonical ADRs 0005–0013
because accepted records already occupied 0001–0004. See the
[Genesis ADR map](../../genesis/adr/README.md).
