# ADR-0018: Controlled model egress gateway

- Status: Accepted
- Date: 2026-08-01

## Context

ADR-0017 established a credential-free, deny-all-network Docker boundary for coding and validation.
That boundary prevents untrusted repository content from reaching the network, but Claude Code needs a
model-provider connection to complete issue #33's live fixture. Unrestricted bridge networking or a
long-lived provider API key inside the task container would undo the isolation boundary.

## Decision

Genesis will use a narrow outer model-egress gateway for the first live fixture.

- Validation remains credential-free with `--network none`.
- Coding uses the gateway only when its complete configuration is present; partial configuration
  fails closed.
- The worker issues an HMAC-signed, task-bound token that expires after five minutes. The task never
  receives the signing secret or provider API key.
- The coding container connects only to a named Docker-internal network. The runtime verifies the
  network's `Internal` property before starting the task.
- The gateway is the only service on both that internal network and a provider-egress network. It is
  not connected to the control-plane network or its databases.
- The gateway accepts only Anthropic Messages and token-count requests, only for configured model
  identifiers, with bounded request count, output tokens, request size, response size, and upstream
  time.
- The upstream origin must be HTTPS and its host must appear in the explicit destination allowlist.
- Caller authorization and arbitrary headers are discarded. The gateway adds the real provider key
  only on the fixed upstream request.
- The Genesis v0.1 worker processes one activity at a time so two untrusted task containers cannot
  share the internal gateway network concurrently. Multi-worker network isolation is deferred.

Claude Code receives `ANTHROPIC_BASE_URL` and `ANTHROPIC_AUTH_TOKEN`; the token authorizes only the
gateway and is not a provider credential. Source-control publication remains outside the sandbox.

## Consequences

- A compromised task can call only the narrow gateway surface during its token lifetime.
- A task cannot select an arbitrary destination, model, provider operation, Docker network, or
  upstream authorization value.
- The real model credential remains confined to the gateway process.
- Streaming provider responses are bounded and buffered by the first implementation. A streaming
  relay can replace this after the live fixture if latency or memory evidence requires it.
- Multi-worker or concurrent activity execution requires per-task network isolation before the
  concurrency limit is raised.
- The per-token request counter is process-local in Genesis v0.1. A durable distributed counter is
  required before the gateway is replicated.
- Controlled-host configuration, disposable credentials, and the live fixture remain operational
  validation steps; this decision does not authorize production use.

## Rejected alternatives

### Provider key inside the sandbox

Rejected because repository content and the coding process are untrusted and could extract a
long-lived credential.

### Unrestricted bridge networking

Rejected because it allows arbitrary destinations and access to unrelated services.

### General multi-provider router

Rejected for issue #33. Provider portfolio and routing work remains queued in issues #34 and #35.
