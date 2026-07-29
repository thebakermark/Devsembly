# Autonomous Coding Factory Delivery Roadmap

## Goal

Deliver a production-grade Devsembly control plane that can take an authorized product request from idea through reviewed pull request and preview deployment with minimal human interaction.

## Phase 1 — Control-plane foundation

### Outcomes

- Product, initiative, workflow, task, run, artifact, approval and audit models
- Factory API with authenticated CRUD and status endpoints
- PostgreSQL persistence and migrations
- Durable workflow runner abstraction
- Mock agent adapter for deterministic development and testing
- Local Docker Compose environment
- Structured logs, health endpoints and baseline telemetry

### Exit criteria

- A sample request can create a workflow run and task graph
- Tasks transition through valid states only
- Every state transition creates an audit event
- Retry, timeout and cancellation behavior is covered by tests
- The stack starts through one documented command

## Phase 2 — GitHub execution loop

### Outcomes

- GitHub issue intake and traceability
- Repository checkout and isolated worktree lifecycle
- Task packet generation and schema validation
- Branch naming and path-policy enforcement
- Patch and evidence collection
- Pull-request creation with generated run manifest
- GitHub Actions status ingestion

### Exit criteria

- A bounded task submitted through the API produces an isolated branch
- The mock agent can modify an allowed fixture repository
- Forbidden paths are rejected
- Validation evidence is attached to the run
- A complete draft pull request is generated automatically

## Phase 3 — Real agent gateway

### Outcomes

- Claude Code adapter
- OpenAI Codex adapter
- Provider routing by task type, budget and availability
- Model/tool policy enforcement
- Context packaging and redaction
- Structured agent result validation
- Token, duration and cost accounting

### Exit criteria

- Either provider can execute the same task contract
- Malformed agent output cannot advance workflow state
- Spending limits stop work predictably
- Provider failure can route to an approved fallback
- Secrets are excluded or redacted from model context

## Phase 4 — Validation and review council

### Outcomes

- Containerized validation runners
- Unit, integration, E2E and security gate plugins
- Evidence normalization
- Bounded repair workflow
- Correctness, testing, architecture and security reviewers
- Risk-based approval policy

### Exit criteria

- Failed validation creates a targeted repair task
- A repeated failure with no new hypothesis escalates
- Builders cannot approve their own work
- CI remains authoritative over agent claims
- Low-risk fixture changes can pass end to end without intervention

## Phase 5 — Preview, staging and release

### Outcomes

- Coolify preview-environment integration
- Preview URLs and deployment evidence attached to pull requests
- Staging promotion workflows
- Immutable release manifests
- Rollback and health-verification workflows
- Release notes and documentation generation

### Exit criteria

- A successful pull request receives a preview deployment
- Failed health verification blocks promotion
- Staging uses the same immutable build artifact as preview
- Production promotion follows configured approval policy
- Rollback is tested and auditable

## Phase 6 — CompanyOS Product Studio

### Outcomes

- Idea and product-request inbox
- PRD and acceptance-criteria review
- Work-graph visualization
- Agent run timeline
- Consolidated approvals inbox
- Cost, quality and cycle-time analytics
- Environment, release and incident views
- Factory templates for CompanyOS modules

### Exit criteria

- A non-developer can submit and track a product request from one interface
- Questions are consolidated instead of repeatedly interrupting the user
- Every approval displays impact, evidence and rollback information
- The user can pause or terminate any active run

## Phase 7 — Self-improving operations

### Outcomes

- Production telemetry analysis
- Incident classification and guarded remediation
- Automatic regression-test proposals
- Workflow performance analytics
- Prompt, agent and model evaluation harness
- Reusable organizational knowledge packages

### Exit criteria

- Incidents produce traceable diagnosis and remediation proposals
- Safe reversible responses may execute under policy
- Risky actions always require approval
- Factory changes are evaluated against historical benchmark tasks
- Improvement proposals include measurable expected benefit

## Recommended first implementation epic

**Epic: Factory Control Plane MVP**

Build a vertical slice that accepts one product request, generates one task packet, runs a mock builder, independently validates a fixture change, records evidence and opens a draft pull request.

Suggested work items:

1. Define domain model and database migrations
2. Scaffold Factory API
3. Implement workflow state machine
4. Implement task-packet validation
5. Implement audit event store
6. Implement mock agent provider
7. Implement disposable workspace manager
8. Implement command validation runner
9. Implement GitHub issue/branch/PR adapter
10. Build end-to-end fixture test
11. Add Docker Compose and one-command bootstrap
12. Add operator documentation and recovery procedures

## Metrics

Track from the first pilot:

- idea-to-PR cycle time
- autonomous completion rate
- first-pass validation rate
- repair attempts per task
- escaped defects
- human interruptions per initiative
- cost per accepted change
- rollback frequency
- mean time to diagnose and recover
- percentage of evidence-backed agent claims
