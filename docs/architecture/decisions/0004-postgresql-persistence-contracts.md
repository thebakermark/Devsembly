# ADR 0004 — PostgreSQL Persistence Contracts

- **Status:** Accepted
- **Date:** 2026-07-30
- **Decision owners:** Devsembly Architecture
- **Applies to:** Genesis v0.1

## Context

Genesis needs reliable persistence for organizations, initiatives, projects, budgets, decisions, approvals, workflow correlations, evidence metadata, and audit records. The model must support transactions, relational integrity, flexible metadata, migrations, reporting, and future multi-tenant controls without introducing multiple authoritative databases.

The platform already uses PostgreSQL in its development foundation. Redis and object storage are also available, but neither should become the canonical system of record for business state.

## Decision

Use **PostgreSQL as the canonical transactional database**, with **SQLAlchemy 2.x** for persistence mapping and **Alembic** for schema migrations.

Persistence follows explicit contracts:

- domain and application layers depend on repository and unit-of-work interfaces;
- ORM models remain inside infrastructure adapters;
- PostgreSQL constraints enforce critical invariants;
- JSONB is allowed for bounded, versioned extension metadata, not as a substitute for core relational modeling;
- domain events use a transactional outbox table;
- audit records are append-only;
- MinIO-compatible object storage holds large files and evidence blobs while PostgreSQL stores metadata, checksums, ownership, and retention state;
- Redis may be used for cache, locks, rate limits, and ephemeral coordination, never as the sole source of truth.

## Alternatives considered

### SQLite

Appropriate for prototypes and tests, but rejected as the production reference because Genesis needs concurrent workflows, durable transactions, and a path to tenant isolation.

### Document database

Not selected because the core model is highly relational and requires strong integrity across budgets, approvals, decisions, and work.

### Event sourcing as the primary model

Deferred. Append-only events and audit history are required, but full event sourcing would add projection, migration, and operational complexity before demonstrated need.

### Direct ORM access from all modules

Rejected because it would create cross-module coupling and make future service extraction difficult.

## Consequences

### Positive

- one authoritative business datastore;
- strong transactions and relational integrity;
- mature migration and operational tooling;
- supports structured data plus limited flexible metadata;
- clear path to reporting, row-level security, and scaling;
- persistence implementations remain replaceable behind contracts.

### Negative

- repository and unit-of-work abstractions add code;
- PostgreSQL operations and backup discipline are required;
- JSONB usage must be governed to prevent schema erosion;
- transactional outbox delivery requires a worker and idempotent consumers.

## Budget impact

Genesis uses the existing self-hosted PostgreSQL container, so no new monthly service cost is required. Managed PostgreSQL is deferred until reliability, customer commitments, or operational evidence justifies the increase.

## Security impact

- use separate database roles for application runtime, migrations, reporting, and administration;
- encrypt connections and backups;
- never store provider secrets in ordinary domain tables;
- include tenant and ownership identifiers in all tenant-scoped records;
- design for row-level security even if application-enforced isolation is used initially;
- append-only audit records require restricted mutation privileges;
- evidence metadata must include checksum and retention classification.

## Implementation constraints

- all schema changes require Alembic migrations;
- migrations must be reversible when practical and tested against a copy of representative data;
- foreign keys and unique constraints enforce business invariants where possible;
- money uses fixed-precision decimal values with explicit currency;
- timestamps use UTC and timezone-aware types;
- identifiers use UUIDs generated independently of database sequence exposure;
- optimistic concurrency is required for mutable aggregate roots;
- every write that emits an integration event writes the outbox record in the same transaction;
- repository contracts receive and return domain objects or explicit data-transfer objects, not raw ORM entities.

## Validation

This decision is validated when Genesis can create and recover the full organization-to-workflow record graph, enforce budget and approval invariants transactionally, publish an outbox event without dual-write loss, restore from backup, and verify evidence metadata against stored object checksums.

## Review triggers

Review when measured scale requires partitioning, a read replica, managed PostgreSQL, a dedicated analytics store, or extraction of a module into an independently owned datastore.