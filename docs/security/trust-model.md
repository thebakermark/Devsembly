# Trust Model

## Required controls

- Least-privilege credentials per agent and environment
- No production credentials on development machines
- Protected default branches
- Pull-request-only changes
- Independent status checks
- Immutable audit events for orchestration decisions
- Secret scanning before commit and in CI
- Network isolation between development and production
- Human approval for production, destructive, financial and security-policy actions
- Reviewed third-party agent skills and plugins
- Bounded retries with escalation

## Untrusted execution boundary

Agent-produced code and repository validation commands are untrusted input. They must not inherit
worker credentials. The current worker therefore gives validation a minimal explicit environment,
uses argument-vector execution without shell interpretation, enforces normalized repository path
boundaries, and terminates timed-out or cancelled validation process groups. Non-idempotent delivery
execution is not automatically retried.

A temporary checkout is filesystem organization, not a security sandbox. Coding and validation now
cross the provider-neutral `ExecutionSandbox` boundary. The Docker implementation is ephemeral,
non-root, read-only-root, capability-free, deny-all-network, and resource bounded; it exposes only the
task workspace as writable and overlays Git metadata read-only. It receives no worker, source-control,
database, cloud, OIDC, or control-plane credentials and never falls back to host execution.

External model-provider egress remains disabled by default. When fully configured, the worker gives a
coding task only a five-minute, task-bound gateway token and connects it to a verified Docker-internal
network. The separate gateway holds the provider key, accepts only allowlisted Anthropic operations
and models, and forwards only to an allowlisted HTTPS origin. It is not connected to the control-plane
network. Validation never receives gateway access. Unrestricted bridge networking is not an
acceptable substitute.

Genesis v0.1 limits the worker to one active activity because coding sandboxes share the isolated
gateway network. Per-task networks are required before multi-worker or concurrent activity execution.
The live proof remains blocked until this topology is commissioned on the controlled development host
with approved disposable access.

The commissioning-only Compose override may mount the host Docker socket into the trusted worker so
it can create sibling task sandboxes. It also mounts a dedicated host workspace at the identical path
inside the worker so Docker bind mounts resolve to the intended disposable checkout. This exception
does not apply to normal Compose startup, and the socket is never mounted into a task sandbox.

Every sandbox attempt records the image identifier, argument vector, effective limits, non-root user,
network policy, timestamps, exit, termination reason, and cleanup result. The worker removes labelled
orphan containers on startup for the single-worker Genesis v0.1 queue.

## Credential classes

| Class | Intended access |
|---|---|
| Development agent | Development repositories, branches and disposable services |
| Review agent | Read-only code and diff access; review comments |
| CI identity | Build/test resources and artifact publishing |
| Deployment agent | Preview and staging deployment triggers |
| Release approver | Explicit production promotion only |

## Prohibited defaults

Agents must not receive organization-owner access, billing access, production root SSH, permission to disable checks, permission to force-push protected branches, or unrestricted access to customer data.
