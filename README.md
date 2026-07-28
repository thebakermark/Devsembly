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

1. Read [`docs/vision/product-vision.md`](docs/vision/product-vision.md).
2. Review [`docs/architecture/system-architecture.md`](docs/architecture/system-architecture.md).
3. Review [`docs/security/trust-model.md`](docs/security/trust-model.md).
4. Start with the roadmap in [`docs/vision/roadmap.md`](docs/vision/roadmap.md).
5. Use the issue templates to propose work.

## License

No open-source license has been selected yet. Until one is added, all rights are reserved.

## Wiki and operating documentation

A full version-controlled wiki source is included under [`wiki/`](wiki/). It covers VM creation, browser access, GitHub, OpenClaw, Archon, Coolify, agent workflows, security, backups, monitoring, daily operations, releases, and troubleshooting. The files are ready to publish to the repository's GitHub Wiki after the new repository is created.
