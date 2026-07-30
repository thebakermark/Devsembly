# Event Bus

**Status:** Planned contract; PostgreSQL outbox is the Genesis transport
**Version:** 0.1.0

## Event types

- **Domain event:** an immutable fact emitted by a domain transaction.
- **Integration event:** a versioned external representation for another boundary.
- **Lifecycle event:** provider, workflow, configuration, or Kernel state transition.
- **Audit event:** governed evidence of an action or decision; audit authority remains
  separate from delivery transport.

## Envelope

Every event contains event ID, type, schema version, occurred-at UTC, recorded-at UTC,
producer, organization, correlation and causation IDs, aggregate ID and version when
applicable, data classification, payload, and trace context. Sensitive values and secrets
are prohibited.

## Delivery semantics

Genesis uses at-least-once delivery from a transactional PostgreSQL outbox. Producers
write domain state and outbox entry atomically. Consumers are idempotent, record
processing outcomes, enforce schema compatibility, and dead-letter or escalate bounded
failure.

Event order is guaranteed only where a documented aggregate or partition rule provides
it. Consumers must not infer global order.

## Evolution

Additive compatible changes use a schema minor version. Breaking changes use a new event
type or major version with a coexistence and migration plan. Historical events are not
rewritten.

## Validation

Tests cover atomic write, duplicate delivery, consumer restart, out-of-order input,
incompatible schema, poison event, retry exhaustion, and audit correlation.
