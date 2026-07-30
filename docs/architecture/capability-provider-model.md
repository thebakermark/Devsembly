# Capability and provider model

## Decision

Devsembly architecture and shared documentation are **capability-first**. Core workflows depend on named capabilities and stable provider interfaces rather than directly depending on product or vendor names.

Product names belong only in provider registries, implementation adapters, compatibility matrices, installation guides, and migration notes where the specific implementation matters.

## Design principles

1. **Capability first** — describe what the platform needs before selecting a product.
2. **Provider abstraction** — external dependencies are accessed through stable provider interfaces.
3. **Replaceable implementations** — a provider can be replaced without redesigning the core workflow.
4. **Configuration over code** — deployments select implementations through configuration.
5. **Provider-specific boundaries** — credentials, API details, installation steps, and limitations stay inside the relevant adapter and guide.
6. **Honest support claims** — an implementation is marked supported only after automated validation and documented operating evidence.

## Capability catalog

| Capability | Stable interface name | Responsibility |
|---|---|---|
| Source control | `SourceControlProvider` | Repositories, issues, branches, pull requests, reviews, releases, and audit events |
| AI coding | `AICodingProvider` | Planning, implementation, debugging, testing, review, and documentation tasks |
| Workflow execution | `WorkflowProvider` | Durable state, retries, approvals, timeouts, and task orchestration |
| Knowledge | `KnowledgeProvider` | Project context, standards, decisions, retrieval, and reusable organizational knowledge |
| Deployment | `DeploymentProvider` | Preview, staging, production promotion, health verification, and rollback |
| Infrastructure | `InfrastructureProvider` | Development Host provisioning, networking, storage, snapshots, and lifecycle operations |
| Identity | `IdentityProvider` | Authentication, authorization, users, groups, and service identities |
| Secrets | `SecretsProvider` | Secret storage, retrieval, rotation, and access policy |
| Observability | `ObservabilityProvider` | Logs, metrics, traces, errors, alerts, and diagnostics |
| Database | `DatabaseProvider` | Durable relational application and workflow data |
| Object storage | `ObjectStorageProvider` | Artifacts, backups, evidence, exports, and large files |
| Search | `SearchProvider` | Full-text and indexed retrieval |
| Vector retrieval | `VectorProvider` | Embeddings and semantic retrieval |
| Notifications | `NotificationProvider` | Email, chat, webhook, and operational notifications |
| Browser IDE | `BrowserIDEProvider` | Browser-accessible editing, terminals, and development sessions |
| Test execution | `TestProvider` | Unit, integration, browser, security, and policy validation |
| Backup | `BackupProvider` | Scheduled backups, retention, restore verification, and recovery evidence |
| DNS | `DNSProvider` | Records, certificates, routing, and domain automation |

## Provider selection

Deployments select implementations by provider identifier rather than embedding a product name into core code.

```yaml
providers:
  source_control: ${SOURCE_CONTROL_PROVIDER}
  ai_coding: ${AI_CODING_PROVIDER}
  workflow: ${WORKFLOW_PROVIDER}
  deployment: ${DEPLOYMENT_PROVIDER}
  infrastructure: ${INFRASTRUCTURE_PROVIDER}
  secrets: ${SECRETS_PROVIDER}
  observability: ${OBSERVABILITY_PROVIDER}
```

The values are deployment configuration. Shared architecture should not assume a particular value.

## Adapter contract

Each provider adapter must declare:

- capability and provider identifier;
- supported operations;
- configuration schema;
- required permissions;
- health and readiness checks;
- error and retry behavior;
- rate, cost, and resource limits;
- security and data-handling boundaries;
- migration and rollback behavior;
- automated contract-test evidence;
- documentation and support status.

## Documentation rules

Shared documentation should say:

> Configure the Source Control Provider.

Provider documentation may say:

> Configure the selected source-control implementation using this guide.

Shared documentation must not require readers to infer architecture from a temporary product list. Product names may be shown only as current implementation examples or in dedicated provider guides.

## Adding or replacing a provider

A new provider implementation requires:

1. an adapter implementing the capability contract;
2. configuration and secret schemas;
3. contract, integration, and failure-mode tests;
4. security and permissions review;
5. provider-specific installation and operations documentation;
6. support-matrix and compatibility updates;
7. migration and rollback guidance;
8. verified evidence before being marked supported.

Replacing an implementation should not require changes to unrelated core workflows. If replacement requires core changes, the capability interface must be reviewed for leaked provider-specific assumptions.
