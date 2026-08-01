# Event Bus

**Status:** Genesis PostgreSQL transport implemented
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

Genesis writes domain state, an append-only audit record, and the outbox entry in one
transaction. A dedicated publisher claims committed entries with time-bounded leases and
atomically inserts them into the durable `published_events` feed while acknowledging the
outbox row. The event UUID is the feed's primary key, so recovery after a crash cannot
create a second publication.

Failed publication attempts release their lease and become available after bounded
exponential backoff. A crashed worker's lease expires so another worker can safely claim
the event. The publisher writes a PostgreSQL heartbeat used by its container health check
and the API readiness endpoint.

Consumers still must be idempotent because their own processing can fail after reading a
published event. Consumer checkpoints and dead-letter handling belong to the consumer
slice; Temporal dispatch is the next consumer.

Event order is guaranteed only where a documented aggregate or partition rule provides
it. Consumers must not infer global order.

## Evolution

Additive compatible changes use a schema minor version. Breaking changes use a new event
type or major version with a coexistence and migration plan. Historical events are not
rewritten.

## Validation

Current tests cover atomic audit/outbox writes, idempotent publication, retry scheduling,
expired-lease recovery, duplicate prevention, and stale worker health. Consumer
checkpoint, out-of-order input, incompatible-schema, poison-event, and retry-exhaustion
tests remain with the first consumers.
