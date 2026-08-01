# Devsembly Provider SDK

**Status:** Binding contract baseline; adapters mature independently
**SDK version:** 0.1.0

The Provider SDK defines how replaceable implementations expose Devsembly capabilities.
It is language-neutral at the contract level. Python protocols and adapters may implement
these contracts without exposing provider libraries to domain code.

## Contract set

| Contract | Purpose |
|---|---|
| [Provider contract](provider-contract.md) | Common identity, operations, errors, timeouts, idempotency, and observability |
| [Capability contract](capability-contract.md) | Capability definition and compatibility |
| [Lifecycle contract](lifecycle-contract.md) | Initialize, ready, degrade, drain, stop, and upgrade |
| [Health contract](health-contract.md) | Liveness, readiness, dependency, and functional probes |
| [Configuration contract](configuration-contract.md) | Typed configuration, validation, and secret references |
| [Authentication contract](authentication-contract.md) | Credential and identity boundaries |
| [Event contract](event-contract.md) | Normalized provider events and delivery |
| [Conformance](conformance.md) | Required test and evidence model |
| [Examples](examples/README.md) | Nonbinding example manifests |

Machine-readable manifests use the
[provider manifest schema](../schemas/provider-manifest.schema.json).

## Required provider categories

| Category | Stable capability | Minimum contract surface |
|---|---|---|
| Source control | `source-control` | Repository, ref, commit, review, check, release, events |
| Work tracking | `work-tracking` | Work item, relationship, comment, state, events |
| LLM | `llm-inference` | Model metadata, generate, stream, usage, safety, cancellation |
| Coding agent | `coding-agent` | Task, workspace, tool policy, progress, evidence, cancellation |
| Identity | `identity` | Authenticate, subject mapping, claims, session and key health |
| Relational database | `relational-database` | Connection, transaction, migration support, backup signals |
| Object storage | `object-storage` | Put, get, metadata, checksum, retention, signed access |
| Workflow orchestration | `workflow-orchestration` | Start, signal, query, cancel, history evidence |
| Container runtime | `container-runtime` | Build, run, inspect, stop, network, volume, image evidence |
| Infrastructure/cloud | `infrastructure` | Plan, provision, inspect, change, destroy under authority |
| Deployment | `deployment` | Deploy, promote, health, rollback, environment evidence |
| Monitoring | `monitoring` | Emit, query, alert, silence under policy, health |

An adapter may implement multiple capabilities, but each capability declares and tests
its contract independently.

## Support levels

- **Experimental:** incomplete conformance; no production claim.
- **Candidate:** required tests pass in a controlled environment.
- **Supported:** conformance, operations, security, compatibility, and replacement
  evidence are current for the stated version.
- **Deprecated:** supported only through a declared transition.
- **Unsupported:** must not be selected for required work.

## Design rules

- Domain code depends on capability ports, not this SDK's provider implementation types.
- Provider metadata never creates organization authority.
- Provider-specific extensions are namespaced, optional, and capability-discoverable.
- Unsupported operations fail explicitly.
- Mutations require idempotency behavior and audit correlation.
- Cost and usage are observable before and after execution where the provider permits.
- Support claims identify versions, environment, evidence time, and known limits.
