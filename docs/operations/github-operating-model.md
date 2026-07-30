# GitHub Operating Model

GitHub is the system of record for Devsembly product development.

## Work hierarchy

1. **Project** — ongoing program and portfolio view.
2. **Milestone** — release or delivery phase.
3. **Parent issue** — major capability or epic.
4. **Sub-issue** — implementable unit of work.
5. **Pull request** — proposed repository change linked to an issue.
6. **Actions** — validation, automation, release, and deployment.

## Standard statuses

- Backlog
- Ready
- In progress
- Review
- Blocked
- Done

## Recommended project fields

- Priority: Critical, High, Medium, Low
- Work type: Feature, Bug, Architecture, Security, Documentation, Operations
- Phase: Genesis, Control Plane, Agent Factory, CompanyOS
- Effort: XS, S, M, L, XL
- Risk: Low, Medium, High
- Agent suitability: Agent-ready, Agent-assisted, Human-only
- Target release
- Environment

## Workflow

1. Capture an idea in Discussions or as an issue.
2. Triage it and define a measurable outcome.
3. Add it to the project and milestone.
4. Break large work into sub-issues and record blockers.
5. Mark suitable work `agent-ready` only after acceptance criteria and dependencies are clear.
6. Implement on a branch and open a pull request that closes the issue.
7. Require CI and human review before merge.
8. Release through a version tag and generated GitHub Release.

## Labels

Recommended labels:

- `status:triage`
- `status:ready`
- `status:blocked`
- `type:feature`
- `type:bug`
- `type:architecture`
- `type:security`
- `type:documentation`
- `agent-ready`
- `agent-assisted`
- `human-only`
- `dependencies`

## Governance rules

- Pull requests must identify linked work and validation performed.
- Agent-generated changes require human review.
- Secrets and production data must never enter issues, logs, commits, or pull requests.
- Documentation and structured schemas receive automated validation.
- Releases use semantic version tags such as `v1.0.0-rc1` and `v1.0.0`.
