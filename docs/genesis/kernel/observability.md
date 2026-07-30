# Kernel Observability

**Status:** Proposed common contract
**Version:** 0.1.0

## Signals

- **Logs:** structured events for diagnosis, sanitized by default.
- **Metrics:** availability, latency, error, saturation, queue, policy, and cost measures.
- **Traces:** correlated request, workflow, activity, provider, and database spans.
- **Audit:** append-only evidence of material authority, policy, and state changes.
- **Evidence:** checksums and references to validation and operational artifacts.

Audit records are not ordinary debug logs and have separate access and retention.

## Required attributes

Signals include timestamp, service and version, environment, organization where
authorized, correlation and trace IDs, capability, provider, operation, outcome, error
class, duration, attempt, and cost units when available. High-cardinality and sensitive
attributes require explicit handling.

## Redaction

Secrets, tokens, credentials, raw authorization headers, private keys, and restricted
payloads must not be emitted. Principal and tenant identifiers follow classification and
access policy. Provider errors are sanitized before general logging.

## Service objectives

Each current capability defines availability, latency, correctness, recovery, and budget
indicators proportional to its maturity. Alerts name owner, threshold, response, and
escalation. An alert without a useful response is not complete.

## Validation

Tests verify correlation across boundaries, redaction, error normalization, cost
capture, audit append behavior, signal loss handling, and alert routing.
