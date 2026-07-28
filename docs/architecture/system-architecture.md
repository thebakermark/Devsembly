# System Architecture

## Logical architecture

```text
User / Product Owner
        |
        v
OpenClaw Orchestrator
        |
        v
Archon Workflow Engine
        |
        +--> Product and architecture agents
        +--> Claude Code and Codex engineering agents
        +--> QA, security and documentation agents
        |
        v
GitHub issues, branches and pull requests
        |
        v
GitHub Actions independent gates
        |
        v
Coolify preview -> staging -> approved production
```

## Control plane

The control plane coordinates work but does not contain customer-product business logic. It includes orchestration, workflow definitions, agent registry, approvals, audit events and project configuration.

## Execution plane

Coding and test agents operate in isolated Git worktrees or disposable containers. Each task receives only the repository, credentials and tools necessary for that task.

## Delivery plane

GitHub Actions performs independent validation. Coolify manages disposable preview environments, staging and approved production deployments.

## Knowledge plane

Authoritative knowledge is stored in versioned repository documents, issues, architecture decision records, pull requests, test results and release notes. Agent memory is never the sole source of truth.

## Initial deployment topology

- Development control VM: OpenClaw, Archon, browser IDE, coding agents and local test services
- Coolify management VM: deployment control only
- Staging VM: production-like application stack
- Production infrastructure: isolated from all development agents
