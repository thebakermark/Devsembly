# Devsembly Genesis Reference Implementation Plan

**Version:** 0.1  
**Status:** Proposed implementation baseline  
**Target:** First deployable, end-to-end Devsembly reference implementation

## 1. Purpose

This plan converts the Devsembly architecture and roadmap into the smallest working release that proves the platform can accept an objective, apply organizational and budget constraints, plan work, execute a controlled software change, validate the result, and preserve the decision trail.

Genesis v0.1 is not a complete enterprise platform. It is the first coherent vertical slice of the Devsembly operating model.

## 2. Release mission

Genesis v0.1 must demonstrate this workflow:

```text
Create organization
  -> create initiative
  -> assign monthly budget
  -> capture objective and acceptance criteria
  -> generate a governed implementation plan
  -> create traceable source-control work
  -> execute a small software change
  -> run independent validation
  -> produce a pull request
  -> record cost, evidence, decisions, and outcome
```

A release is successful only when this path works end to end on a supported Development Host.

## 3. Scope

### 3.1 Mandatory capabilities

| Capability | Minimum v0.1 behavior |
|---|---|
| Organization registry | Create and retrieve one organization with mission, owner, policies, and active status |
| Initiative registry | Create an initiative linked to an organization with objective, priority, status, sponsor, and success criteria |
| Project registry | Link one or more repositories and execution targets to an initiative |
| Budget profile | Set monthly, one-time, AI, and infrastructure limits; report remaining and forecasted spend |
| Decision record | Store context, options, selected action, cost impact, risk, confidence, approver, and outcome |
| Agent registry | Register named agents with role, permissions, authority level, provider, and status |
| Governed workflow | Execute a durable workflow with explicit stages, retries, approval gates, and escalation |
| Source-control integration | Create or link a work item, branch, commit, pull request, and CI evidence |
| Validation | Run deterministic checks independently from the implementation agent |
| Memory and knowledge | Persist project context, decisions, evidence, summaries, and lessons in a searchable store |
| Audit events | Record who or what performed each meaningful action and when |
| Operator view | Show initiative status, budget health, workflow stage, approvals, evidence, and failures |

### 3.2 Budget-aware behavior

A project can be initialized with a constraint such as `$50/month`. The platform must:

1. Store the declared limit and allowed flexibility.
2. Estimate the monthly cost of recommended infrastructure, AI providers, and external services.
3. Reject or escalate a plan that exceeds the approved limit.
4. Offer a lower-cost alternative when one satisfies the acceptance criteria.
5. Reforecast when usage or project maturity changes.
6. preserve the rationale behind every budget recommendation.

### 3.3 First proof workflow

The first supported workload will be a small repository change, such as adding a documented API endpoint or correcting a validated defect. It must be large enough to exercise planning, implementation, testing, review, and documentation, but small enough to complete within one governed workflow run.

## 4. Explicitly deferred

The following are outside Genesis v0.1 unless required to complete the proof workflow:

- CompanyOS business modules
- Marketplace and third-party plugin distribution
- Multi-region or active-active deployment
- Kubernetes
- Enterprise SSO and SCIM
- Full accounting, CRM, HR, fleet, dispatch, or ERP capabilities
- Autonomous production releases without human approval
- Custom foundation models
- General-purpose knowledge graph infrastructure
- Complex chargeback and revenue recognition
- Native mobile applications
- Large-scale multi-tenant isolation

Deferred work remains visible in the roadmap but must not delay the reference implementation.

## 5. Adopt, build, and evaluate

| Area | v0.1 decision | Rationale |
|---|---|---|
| PostgreSQL | Adopt | Authoritative structured state, audit records, and workflow metadata |
| Redis | Adopt where required | Queueing, locks, and ephemeral coordination; avoid using it as durable truth |
| MinIO or compatible object storage | Adopt | Artifacts, logs, evidence bundles, and generated documents |
| Docker Compose | Adopt | Fits the supported single-host development and bootstrap model |
| GitHub | Adopt through provider interface | Initial source-control system of record without coupling the core domain to one vendor |
| Existing workflow engine | Evaluate first | Prefer a proven durable engine over writing a custom scheduler |
| Existing identity provider | Evaluate first | Do not build authentication or secret storage from scratch |
| OpenTelemetry | Adopt incrementally | Common telemetry contract for workflows and services |
| Company Intelligence domain model | Build | Core differentiated organizational context |
| Budget Intelligence | Build | Core differentiated financial constraint and recommendation behavior |
| Decision and approval model | Build | Core governance and explainability capability |
| Agent policy and authority model | Build | Core controlled-autonomy capability |
| General knowledge retrieval | Hybrid | Use proven storage and retrieval components behind Devsembly interfaces |

Every external dependency must be replaceable behind a capability provider interface.

## 6. Reference architecture

Genesis v0.1 should begin as a modular monolith plus workers, not a fleet of microservices.

```text
Operator UI / API
        |
Application Core
  - organizations
  - initiatives
  - projects
  - budgets
  - decisions
  - agents
  - approvals
        |
Workflow Runtime ---- Worker adapters ---- AI/tool providers
        |
PostgreSQL ---- Object storage ---- optional Redis
        |
Source-control provider and validation runners
```

Modules must have explicit interfaces and events so they can be separated later if measured scale or reliability requirements justify it.

## 7. Canonical minimum data model

### Organization

- id
- name
- mission
- owner_id
- status
- default_policy_set_id
- created_at
- updated_at

### Initiative

- id
- organization_id
- name
- objective
- success_criteria
- priority
- lifecycle_state
- sponsor_id
- budget_profile_id
- created_at
- updated_at

### Project

- id
- initiative_id
- name
- repository_provider
- repository_identifier
- default_branch
- execution_environment
- status

### BudgetProfile

- id
- scope_type
- scope_id
- currency
- monthly_limit
- one_time_limit
- ai_limit
- infrastructure_limit
- flexibility_percent
- warning_threshold_percent
- hard_stop_enabled

### CostEntry

- id
- budget_profile_id
- category
- provider
- estimated_amount
- actual_amount
- period_start
- period_end
- source_event_id

### DecisionRecord

- id
- scope_type
- scope_id
- context
- options
- selected_option
- rationale_summary
- estimated_cost
- risk_score
- confidence_score
- approval_state
- outcome
- review_at

### AgentDefinition

- id
- name
- role
- capability_set
- authority_level
- budget_authority
- provider
- active

### WorkflowRun

- id
- initiative_id
- workflow_type
- current_stage
- status
- retry_count
- budget_reserved
- started_at
- completed_at

### Evidence

- id
- workflow_run_id
- evidence_type
- location
- digest
- produced_by
- created_at

## 8. Workflow stages

The Genesis software-change workflow uses these mandatory stages:

1. **Intake** — normalize objective, constraints, and acceptance criteria.
2. **Context** — retrieve organization, project, architecture, policies, and budget.
3. **Plan** — produce tasks, dependencies, estimates, risks, and expected cost.
4. **Budget gate** — approve, optimize, or escalate based on the budget profile.
5. **Human gate** — obtain approval when policy requires it.
6. **Implementation** — make the change in an isolated branch or workspace.
7. **Validation** — run tests, static analysis, security checks, and documentation checks independently.
8. **Review** — compare evidence to acceptance criteria and policy.
9. **Publish** — create or update the pull request and attach evidence.
10. **Learn** — record actual cost, elapsed time, outcome, and reusable lessons.

An implementation agent may not approve its own result.

## 9. Acceptance tests

### Organization and initiative

- A user can create an organization and an initiative through the API or operator interface.
- The initiative cannot enter planning without an objective and success criteria.
- Every initiative is linked to a budget profile and at least one human owner or sponsor.

### Budget Intelligence

- A `$50/month` limit can be configured.
- A recommendation includes estimated one-time and recurring cost.
- A plan over the hard limit is blocked or escalated.
- A compliant lower-cost plan can be generated.
- Actual and forecasted spend are visible by category.
- Changing the limit changes subsequent recommendations without rewriting historical decisions.

### Decision governance

- Every material plan selection creates a decision record.
- Alternatives, financial impact, confidence, risk, approval, and outcome are queryable.
- A denied decision cannot continue to execution.

### Agent governance

- Each execution identifies the acting agent and its authority.
- An agent is blocked from actions outside its permission set.
- Implementation and validation are performed by separate roles.
- Retry limits end in escalation rather than an infinite loop.

### Source-control workflow

- A traceable work item exists before implementation.
- Work occurs on an isolated branch or workspace.
- Commits and pull requests reference the initiative and workflow run.
- Validation evidence is attached or linked.
- The pull request is not represented as approved until the required checks and approvals exist.

### Auditability and recovery

- Meaningful actions produce immutable audit events.
- A failed workflow can resume from the last safe checkpoint.
- Duplicate external side effects are prevented or detected.
- Secrets are never stored in workflow logs or decision records.

### Operator experience

- The operator can see current stage, assigned agents, blockers, approvals, estimated spend, actual spend, and evidence.
- The operator can stop, retry, approve, or reject within granted authority.

## 10. Milestones

### G0 — Baseline locked

- Reference implementation plan approved
- Architecture decisions for application shape, workflow engine, identity, and persistence recorded
- Supported-host bootstrap remains green

### G1 — Domain foundation

- Organization, initiative, project, budget, decision, agent, and audit models
- Database migrations and API contracts
- Unit and integration tests

### G2 — Governed workflow skeleton

- Durable workflow with stages, retries, approvals, and evidence
- Mock implementation and validation agents
- Recovery and idempotency tests

### G3 — Source-control vertical slice

- Real provider adapter
- Work item, branch, commit, pull request, and CI evidence flow
- Independent validation role

### G4 — Budget-aware execution

- Cost estimate contract
- Budget gate
- hard-stop and warning behavior
- monthly forecast and recommendation output

### G5 — Operator control surface

- Initiative and workflow status
- approvals and escalation inbox
- budget and cost view
- audit and evidence view

### G6 — Genesis release candidate

- End-to-end demonstration on a fresh supported host
- Security review
- Backup and recovery test
- Operating runbook
- Known limitations and upgrade notes

## 11. Anti-overengineering constraints

Genesis v0.1 must not introduce the following without a separate approved ADR and measured need:

- Kubernetes or service mesh
- Multi-region architecture
- More than one durable source of truth for core records
- Event sourcing as the default persistence model
- A custom database, queue, workflow scheduler, identity provider, or secret manager
- Separate deployable service for every domain module
- Premature provider abstraction that has no second implementation or clear boundary
- Autonomous production mutation without a human-controlled policy gate
- A generalized ontology intended to model every possible business domain

Prefer direct, testable interfaces and reversible decisions.

## 12. Quality and operational requirements

Every deployable component must provide:

- health and readiness checks
- structured logs with correlation identifiers
- basic metrics for workflow duration, failure, retry, model usage, and cost
- explicit configuration schema
- database migration and rollback guidance
- least-privilege credentials
- dependency and secret scanning
- documented backup and recovery procedure
- deterministic local validation command

## 13. Risks and controls

| Risk | Control |
|---|---|
| Scope expands into CompanyOS | Enforce explicit deferred list and milestone exit criteria |
| Agents claim success without evidence | Independent validation and evidence requirements |
| AI cost becomes unpredictable | Budget reservation, per-run estimates, hard limits, and provider routing |
| Provider lock-in | Capability interfaces around external providers |
| Workflow duplicates external actions | Idempotency keys and checkpointed stages |
| Architecture becomes too abstract | One real vertical slice before adding generality |
| Security is postponed | Identity, secrets, audit, and permissions included from the first workflow |
| Human operator loses control | Configurable approval gates and immediate stop capability |

## 14. Exit criteria

Genesis v0.1 is complete when all of the following are demonstrated on a fresh supported Development Host:

1. An operator creates an organization, initiative, project, and `$50/month` budget profile.
2. The system produces a plan and cost estimate that respects the constraint or clearly escalates it.
3. A human approves the governed plan.
4. An implementation agent completes a small repository change in isolation.
5. A separate validation role produces verifiable evidence.
6. A pull request is created with traceability to the initiative, decisions, workflow run, and evidence.
7. The operator can inspect status, budget, approvals, costs, failures, and audit history.
8. The workflow survives one intentionally injected failure and resumes safely.
9. Actual cost and elapsed time are recorded and compared with the estimate.
10. The runbook allows another operator to reproduce the demonstration.

## 15. First implementation backlog

1. Approve this plan and record its ADR.
2. Select the application framework, durable workflow engine, and identity approach.
3. Define API and event contracts for the canonical minimum data model.
4. Implement domain models, migrations, and policy checks.
5. Implement a mock end-to-end workflow before connecting an AI provider.
6. Add the source-control provider adapter and independent validation runner.
7. Add budget estimation, reservation, hard-stop, and forecast behavior.
8. Add the minimum operator interface.
9. Run the release-candidate demonstration on a clean host.
10. Capture actual results and revise the v0.2 plan from measured evidence.

## 16. Governing rule

No new Genesis capability is accepted merely because it is technically interesting. It must solve a defined problem, fit the current release mission and budget, produce measurable evidence, and justify its ongoing operational cost.
