# Kernel Lifecycle

**Status:** Proposed
**Version:** 0.1.0

## States

`uninitialized -> initializing -> ready -> degraded -> draining -> stopped`

Any active state may enter `failed`. Recovery from `failed` requires a fresh
initialization or an explicitly supported repair transition.

## Initialization order

1. Load non-secret bootstrap configuration.
2. Resolve secret references through the configured secret capability.
3. Validate identity, policy, and audit prerequisites.
4. Initialize the canonical datastore and migration compatibility check.
5. Register capability contracts.
6. Initialize required providers in dependency order.
7. Verify provider health and conformance versions.
8. Start outbox, workflow, and background consumers.
9. Publish readiness only after required capabilities are ready.

Optional providers may produce `degraded` status; missing required providers block
readiness.

## Runtime behavior

Health is evaluated separately as liveness, readiness, dependency health, and functional
probe. Repeated failures use circuit, bounded retry, or safe-stop policy. Lifecycle
changes emit sanitized events and audit evidence.

## Shutdown

The Kernel stops accepting new work, records drain state, pauses schedulers, waits within
a deadline for in-flight work, checkpoints provider correlations, flushes outbox and
telemetry where safe, closes providers in reverse dependency order, and records outcome.
Forced shutdown must be detectable on restart.

## Upgrade

An upgrade declares contract compatibility, schema migration, provider compatibility,
workflow versioning, rollback, and mixed-version behavior. Migrations run before
readiness and destructive changes require a verified backup.

## Validation

Lifecycle tests cover clean startup, missing configuration, unavailable required and
optional providers, degraded recovery, duplicate start, graceful drain, forced stop,
restart reconciliation, and version mismatch.
