# ADR-0017: Ephemeral Docker execution boundary

- Status: Accepted
- Date: 2026-08-01

## Context

Repository content, coding-provider behavior, and validation commands are untrusted. A temporary
checkout and an environment allowlist do not isolate the worker filesystem, process namespace,
network, or credentials. The first governed delivery-loop fixture must not run with external-provider
credentials until coding and validation have an operating-system boundary.

## Decision

Genesis will execute coding and validation through the provider-neutral `ExecutionSandbox` contract.
The first implementation uses one ephemeral Docker container per command and fails closed when Docker
or the configured image is unavailable. It never falls back to host execution.

Each container:

- runs as fixed non-root identity `65532:65532`;
- receives the task checkout as its only writable host mount and overlays `.git` read-only;
- uses a read-only root filesystem and a bounded, non-executable `/tmp`;
- receives a deterministic, credential-free environment;
- has network disabled with `--network none`;
- drops all Linux capabilities and prevents privilege escalation;
- receives CPU, memory, PID, file-size, aggregate-workspace, output, and wall-clock limits;
- is force-removed after success, command failure, timeout, cancellation, or output/storage limit;
- records its image identifier, command vector, effective limits, identity, network policy, exit,
  termination reason, timestamps, and cleanup result in workflow evidence.

The worker removes labelled orphan containers during startup. Genesis v0.1 operates one worker for this
queue; coordinated orphan ownership is required before multiple workers share one Docker daemon.

Validation is credential-free. The first coding slice is also credential-free and deny-all network.
External model-provider access remains disabled by default. ADR-0018 defines the optional controlled
outer gateway that issues narrowly scoped, short-lived task access and enforces destination policy.

Source-control operations remain outside the sandbox behind the source-control provider. The Docker
socket is never mounted into a task container.

## Consequences

- Sandbox startup failure becomes a safe, auditable terminal run instead of host execution.
- Shell metacharacters remain literal because commands cross the boundary as argument vectors.
- A container or microVM implementation can replace Docker without changing factory orchestration.
- The credentialed development-host fixture remains blocked until the Docker integration and model-
  gateway security tests run on the controlled host with approved disposable access.
- The v0.1 workspace storage limit combines Docker file-size enforcement with active aggregate-size
  monitoring. Filesystem quota-backed workspaces remain a future hardening option.

## Rejected alternatives

### Host subprocesses with filtered environments

Rejected because environment filtering does not isolate filesystems, processes, or networking.

### Unrestricted Docker bridge networking

Rejected because bridge networking does not enforce destination-level policy.

### Building a generalized container or microVM platform now

Rejected because issue #33 needs one narrow execution boundary, while the provider contract preserves
future runtime choice.
