# Devsembly Kernel

**Status:** Proposed logical platform boundary
**Version:** 0.1.0

The Kernel defines shared platform ports and governance used by applications and
business modules. Under Genesis it is implemented incrementally inside the accepted
Python modular monolith. This specification does not authorize a separate Kernel
service, dynamic plugin loading, or additional paid infrastructure.

## Specifications

| Specification | Responsibility |
|---|---|
| [Kernel specification](kernel-specification.md) | Scope, boundaries, dependencies, and invariants |
| [Lifecycle](lifecycle.md) | Startup, readiness, degradation, shutdown, and upgrades |
| [Capability registry](capability-registry.md) | Capability definitions and resolution |
| [Provider manager](provider-manager.md) | Provider configuration, lifecycle, health, and replacement |
| [Event bus](event-bus.md) | Domain and integration event contracts |
| [Workflow engine](workflow-engine.md) | Governed workflow port and durability boundary |
| [Identity and policy](identity-and-policy.md) | Principals, delegation, authorization, and audit |
| [Memory services](memory-services.md) | Governed knowledge and retrieval ports |
| [Configuration](configuration.md) | Typed, layered, secret-safe configuration |
| [Observability](observability.md) | Logs, metrics, traces, audit, and cost signals |
| [Plugin model](plugin-model.md) | Permissioned extension packaging and isolation |

## Binding context

The Kernel is subordinate to the [Constitution](../book-1-constitution.md), accepted
[ADRs](../../architecture/decisions/README.md), and
[Book II](../book-2-architecture.md). Provider implementations conform to the
[Provider SDK](../provider-sdk/README.md).
