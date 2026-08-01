# Provider Conformance

**Status:** Binding baseline
**Suite version:** 0.1.0

## Required test layers

1. **Manifest and schema:** identity, versions, permissions, configuration, and declared
   capabilities.
2. **Contract:** required operations, types, normalized errors, timeouts, cancellation,
   idempotency, events, and evidence.
3. **Security:** credential scope, redaction, tenant isolation, untrusted input, webhook
   verification, and revocation.
4. **Failure:** unavailable, timeout, rate limit, partial response, duplicate, conflict,
   integrity failure, and recovery.
5. **Lifecycle:** initialize, health, degrade, drain, stop, upgrade, rollback, and disable.
6. **Observability:** correlation, trace, usage, cost, sanitized errors, and audit.
7. **Integration:** real supported provider version in an isolated environment.
8. **Replacement:** export, identifier mapping, cutover, reconciliation, rollback, and
   credential revocation.

## Evidence record

Conformance evidence contains provider and adapter versions, contract and suite versions,
environment, test revision, configuration fingerprint with secrets removed, time, result,
failed or skipped cases, limitations, artifact checksums, reviewer, and expiry or review
date.

## Support decision

No provider is supported because its happy path works. Required tests must pass, skipped
tests require documented limits, operations and security review must be current, and the
support matrix must name exact compatible versions.

## Common assertions

- Unsupported operations return `unsupported`.
- Deadlines and cancellations are respected.
- Retried mutations do not duplicate side effects.
- Provider errors map to stable categories.
- Credentials and restricted data do not enter logs or evidence.
- Organization and environment scope cannot cross.
- Events deduplicate and reconcile.
- Health reflects permission and compatibility loss.
- Usage and cost are reported where available.
- Disable prevents new selection and documents retained state.

## Continuous conformance

Contract tests run on adapter changes. Scheduled integration tests detect provider API,
permission, and behavior drift. A failed required test downgrades support status until
resolved or explicitly excepted by authorized review.
