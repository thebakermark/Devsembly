# Provider Contract

**Status:** Binding baseline
**Contract version:** 0.1.0

## Metadata

Every provider instance declares:

- provider, adapter, and instance IDs;
- provider and adapter versions;
- implemented capability IDs and version ranges;
- organization and environment scope;
- support level and conformance evidence;
- configuration schema and fingerprint;
- required permissions and data classifications;
- regions, endpoints, service limits, and cost model;
- lifecycle and health state;
- documentation, owner, and replacement guide.

## Invocation envelope

Operations receive operation name and contract version, organization, principal and
delegation context, correlation and trace IDs, idempotency key for mutations, deadline,
budget context, input classification, and typed payload.

Responses contain outcome, typed result, provider correlation, normalized usage and
cost, evidence references, retry guidance, warnings, and sanitized metadata.

## Errors

Adapters map provider failures to:

| Error | Retry default |
|---|---|
| `invalid_request` | No |
| `unauthenticated` | No; refresh only through credential policy |
| `unauthorized` | No |
| `policy_denied` | No |
| `not_found` | No |
| `conflict` | Conditional after reconciliation |
| `unsupported` | No |
| `rate_limited` | Yes within deadline and budget |
| `timeout` | Conditional on idempotency |
| `unavailable` | Yes, bounded |
| `integrity_failure` | No; quarantine and escalate |
| `internal_failure` | Bounded only when safe |

Provider messages and codes may be retained in restricted evidence but cannot replace
the normalized class.

## Timeouts and cancellation

Every operation declares connect, response, total deadline, and cancellation behavior.
The caller's earlier deadline controls. Adapters must not continue billable or mutating
work after cancellation unless the provider cannot stop; that limitation must be
reported and reconciled.

## Idempotency

Every mutating operation declares one of:

- provider-enforced key;
- adapter-enforced key with durable correlation;
- reconciliation-required;
- non-idempotent and prohibited from automatic retry.

Idempotency scope and retention are documented and tested.

## Observability

Adapters emit sanitized duration, attempt, outcome, error class, provider correlation,
rate-limit state, usage, cost units, health, and trace context. Logs never include raw
credentials or restricted payloads by default.

## Compatibility

Adapters reject incompatible major contract versions. Optional features use declared
capability flags. Provider API deprecation must create an alert, migration plan, and
support-status update.
