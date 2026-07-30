# Provider Event Contract

**Status:** Binding baseline
**Contract version:** 0.1.0

## Inbound events

Adapters verify signature or authenticated transport, provider account and installation,
timestamp and replay window, event ID, organization mapping, and payload schema before
acceptance. Raw payload retention follows classification and policy.

## Normalized envelope

Events include event and delivery IDs, provider and instance, capability, event type and
schema version, occurred and received UTC times, organization, provider subject
correlation, correlation and causation IDs, classification, normalized payload, and raw
evidence reference when retained.

## Delivery behavior

Delivery is assumed at least once unless a provider proves otherwise. Consumers dedupe by
provider event or delivery ID, tolerate reordering, reconcile missed events, quarantine
invalid payloads, and bound retries. Acknowledgment occurs only after durable acceptance
when the provider protocol allows it.

## Outbound events

Provider mutations that emit events retain the original idempotency and correlation
identifiers. Reconciliation must tolerate an event arriving before the mutation response.

## Validation

Tests cover valid signature, invalid and stale signature, duplicate, reordering, unknown
installation, incompatible schema, missing event, reconciliation, and secret redaction.
