# Autonomous Coding Factory

## Purpose

Devsembly is the control plane for an automated software-production organization. It accepts a product goal, converts it into traceable work, delegates that work to specialized AI agents, validates every claim with independent tooling, and safely delivers releases with minimal human interaction.

CompanyOS is the first flagship product produced by the factory, but every product runs through the same governed lifecycle.

## Operating target

The factory should autonomously perform the routine portions of:

1. Product discovery and specification
2. Repository and architecture analysis
3. Backlog generation and dependency planning
4. Implementation in isolated branches or worktrees
5. Unit, integration, browser and security testing
6. Code review and repair loops
7. Pull-request preparation and CI remediation
8. Preview and staging deployment
9. Release notes, documentation and operational handoff
10. Production monitoring, incident triage and improvement proposals

Humans define business intent, budgets, policy and risk tolerance. Humans approve irreversible, expensive, legally sensitive, security-sensitive or production-impacting actions.

## Factory architecture

```text
Human / API / CompanyOS Idea Inbox
                |
                v
        Intake & Clarification Agent
                |
                v
        Product Manager Agent
                |
                v
      Architecture & Security Council
                |
                v
     Planner / Dependency Graph Builder
                |
                v
       Workflow Orchestrator + Event Bus
         /        |         |        \
        v         v         v         v
 Researcher   Builder A  Builder B  Data Agent
        \         |         |         /
         \        v         v        /
          ---> Validation Pipeline <---
          lint / test / e2e / security
                     |
                     v
         Independent Reviewer Council
                     |
               repair or approve
                     |
                     v
              GitHub Pull Request
                     |
                     v
          Preview -> Staging -> Release
                     |
                     v
       Observability / Incident / Learning
```

## Major services

### 1. Factory API

The canonical interface for product goals, jobs, runs, approvals, artifacts and status. All user interfaces and agents communicate through this API instead of directly mutating factory state.

### 2. Workflow orchestrator

Executes versioned workflow definitions as durable state machines. It owns retries, timeouts, budgets, concurrency, compensation steps and escalation. Agent chat history is not workflow state.

Recommended implementation:

- Temporal for durable execution, retries and long-running workflows
- PostgreSQL for product, job, run, approval and audit records
- NATS JetStream for event distribution
- Redis only for cache, rate limiting and ephemeral locks

### 3. Agent gateway

Provides a single provider-neutral interface to Claude Code, OpenAI Codex and future models. It applies role prompts, repository permissions, budgets, tool policies, context packages and structured output schemas.

### 4. Workspace manager

Creates disposable workspaces per task using Git worktrees or short-lived containers. Each workspace receives only the repository, secrets and network access needed for its assigned task.

### 5. Validation service

Runs deterministic quality gates outside the agent process. Agents may request validation, but cannot mark their own work successful.

Required gates:

- formatting and linting
- type checking
- unit tests
- integration tests with Testcontainers
- Playwright browser tests
- dependency and container scanning
- secret scanning
- policy checks
- migration safety checks
- build and packaging verification

### 6. Review council

Uses separate agents and deterministic evidence to review implementation, tests, security, architecture and documentation. A builder never approves its own work.

### 7. Deployment controller

Creates preview environments for pull requests, promotes approved builds to staging and executes controlled production releases. Production deploys consume immutable artifacts previously validated in CI.

### 8. Observability and learning service

Collects traces, logs, metrics, test results, deployment health and incident data. It can automatically open improvement issues, but it may not silently rewrite production systems.

## Agent roles

| Role | Responsibility | May write code | May approve own work |
|---|---|---:|---:|
| Intake | Normalize ideas and identify missing requirements | No | No |
| Product Manager | PRD, stories, acceptance criteria and priorities | Docs only | No |
| Researcher | Discover standards, dependencies and prior art | No | No |
| Architect | System design, interfaces and ADRs | Docs/scaffolds | No |
| Security Architect | Threat model, controls and policy gates | Docs/policy | No |
| Planner | Dependency graph and executable task packets | No | No |
| Builder | Implement one bounded task | Yes | No |
| Test Engineer | Create and strengthen automated tests | Tests | No |
| Reviewer | Review changes against evidence and requirements | Suggested fixes | No |
| Release Manager | Prepare release evidence and promotion request | Release files | No |
| SRE | Diagnose incidents and propose or execute reversible remediation | Limited | No |
| Documentation Agent | User, developer and operations documentation | Docs | No |

## Autonomous product lifecycle

### Stage 0: Intake

Input may be a sentence, voice transcript, uploaded document, GitHub issue or CompanyOS product request.

Output:

- normalized product goal
- constraints and assumptions
- success metrics
- risk classification
- required human decisions

The factory proceeds automatically when ambiguity is low. When ambiguity materially changes cost, safety or product behavior, it creates one consolidated approval request rather than repeatedly interrupting the user.

### Stage 1: Product definition

The Product Manager creates:

- product requirements document
- personas and jobs-to-be-done
- functional and non-functional requirements
- acceptance criteria
- out-of-scope list
- initial release slices

A critic agent checks completeness and internal consistency.

### Stage 2: Architecture and security

The architecture council produces:

- system context and component diagrams
- data model
- API contracts
- deployment topology
- architecture decision records
- threat model and trust boundaries
- privacy and compliance classification
- test strategy

Changes conflicting with existing ADRs require an explicit replacement ADR.

### Stage 3: Planning

The planner converts approved requirements into a directed acyclic graph of task packets. Every task packet contains:

- objective
- repository and permitted paths
- dependencies
- acceptance tests
- commands to validate
- risk and budget limits
- required artifacts
- rollback expectations

Tasks with no write overlap may execute in parallel.

### Stage 4: Implementation

The workspace manager creates one isolated branch/worktree per task. The builder receives a minimal context package and implements only the declared scope.

The builder must return structured evidence:

- files changed
- commands executed
- test results
- assumptions
- unresolved risks
- suggested follow-up tasks

### Stage 5: Deterministic validation

The validation service independently runs repository-defined checks. Failure creates a bounded repair loop with the original builder or a debugging specialist.

Default limits:

- maximum three repair attempts per failure class
- maximum task cost and token budget
- maximum wall-clock deadline
- no repeated attempt without a changed hypothesis

Exceeding limits creates an escalation artifact with logs, likely cause and recommended human decision.

### Stage 6: Independent review

At minimum, one reviewer checks correctness and one reviewer checks security/test adequacy for medium-risk changes. Review comments become structured repair tasks. Reviewer approval never substitutes for deterministic CI.

### Stage 7: Pull request and preview

The factory creates a pull request containing:

- requirement and issue links
- implementation summary
- architecture/security impact
- test evidence
- screenshots or recordings for UI changes
- deployment and rollback notes
- machine-readable run manifest

A preview deployment is created automatically when supported.

### Stage 8: Promotion

Low-risk changes may auto-merge after all policies pass. Medium-risk changes require a batched human approval. High-risk changes require explicit approval at both merge and production promotion.

### Stage 9: Operations and learning

After deployment, the factory observes service health against release-specific success criteria. Regressions trigger rollback or a guarded remediation workflow according to policy. Retrospectives create reusable knowledge, tests and backlog items.

## Human interaction policy

### Fully autonomous

- documentation corrections
- dependency patch updates passing all gates
- tests and coverage improvements
- isolated low-risk bug fixes
- preview deployments
- issue decomposition and planning
- reversible development-environment maintenance

### Batched approval

- new product scope
- architecture changes
- schema migrations
- monthly provider spending above budget
- staging promotion for medium-risk changes
- enabling new third-party integrations

### Explicit approval every time

- production database destructive operations
- production secrets or identity changes
- legal, payroll, accounting or regulated workflows
- security policy reductions
- sending external communications as the company
- production release classified high risk
- irreversible infrastructure deletion

## Safety and control model

- Deny-by-default tool access
- Per-agent service identities
- Short-lived credentials
- Repository path allowlists
- Network egress allowlists
- Signed workflow definitions
- Immutable audit events
- Secret redaction before model calls
- Cost and token budgets by product and task
- Kill switch for product, workflow, agent provider and global factory
- No self-approval
- No direct agent writes to protected branches
- No production access from builder workspaces

## CompanyOS integration

CompanyOS should expose a Product Studio module backed by the Factory API. A business owner can describe a desired application or module, attach policies and data examples, select a budget/risk profile and follow progress through:

- Ideas
- Product briefs
- Active initiatives
- Work graph
- Agent runs
- Approvals
- Pull requests
- Environments
- Releases
- Incidents
- Cost and performance analytics

This creates a commercial path where CompanyOS customers can operate their own governed software factory, use a managed shared factory, or purchase prebuilt industry modules from a marketplace.

## Initial implementation slices

### Slice 1: Executable control-plane skeleton

- Factory API service
- PostgreSQL schema
- workflow/job/run/approval models
- event contracts
- mock agent provider
- local Docker Compose
- health checks and tests

### Slice 2: GitHub-native task execution

- issue intake
- branch/worktree creation
- task packet generation
- patch capture
- pull-request creation
- CI result ingestion

### Slice 3: Multi-provider agent gateway

- Claude Code adapter
- Codex adapter
- policy and budget enforcement
- structured outputs
- context packaging

### Slice 4: Validation and review council

- validation runners
- evidence store
- bounded repair loops
- independent reviews
- risk-based merge policy

### Slice 5: Deployment and operations

- Coolify previews
- staging promotion
- release manifests
- telemetry and incident workflows
- automated rollback policy

### Slice 6: CompanyOS Product Studio

- product intake UI
- workflow visualization
- approvals inbox
- run and cost explorer
- release and incident center

## Definition of factory-ready

The factory is ready for an internal pilot when one authorized user can submit a bounded feature request and the system can, without manual command execution:

1. Create a requirements artifact and task graph
2. Open traceable GitHub issues
3. Execute one or more isolated implementation tasks
4. Run deterministic tests and security checks
5. Repair bounded failures
6. Obtain independent review
7. Open a complete pull request
8. Deploy a preview environment
9. Request only the policy-required approval
10. Preserve an auditable record of prompts, decisions, evidence, costs and artifacts
