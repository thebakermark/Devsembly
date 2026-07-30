# Devsembly

**The agent-powered software assembly line.**

Devsembly is a self-hosted AI software factory for planning, architecting, building, testing, reviewing, securing, documenting, deploying, and operating software products through controlled multi-agent workflows.

CompanyOS is the first flagship product intended to be developed with Devsembly, but the platform is product-agnostic.

## Core principles

- Human ownership of product direction and high-risk approvals
- Specialized agents with narrowly scoped responsibilities
- No agent approves its own work
- GitHub is the authoritative system of record
- Every change starts with a traceable issue
- Every change is built in an isolated branch or worktree
- Independent CI validates all agent claims
- Preview and staging deployments precede production
- Least-privilege credentials and complete audit logging
- Repeated failures escalate instead of looping indefinitely

## Supported platform

Devsembly currently requires a **Development Host** running a supported Ubuntu LTS release. Ubuntu is the only host operating system currently built, tested, and supported by the project.

A Development Host may run on any compatible infrastructure provider. Vultr is the first documented and tested provider, but provider-specific assumptions should remain outside the core application and installer wherever practical.

Most Devsembly application services run in Docker containers. Host operating-system differences primarily affect provisioning, package installation, Docker setup, users and permissions, firewall configuration, service management, and first-boot automation.

See [`docs/platform-support.md`](docs/platform-support.md) for the support policy and terminology.

## Platform components

| Component | Responsibility |
|---|---|
| OpenClaw | Conversational task intake and orchestration |
| Archon | Deterministic workflow execution and gates |
| Claude Code | Architecture, implementation, refactoring, documentation |
| OpenAI Codex | Implementation, debugging, testing, independent review |
| GitHub | Issues, source, branches, pull requests, releases and audit trail |
| GitHub Actions | Independent quality and security gates |
| Coolify | Preview, staging and controlled production deployment |
| code-server | Browser-accessible development environment |
| Playwright | End-to-end browser testing |
| Testcontainers | Real integration-test infrastructure |
| Trivy, Semgrep, Gitleaks | Security and secret scanning |
| OpenTelemetry, Sentry, Grafana | Observability and diagnostics |

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

This repository currently contains the product foundation, workflow specifications, agent role contracts, infrastructure blueprint, security model, and initial CI scaffolding. Application services will be added incrementally through reviewed pull requests.

## Getting started

1. Review the supported-host requirements in [`docs/platform-support.md`](docs/platform-support.md).
2. Read [`docs/vision/product-vision.md`](docs/vision/product-vision.md).
3. Review [`docs/architecture/system-architecture.md`](docs/architecture/system-architecture.md).
4. Review [`docs/security/trust-model.md`](docs/security/trust-model.md).
5. Start with the roadmap in [`docs/vision/roadmap.md`](docs/vision/roadmap.md).
6. Use the issue templates to propose work.

## License

No open-source license has been selected yet. Until one is added, all rights are reserved.

## Wiki and operating documentation

A full version-controlled wiki source is included under [`wiki/`](wiki/). It covers Development Host provisioning, browser access, GitHub, OpenClaw, Archon, Coolify, agent workflows, security, backups, monitoring, daily operations, releases, and troubleshooting.

Provider-specific instructions belong in dedicated provider guides. Shared documentation should refer to the Development Host rather than a particular cloud vendor or VM product unless the provider detail is technically necessary.