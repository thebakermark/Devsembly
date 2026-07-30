# Genesis Traceability Matrix

**Status:** Active
**Version:** 0.1.0

This matrix connects issue #20 requirements to governing artifacts and intended
validation. Status describes documentation completion, not runtime implementation.

| Requirement | Governing artifact | Supporting specification | Evidence |
|---|---|---|---|
| Philosophy and North Star | [Book 0](book-0-philosophy.md) | Constitution | Markdown validation |
| Human final authority | [Book I](book-1-constitution.md) | [ADR 0013](../architecture/decisions/0013-human-authority-final.md) | Governance review |
| Provider independence | [Book I](book-1-constitution.md) | [ADR 0005](../architecture/decisions/0005-provider-independence.md), [Provider SDK](provider-sdk/README.md) | Contract/schema checks |
| Kernel-first boundary | [Book II](book-2-architecture.md) | [ADR 0006](../architecture/decisions/0006-kernel-first.md), [Kernel](kernel/README.md) | Architecture review |
| Organizations before applications | [Book II](book-2-architecture.md) | [ADR 0007](../architecture/decisions/0007-organizations-before-applications.md) | Model review |
| Memory as a platform service | [Book II](book-2-architecture.md) | [ADR 0008](../architecture/decisions/0008-memory-as-platform-service.md), [Memory services](kernel/memory-services.md) | Contract review |
| Organizational Genome canonical | [Book VI](book-6-organizational-genome.md) | [ADR 0009](../architecture/decisions/0009-organizational-genome-canonical.md) | Schema/provenance checks |
| Executive Core governance | [Book II](book-2-architecture.md) | [ADR 0010](../architecture/decisions/0010-executive-core-governs-workflow.md) | Workflow policy tests, planned |
| Capability architecture | [Book II](book-2-architecture.md) | [ADR 0011](../architecture/decisions/0011-capability-based-architecture.md), [Catalog](capability-catalog.md) | Provider conformance, planned |
| GitHub is a provider | [Book II](book-2-architecture.md) | [ADR 0012](../architecture/decisions/0012-github-is-a-provider.md) | Adapter tests, planned |
| Engineering standards | [Book III](book-3-engineering-standards.md) | Existing Genesis ADRs 0001–0004 | Ruff, MyPy, Pytest, migrations |
| Operational controls | [Book IV](book-4-operations-manual.md) | Existing operations and provider guides | Compose and Docker checks |
| Agent limits and evidence | [Book V](book-5-agent-handbook.md) | Trust model and workflows | Independent review |
| Organizational canonical models | [Book VI](book-6-organizational-genome.md) | Existing Organizational Genome schemas | JSON Schema checks |
| Provider contracts | [Provider SDK](provider-sdk/README.md) | Contract specifications and examples | Schema and conformance checks |
| Current versus future scope | [Book II](book-2-architecture.md) | [Genesis plan](../implementation/genesis-reference-implementation-plan.md) | Architecture review |
| `$50/month` constraint | [Book I](book-1-constitution.md) | Genesis plan and operations manual | Budget acceptance test, planned |
| Organization registry runtime | [Book VI](book-6-organizational-genome.md) | [Registry API v1](api-reference.md) | API and PostgreSQL integration tests |
| Repository and Unit of Work runtime | [Book III](book-3-engineering-standards.md) | [ADR 0004](../architecture/decisions/0004-postgresql-persistence-contracts.md) | Transaction, rollback, and concurrency tests |
| Initiative and project isolation | [ADR 0007](../architecture/decisions/0007-organizations-before-applications.md) | [Registry API v1](api-reference.md) | Parent-path isolation tests |
| Monthly budget profile | Genesis plan | [Registry API v1](api-reference.md) | Decimal, uniqueness, mode, and migration constraints |
| Transactional event writes | [ADR 0004](../architecture/decisions/0004-postgresql-persistence-contracts.md) | [Event bus](kernel/event-bus.md) | Atomic outbox integration test |
| Workflow intent before execution | [Workflow engine](kernel/workflow-engine.md) | [Workflow Run API v1](workflow-run-api.md) | Create/replay API and PostgreSQL tests |
| Workflow lifecycle and concurrency | [Book III](book-3-engineering-standards.md) | [Workflow Run API v1](workflow-run-api.md) | Transition, stale-version, cancellation, and terminal-state tests |
| Workflow retry lineage | [Workflow engine](kernel/workflow-engine.md) | [Workflow Run API v1](workflow-run-api.md) | Retry isolation and idempotency tests |
| Workflow step evidence | [Book V](book-5-agent-handbook.md) | [Workflow Run API v1](workflow-run-api.md) | Attempt ordering, payload, transaction, and outbox tests |

## Maintenance

Every normative Genesis change MUST update this matrix when it adds, removes, or moves a
requirement. Runtime rows remain planned until executable evidence exists.
