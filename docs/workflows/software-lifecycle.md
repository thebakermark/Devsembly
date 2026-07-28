# Automated Software Lifecycle

## 1. Idea intake

OpenClaw records the request and creates or links a GitHub initiative. Product agents define the problem, users, expected outcome and success measures.

## 2. Requirements

Business and requirements agents produce user stories, acceptance criteria, constraints, edge cases and explicit out-of-scope items.

## 3. Architecture

Architecture agents produce the technical design, data model, API contracts, threat model, deployment impact and architecture decisions. An independent architecture reviewer challenges the design.

## 4. Planning

The Engineering Director decomposes the approved design into dependency-aware GitHub issues and selects the appropriate agent and workflow for each task.

## 5. Implementation

Temporary coding agents work in separate branches and worktrees. Parallel work is permitted only when file and dependency conflicts are controlled.

## 6. Local validation

Formatting, linting, type checks, unit tests, integration tests, migration checks, container builds, secret scans and static security scans run before a pull request.

## 7. Independent review

Separate agents review code, architecture, tests, security and documentation. Must-fix findings return the task to implementation.

## 8. Pull request and CI

A draft pull request includes requirements, design references, test evidence, security results, screenshots, deployment notes and rollback instructions. GitHub Actions reruns checks from a clean environment.

## 9. Preview

Coolify deploys a disposable pull-request environment. Browser, accessibility, smoke and API tests run against the deployed system.

## 10. Approval and staging

A release-readiness agent assembles the evidence. Human approval permits merge and staging promotion.

## 11. Production

A release agent prepares notes, version, backup confirmation and rollback point. Production promotion requires explicit authorization.

## 12. Monitoring and learning

Observability and incident agents detect regressions. Retrospectives update workflows, standards, tests and agent instructions.
