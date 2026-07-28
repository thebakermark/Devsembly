# Platform overview

Devsembly coordinates specialized AI agents and conventional engineering tools to reproduce the controls and responsibilities of a large software organization.

## Component responsibilities

| Component | Responsibility |
|---|---|
| OpenClaw | Conversational task intake and orchestration |
| Archon | Repeatable, gated development workflows |
| Claude Code | Architecture, repository analysis, implementation, and documentation |
| OpenAI Codex | Focused implementation, debugging, tests, and independent review |
| GitHub | Issues, code, branches, pull requests, releases, and audit history |
| GitHub Actions | Independent build, test, and security gates |
| Coolify | Preview, staging, and approved production deployment |
| code-server | Browser-based manual development environment |
| Playwright | End-to-end browser testing |
| Testcontainers | Temporary realistic integration-test services |
| Trivy, Semgrep, Gitleaks | Vulnerability, code-pattern, and secret scanning |
| OpenTelemetry and Grafana | Logs, metrics, traces, and operational visibility |

## Agent hierarchy

The platform uses persistent lead agents for product, architecture, engineering, quality, security, platform, documentation, and orchestration. Temporary specialist agents are created for each task and work in isolated Git worktrees.
