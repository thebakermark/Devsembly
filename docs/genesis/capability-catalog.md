# Genesis Capability Catalog

**Status:** Binding catalog; maturity varies
**Version:** 0.1.0

Maturity uses **current**, **planned**, **proposed**, or **deferred**. A provider example
does not change capability ownership or imply support without conformance evidence.

| Capability | Contract owner | Genesis maturity | Initial implementation or posture |
|---|---|---|---|
| Organization registry | Organization domain | Current | Versioned FastAPI and PostgreSQL module |
| Initiative and project registry | Portfolio domain | Current | Organization-scoped FastAPI and PostgreSQL module |
| Budget policy and forecasting | Budget domain | Current foundation | Monthly limit and enforcement profile; forecasting planned |
| Decision and audit records | Governance domain | Planned | PostgreSQL plus evidence references |
| Identity | Identity and policy | Current | OIDC bearer verification and internal policy |
| Authorization and delegation | Identity and policy | Planned | Internal policy records |
| Workflow orchestration | Workflow capability | Current scaffold | Temporal adapter |
| Capability registry | Kernel | Proposed | Static configuration during Genesis |
| Provider management | Kernel | Proposed | Explicit adapters during Genesis |
| Domain event delivery | Event capability | Current writer | Transactional outbox writes; publisher planned |
| Memory and knowledge | Memory capability | Planned | Relational metadata and object evidence first |
| Relational database | Data capability | Current scaffold | PostgreSQL and SQLAlchemy |
| Object storage | Storage capability | Current scaffold | MinIO-compatible adapter |
| Ephemeral coordination | Cache capability | Current scaffold | Redis, never canonical |
| Source control | Delivery capability | Current adapter | GitHub as initial provider |
| Work tracking | Delivery capability | Planned | GitHub issues initially |
| LLM inference | Intelligence capability | Planned | Provider selected by configuration |
| Coding agent | Engineering capability | Current adapter | Command-based provider adapter |
| Independent validation | Quality capability | Current foundation | Repository, API, PostgreSQL, migration, and Docker CI |
| Container runtime | Execution capability | Current | Docker and Compose |
| Infrastructure/cloud | Infrastructure capability | Current guides | Provider-independent host contract |
| Deployment | Delivery capability | Planned | Provider adapter; production human gate |
| Monitoring and alerting | Observability capability | Planned | Provider selected by configuration |
| Knowledge graph | Knowledge capability | Deferred | Relationships modeled without dedicated graph DB |
| Plugin marketplace | Extension capability | Deferred | Contract design only |
| Business modules | Product capability | Deferred | Outside Genesis control-plane scope |

## Catalog rules

- Each capability MUST have an accountable contract owner.
- Required operations, inputs, outputs, policies, measures, service levels, and evidence
  MUST be defined before selecting a provider.
- Provider implementations MUST declare contract versions and conformance status.
- Maturity MUST be based on repository and operating evidence, not plans.
- Cost, security, data authority, failure, and exit behavior MUST be visible at selection.
