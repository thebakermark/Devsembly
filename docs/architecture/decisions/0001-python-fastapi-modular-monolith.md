# ADR 0001 — Python and FastAPI Modular Monolith

- **Status:** Accepted
- **Date:** 2026-07-30
- **Decision owners:** Devsembly Architecture
- **Applies to:** Genesis v0.1

## Context

Genesis must deliver one end-to-end vertical slice on a constrained budget while remaining understandable to human and AI contributors. The platform requires HTTP APIs, typed contracts, background workflow integration, generated API documentation, and strong Python interoperability with AI and automation libraries.

Premature microservices would increase deployment, observability, networking, testing, and operational costs before independent scaling is justified.

## Decision

Build Genesis as a **Python modular monolith using FastAPI and Pydantic**.

The application will be one deployable service with explicit internal modules for:

- organizations and projects;
- initiatives and work items;
- budgets and cost records;
- agents and approvals;
- decisions and evidence;
- workflows and integrations;
- audit events.

Modules communicate through application service interfaces and domain events rather than importing each other's persistence internals. Public interfaces use versioned HTTP APIs and generated OpenAPI contracts.

## Alternatives considered

### Django

Mature, batteries-included, and strong for administration. Not selected because Genesis is API- and workflow-first, and FastAPI provides a smaller typed core with direct Pydantic integration. Django remains a valid future option for a separate administrative surface if justified.

### Node.js with NestJS

Strong modular architecture and ecosystem. Not selected because Devsembly's AI, automation, and orchestration ecosystem is primarily Python-based, and introducing a second primary runtime would increase complexity.

### Microservices

Deferred until measured scaling, isolation, compliance, or release-cadence requirements justify extraction.

## Consequences

### Positive

- one build, deployment, and rollback unit;
- low infrastructure cost;
- typed API contracts;
- straightforward local development and testing;
- direct access to Python AI and automation libraries;
- modules can later be extracted behind existing interfaces.

### Negative

- module boundaries require enforcement in code review and tests;
- failures can affect the whole application process;
- independent scaling is limited until modules are extracted.

## Budget impact

No additional managed service is required. Genesis can run in the existing Docker environment on one development host and remain compatible with a `$50/month` infrastructure constraint.

## Security impact

The application must centralize authentication middleware, authorization policy enforcement, input validation, audit logging, secure headers, and secret access. Internal module boundaries do not replace authorization checks.

## Implementation constraints

- Python package boundaries must mirror domain modules.
- Direct cross-module database table access is prohibited.
- API schemas must not expose ORM models directly.
- Every module must provide unit tests and contract tests.
- Configuration must use typed settings and environment-based secret references.
- Extraction into a service requires a new ADR.

## Validation

This decision is validated when the Genesis workflow can be executed through one FastAPI deployment, all module-boundary tests pass, and the service publishes a versioned OpenAPI specification.

## Review triggers

Review when one module requires independent scaling, a separate security boundary, a materially different runtime, or an independent deployment cadence.