# Provider Manager

**Status:** Proposed logical component
**Version:** 0.1.0

## Responsibilities

The provider manager validates manifests and configuration, resolves secret references,
constructs adapters, orders dependencies, starts and stops providers, monitors health,
applies timeout and circuit policy, exposes normalized status, and coordinates
replacement.

It does not own provider credentials as domain data, interpret business policy, or mark a
provider supported without conformance evidence.

## Instance model

Each instance records provider and adapter IDs, capability versions, organization and
environment scope, configuration fingerprint, secret references, permissions, lifecycle
state, health, conformance evidence, cost model, and last transition.

## Failure policy

Errors are normalized using the Kernel categories. Retries require an idempotent
operation or explicit idempotency key and obey provider hints, exponential backoff,
jitter, deadlines, attempt ceilings, and budget limits. Authentication and policy errors
are not retried automatically.

## Replacement sequence

1. Validate the replacement contract and permissions.
2. Run conformance and functional probes.
3. Export and map provider-owned records where required.
4. Rehearse cutover and rollback.
5. Drain or pause new writes.
6. Reconcile state and switch configuration under approval.
7. Monitor, then revoke old access and record residual data.

## Validation

Tests cover dependency ordering, invalid secrets and configuration, duplicate start,
degraded health, circuit behavior, timeout, rate limit, shutdown, replacement rollback,
and credential revocation.
