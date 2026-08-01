# Book III — Engineering Standards

**Status:** Binding
**Version:** 0.1.0

The key words **MUST**, **MUST NOT**, **SHOULD**, **SHOULD NOT**, and **MAY** indicate
requirement strength. A deviation from MUST requires an approved exception or higher
authority change.

## Repository structure

- Production Python code MUST live in the package defined by `pyproject.toml`.
- Tests MUST be organized by the behavior and layer they validate.
- Migrations MUST live in the configured Alembic version directory.
- Architecture, security, operations, and provider documentation MUST remain
  version-controlled with the implementation.
- Provider-specific logic MUST remain in adapters or provider guides.
- Generated artifacts SHOULD be excluded unless reproducibility or audit evidence
  requires versioning them.

## Python and API development

- Supported Python and dependency ranges MUST be declared in `pyproject.toml`.
- Public functions and application boundaries MUST be typed.
- FastAPI routes MUST validate input and return explicit response contracts.
- API changes MUST state compatibility and versioning impact.
- Domain errors MUST map to stable, documented API error types without leaking secrets or
  infrastructure details.
- Async code MUST avoid blocking I/O.
- Time MUST be timezone-aware UTC at storage boundaries.
- Money MUST use fixed-precision decimal values and explicit currency.

## Domain boundaries and dependency direction

- Domain policy MUST be independent of FastAPI, SQLAlchemy, Temporal, provider SDKs, and
  deployment products.
- Application services MAY coordinate domain objects, repositories, policy, and provider
  ports.
- Infrastructure adapters MUST implement inward-facing contracts.
- Modules MUST NOT read or mutate another module's persistence internals.
- Cross-module effects SHOULD use application services and domain events.
- Circular dependencies MUST be rejected.

## Repository and Unit of Work patterns

- Application code MUST depend on repository protocols, not concrete ORM queries.
- A repository MUST serve one aggregate or explicit read model.
- Repositories MUST return domain objects or DTOs, not raw ORM entities.
- A Unit of Work MUST define one transaction boundary and expose explicit commit and
  rollback behavior.
- Domain writes and their outbox events MUST commit atomically.
- Transaction ownership MUST remain at the application-service boundary.
- Tests MUST cover rollback, duplicate requests, concurrent update behavior, and
  invariant enforcement.

## SQLAlchemy and Alembic

- SQLAlchemy 2.x typed declarative and session APIs MUST be used.
- ORM mappings MUST remain in infrastructure code.
- Every production schema change MUST have an Alembic migration.
- Migrations MUST have deterministic revision identifiers, upgrade logic, and downgrade
  logic when safe and practical.
- Destructive or irreversible migrations MUST declare backup, verification, and rollback
  strategy.
- Foreign keys, uniqueness, checks, and indexes MUST enforce critical invariants where
  the database can do so.
- Migration tests SHOULD run from an empty database and from the previous supported
  revision.

## Testing

| Level | Required purpose |
|---|---|
| Unit | Domain rules, policy, parsing, and deterministic transformations |
| Contract | Provider, API, schema, and repository compatibility |
| Integration | Database, migrations, workflow provider, object store, and adapters |
| End-to-end | Critical user and governed-workflow outcomes |
| Security | Authorization, tenant isolation, secret handling, abuse, and dependency risk |
| Recovery | Retry, restart, rollback, backup restore, and provider failure |

- New behavior MUST have tests at the lowest sufficient level.
- Critical workflows MUST have at least one end-to-end acceptance test.
- Tests MUST be deterministic, isolated, and safe to rerun.
- External services SHOULD use contract fakes for fast tests and real adapters for
  integration tests.
- Implementation and independent validation MUST be separable roles.

## Ruff and MyPy

- Repository Python MUST pass the configured Ruff checks.
- Production Python MUST pass MyPy strict mode unless a narrow, documented exclusion is
  approved.
- Suppressions MUST be specific and explain why type or lint safety cannot be expressed.
- Formatting and import order MUST be automated and reproducible.

## Documentation

- Behavior, configuration, architecture, security, and operations changes MUST update the
  relevant documentation in the same change.
- Markdown links MUST resolve.
- Documentation MUST distinguish current, proposed, deferred, and example content.
- Commands MUST avoid real secrets and machine-specific credentials.
- Canonical definitions SHOULD be linked rather than copied.
- Claims of support MUST include validation evidence.

## ADRs

- Significant durable decisions MUST use the established ADR lifecycle and template.
- Accepted ADRs MUST NOT be rewritten; a new ADR supersedes them.
- ADRs MUST include context, decision, consequences, alternatives, security, budget,
  implementation constraints, validation, review triggers, and references.
- Proposed ADRs MUST NOT be described as implemented.

## Security

- Secrets MUST NOT be committed, logged, placed in URLs, or embedded in examples.
- Least-privilege scopes MUST be documented for every provider.
- Authentication and authorization MUST be tested independently.
- Tenant-scoped data MUST carry organization ownership and enforce access at every
  boundary.
- Inputs, provider outputs, archives, and generated code MUST be treated as untrusted.
- High-risk security changes MUST receive independent security review and human approval.

## Versioning and releases

- Public contracts and schemas MUST use semantic versions.
- Breaking changes MUST include migration and rollback guidance.
- Releases MUST be built from immutable commits and produce traceable artifacts.
- Release notes MUST state user impact, migrations, security changes, known limitations,
  and rollback.

## CI/CD

- Pull requests MUST run deterministic lint, typing, tests, and applicable build checks.
- Required checks MUST run in an environment independent from the implementing agent.
- Deployment MUST promote the same verified artifact across environments.
- Production deployment MUST require explicit human authorization.
- A failed required check MUST NOT be bypassed without a recorded exception.

## Observability

- Requests, workflows, provider calls, decisions, and audit events MUST carry correlation
  identifiers.
- Logs MUST be structured, sanitized, and useful without exposing secrets.
- Metrics MUST cover availability, latency, error, saturation, cost, queue depth, and
  policy outcomes where applicable.
- Alerts MUST identify an owner and response action.

## Provider conformance

- Each adapter MUST pass the common provider contract suite and capability-specific
  tests.
- Timeouts, retries, rate limits, idempotency, errors, health, cost, and events MUST be
  observable and normalized.
- Unsupported operations MUST fail explicitly.
- A provider MUST NOT be marked supported without current conformance evidence.

## Definition of done

A change is done only when:

1. acceptance criteria and authority are satisfied;
2. implementation respects domain and provider boundaries;
3. migrations and compatibility are addressed;
4. applicable lint, typing, tests, links, documentation, and container checks pass;
5. security, budget, observability, rollback, and operations impacts are recorded;
6. evidence is reproducible and limitations are disclosed;
7. independent review is complete when required;
8. the authorized human makes any required final decision.
