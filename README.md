# Devsembly

**The agent-powered software assembly line.**

Devsembly is a self-hosted AI software factory for planning, architecting, building, testing, reviewing, securing, documenting, deploying, and operating software products through controlled multi-agent workflows.

The first flagship application is being developed with Devsembly, but the platform is product-agnostic and product names may change over time.

## Core principles

- Human ownership of product direction and high-risk approvals
- Specialized agents with narrowly scoped responsibilities
- No agent approves its own work
- A source-control provider is authoritative for repository and delivery evidence
- Every change starts with a traceable work item
- Every change is built in an isolated branch or workspace
- Independent validation verifies all agent claims
- Preview and staging deployments precede production
- Least-privilege credentials and complete audit logging
- Repeated failures escalate instead of looping indefinitely
- Capabilities and interfaces are stable; provider implementations are replaceable

## Supported platform

Devsembly currently requires a **Development Host** running a supported Ubuntu LTS release. Ubuntu is the only host operating system currently built, tested, and supported by the project.

A Development Host may run on any compatible infrastructure provider. The first documented and tested provider is recorded in the provider documentation, but provider-specific assumptions should remain outside the core application and installer wherever practical.

Most Devsembly application services run in Docker containers. Host operating-system differences primarily affect provisioning, package installation, Docker setup, users and permissions, firewall configuration, service management, and first-boot automation.

See [`docs/platform-support.md`](docs/platform-support.md) for the support policy and terminology.

## Capability model

Devsembly is designed around stable capabilities rather than temporary product names.

| Capability | Responsibility |
|---|---|
| Conversational intake | Accept and normalize goals, requests, questions, and approvals |
| Workflow execution | Coordinate durable tasks, retries, gates, budgets, and escalation |
| AI coding | Plan, implement, debug, test, review, and document changes |
| Source control | Manage work items, repositories, branches, reviews, releases, and audit history |
| Independent validation | Run quality, security, policy, integration, and browser checks |
| Deployment | Create preview environments and control staging and production promotion |
| Browser development environment | Provide secure browser-accessible editing and terminal sessions |
| Knowledge and retrieval | Store standards, decisions, project context, and reusable organizational knowledge |
| Secrets and identity | Protect credentials and enforce least-privilege access |
| Observability | Collect logs, metrics, traces, errors, alerts, and diagnostics |
| Data and storage | Persist workflow state, artifacts, evidence, and backups |

Each capability is implemented through a provider interface and selected through configuration. Product and vendor names belong in provider-specific registries, adapters, compatibility matrices, and implementation guides.

See [`docs/architecture/capability-provider-model.md`](docs/architecture/capability-provider-model.md).

## Lifecycle

```text
Idea
  -> product discovery
  -> requirements and acceptance criteria
  -> architecture and threat model
  -> implementation plan
  -> isolated parallel development
  -> local validation
  -> independent agent review
  -> pull request and CI
  -> preview environment
  -> human approval
  -> staging validation
  -> controlled production release
  -> monitoring and learning
```

## Repository status

This repository contains the product foundation, Genesis Library, workflow specifications, agent role contracts, infrastructure blueprint, security model, initial CI scaffolding, and the first runnable Genesis control-plane scaffold. Application capabilities will continue to be added incrementally through reviewed pull requests.

## Getting started

1. Read the canonical [`Genesis Library`](docs/genesis/README.md).
2. Review the supported-host requirements in [`docs/platform-support.md`](docs/platform-support.md).
3. Review the capability and provider model in [`docs/architecture/capability-provider-model.md`](docs/architecture/capability-provider-model.md).
4. Read [`docs/vision/product-vision.md`](docs/vision/product-vision.md).
5. Review [`docs/architecture/system-architecture.md`](docs/architecture/system-architecture.md).
6. Review [`docs/security/trust-model.md`](docs/security/trust-model.md).
7. Read the Genesis contract in [`docs/implementation/genesis-reference-implementation-plan.md`](docs/implementation/genesis-reference-implementation-plan.md).
8. Start the runnable local stack with [`docs/implementation/genesis-local-development.md`](docs/implementation/genesis-local-development.md).
9. Use the issue templates to propose work.

## License

No open-source license has been selected yet. Until one is added, all rights are reserved.

## Wiki and operating documentation

A full version-controlled wiki source is included under [`wiki/`](wiki/). It covers Development Host provisioning, browser access, source control, workflow execution, deployment, agent workflows, security, backups, monitoring, daily operations, releases, and troubleshooting.

Shared documentation names capabilities. Provider-specific product names and instructions belong in dedicated provider guides unless the implementation detail is technically required.
