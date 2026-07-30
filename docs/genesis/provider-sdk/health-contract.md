# Provider Health Contract

**Status:** Binding baseline
**Contract version:** 0.1.0

## Dimensions

- **Liveness:** adapter process can respond.
- **Readiness:** instance can accept the declared operations.
- **Dependency:** required upstream systems are reachable and compatible.
- **Functional:** a safe provider-specific probe proves critical behavior.
- **Conformance freshness:** support evidence remains within its review window.

## Response

Health returns overall state (`healthy`, `degraded`, `unhealthy`, or `unknown`), checked
time, latency, capability and operation impact, dependency states, rate-limit or capacity
signals, evidence, next check, and sanitized reason codes.

Health must not expose credentials, grant authority, or perform a billable or mutating
probe without explicit declaration and budget.

## Aggregation

A required operation unavailable makes readiness false. Optional capability failure may
produce degraded state. Unknown high-risk dependency state fails closed.

## Validation

Tests cover timeout, expired credential, permission loss, provider outage, rate limit,
partial capability degradation, incompatible API version, stale evidence, recovery, and
safe probe behavior.
