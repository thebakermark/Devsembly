# Provider Lifecycle Contract

**Status:** Binding baseline
**Contract version:** 0.1.0

## States

`discovered -> validated -> configured -> initializing -> ready -> degraded -> draining -> stopped`

`failed` is reachable from initialization or active states. `disabled` is an
administrative state that prevents selection.

## Required operations

- `validate_manifest`: verify identity, compatibility, permissions, and schemas.
- `validate_configuration`: check non-secret values and secret references.
- `initialize`: create a scoped instance without publishing readiness early.
- `health`: report normalized health and evidence.
- `drain`: reject new work and finish or checkpoint accepted work.
- `shutdown`: close connections and release resources within a deadline.
- `upgrade`: verify compatibility and migration before switching versions.
- `disable`: prevent selection and revoke access where policy requires.

Operations are safe to repeat or explicitly report their current transition.

## Dependencies

Providers declare required capability dependencies and initialize in topological order.
Cycles are invalid. Shutdown uses reverse order.

## Upgrade and rollback

Upgrade declares contract, configuration, data, credential, event, and runtime
compatibility. State migration must be rehearsed. Failure leaves the prior version ready
or the instance disabled with explicit operator action.

## Evidence

Every transition records actor, authority, prior and new state, configuration fingerprint,
version, time, result, and sanitized error.
