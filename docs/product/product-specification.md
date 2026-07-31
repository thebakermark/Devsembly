# Devsembly Product Specification

**Status:** Draft v1.0  
**Canonical project:** `project:devsembly`  
**Repository:** `thebakermark/Devsembly`  
**Canonical machine-readable source:** `.devsembly/project-state.json`  
**Document role:** Human-readable product projection

> This document explains what Devsembly is, why it exists, who it serves, and the product boundaries that govern its development. It must remain aligned with `.devsembly/project-state.json`, accepted architecture decision records, and the Genesis Constitution. Stable technical identifiers must be used independently of changeable product and release names.

## 1. Executive summary

Devsembly is a governed, AI-native software delivery platform that converts business intent into secure, testable, documented, and operable software systems. It combines a persistent project intelligence layer, an orchestrated AI workforce, durable workflows, software-development tooling, evidence-backed validation, cost governance, and human approval controls.

Devsembly is designed to solve a central weakness in current AI-assisted development: models, chats, coding agents, issue trackers, repositories, and workflow systems each hold fragments of project knowledge, but no single governed system maintains the complete, durable truth of the project. Context is repeatedly lost, documentation drifts, decisions become difficult to trace, and AI agents can act without an authoritative understanding of priorities, constraints, dependencies, or prior work.

Devsembly addresses this by making the Project Intelligence Engine, or PIE, the canonical project brain. GitHub, model providers, Temporal, documentation, dashboards, and future integrations are synchronized providers, execution systems, or projections of that intelligence. They do not independently own project truth.

The platform’s first runtime and reference implementation is currently displayed as **Genesis**. The broader enterprise platform is currently displayed as **CompanyOS**. These names are branding and release-layer concerns. The underlying architecture uses stable identifiers and industry-standard technical terms so products can be renamed without breaking code, data, interfaces, documentation, or integrations.

## 2. Product definition

### 2.1 General description

Devsembly is an AI-first software factory and project operating system. It plans, builds, validates, documents, governs, and continuously understands software projects through coordinated AI agents and durable project state.

### 2.2 Plain-language description

A user describes what they want to build, the constraints they must work within, and the outcome they need. Devsembly turns that intent into an organized body of work, coordinates specialized AI agents and development tools, tracks decisions and evidence, validates results, and keeps the project’s knowledge current across sessions and systems.

### 2.3 High-level technical description

Devsembly is a provider-neutral enterprise AI development platform composed of:

- a canonical Project Intelligence Engine;
- a multi-agent orchestration and runtime layer;
- durable workflow orchestration;
- a governed tool and capability registry;
- project memory and context management;
- source-control and work-management synchronization;
- identity, authorization, policy, and approval controls;
- audit, provenance, evidence, and validation systems;
- token, cost, budget, risk, and technical-debt governance;
- observability, forecasting, and executive reporting.

## 3. Vision

Create an AI Work Operating System that allows a person, team, or enterprise to move from intent to production software through a durable, governed, and increasingly autonomous delivery process.

The long-term vision is not merely to make coding faster. It is to create a reusable operating model for AI-assisted work in which projects retain memory, agents understand their authority, workflows recover safely, decisions are explainable, costs remain controlled, and every important output can be traced to evidence.

## 4. Mission

Devsembly’s mission is to make enterprise-grade software creation accessible, repeatable, auditable, and economically sustainable by combining AI labor with disciplined engineering and governance.

## 5. Product philosophy

### 5.1 One canonical truth, many views

Project knowledge is maintained as canonical, schema-versioned state. Product briefs, architecture summaries, roadmaps, dashboards, agent context, and other views are projections of that state rather than independent sources that silently drift.

### 5.2 AI proposes and executes within governed authority

AI agents may reason, recommend, generate, test, reconcile, and execute, but their authority is explicit. Material decisions, sensitive actions, budget exceptions, security changes, and production release actions can require human approval.

### 5.3 Durable systems over conversational memory

Chat history is not the project database. Important facts, decisions, provenance, validation evidence, risks, and work state must be persisted in structured systems.

### 5.4 Provider neutrality

GitHub, model vendors, cloud providers, workflow engines, issue trackers, and knowledge systems are replaceable providers behind stable contracts. Devsembly must not make the project dependent on one vendor’s proprietary representation of truth.

### 5.5 Evidence before confidence

Confidence, completion status, and recommendations must be linked to evidence, provenance, validation, and known uncertainty. The system must distinguish verified, inferred, and disputed assertions.

### 5.6 Incremental autonomy

Devsembly should earn autonomy through validation and operational history. New projects and capabilities may begin with close human supervision and progressively automate low-risk work as policies, tests, and evidence mature.

### 5.7 Cost is an architectural constraint

Token usage, model cost, infrastructure expense, and operating budgets are first-class product concerns. The platform must be capable of operating under explicit monthly budget limits and recommending compliant lower-cost alternatives.

### 5.8 Stable identifiers, changeable names

Internal IDs, event names, schemas, APIs, and persisted relationships use stable technical identifiers. Display names, product names, release names, and marketing language are configuration-driven and may change without data migration or widespread code edits.

## 6. Target users

Devsembly is intended for:

- founders and business leaders who need software but do not want to manage a conventional engineering organization;
- product and technology executives who need reliable visibility across AI-assisted delivery;
- software teams adopting coding agents without sacrificing governance or traceability;
- enterprises building internal AI development platforms or agent factories;
- consultants, agencies, and managed-service providers operating multiple client projects;
- future CompanyOS applications that need a shared project intelligence and delivery foundation.

## 7. Problems solved

Devsembly addresses the following problems:

1. **Context loss:** AI tools forget project history, repeat work, and make inconsistent decisions.
2. **Fragmented truth:** repositories, tickets, documents, chats, and dashboards disagree.
3. **Uncoordinated agents:** multiple agents act without shared priorities, dependencies, or authority.
4. **Documentation drift:** architecture, roadmaps, and status reports become outdated.
5. **Weak governance:** AI-generated changes may lack identity, approval, audit, or policy enforcement.
6. **Unreliable execution:** workflows fail midway, duplicate work, or cannot recover safely.
7. **Opaque progress:** completion claims are not consistently tied to tests and evidence.
8. **Uncontrolled cost:** token, model, infrastructure, and labor-equivalent costs are difficult to forecast.
9. **Vendor lock-in:** project knowledge becomes trapped in a single model, tracker, or cloud platform.
10. **High operating burden:** users must repeatedly direct tools, transfer context, and determine the next step manually.

## 8. Core capabilities

### 8.1 Project Intelligence Engine

PIE is the canonical intelligence and shared project-state layer. It maintains versioned project truth, provenance, work hierarchy, capability and dependency graphs, validation state, risks, technical debt, budgets, recommendations, forecasts, and synchronized provider identities.

### 8.2 AI workforce orchestration

Devsembly coordinates specialized agents with defined roles, scopes, capabilities, context, permissions, budgets, and escalation rules. Agents operate as governed workers rather than independent chat sessions.

### 8.3 Workflow orchestration

Durable workflows coordinate long-running work, retries, cancellation, approvals, provider execution, and recovery after interruption. Workflow intent is persisted before external execution begins.

### 8.4 Tool and capability registry

Tools, models, connectors, skills, agents, and reusable workflows are registered as discoverable capabilities with stable contracts, permissions, health state, cost characteristics, and compatibility metadata.

### 8.5 Memory and context management

The memory layer retrieves the smallest relevant, authorized, and current context for each task. It distinguishes canonical facts from historical records, inferred knowledge, transient conversation, and external provider data.

### 8.6 Repository and provider synchronization

Devsembly synchronizes with GitHub and future providers using stable external identifiers, event ordering, idempotency, freshness tracking, conflict detection, and governed reconciliation. External systems remain synchronized projections or providers, not the canonical project brain.

### 8.7 Validation and evidence

Tests, CI runs, reviews, artifacts, approvals, deployment results, and other evidence are linked to requirements, work items, capabilities, and claims. Validation state is derived from evidence rather than manually asserted.

### 8.8 Identity, authorization, and governance

Human and machine identities are distinct. Organization membership, roles, delegations, policies, approvals, audit records, and decision provenance determine what each actor may do.

### 8.9 Cost and budget governance

The platform tracks estimated and actual AI usage, token consumption, infrastructure cost, budget status, and decision records. Policies may observe, warn, require approval, recommend alternatives, or block work.

### 8.10 Risk and technical-debt management

Risks and technical debt are represented as structured, attributable project entities connected to affected capabilities, work items, evidence, mitigations, owners, and status.

### 8.11 Recommendations and forecasting

PIE generates recommended next work, confidence assessments, completion forecasts, budget projections, and executive summaries using canonical state and evidence. Recommendations must explain their basis and uncertainty.

### 8.12 Observability and operational control

The operator surface exposes workflow health, agent activity, provider status, queues, failures, budgets, risks, approvals, evidence, and recovery actions without requiring direct database or infrastructure access.

## 9. Product architecture

At a high level, Devsembly follows a layered architecture:

1. **Experience layer** — user interfaces, APIs, dashboards, CLI, and future conversational interfaces.
2. **Project intelligence layer** — canonical state, provenance, projections, memory, recommendations, and forecasts.
3. **Governance layer** — identity, authorization, policy, approvals, budget controls, audit, and evidence.
4. **Orchestration layer** — workflows, agents, task routing, retries, scheduling, and recovery.
5. **Capability layer** — tools, models, connectors, skills, provider adapters, and execution environments.
6. **Data and infrastructure layer** — relational persistence, object storage, event publication, caches, secrets, telemetry, and deployment infrastructure.

The accepted reference implementation uses a Python and FastAPI modular monolith with PostgreSQL, Temporal, MinIO, Redis, external OIDC, transactional outbox publication, and provider-neutral boundaries. This implementation choice does not change the product definition and may evolve through accepted architecture decisions.

## 10. Product hierarchy and naming model

The current product hierarchy is:

- **Devsembly** — the AI-native software delivery platform and software factory.
- **Genesis** — the current display name for the reference runtime and foundational implementation.
- **Project Intelligence Engine (PIE)** — the canonical project intelligence capability.
- **CompanyOS** — the current display name for the broader enterprise AI operating platform and family of applications built using Devsembly.

These are display names, not permanent architectural identifiers. Code and data should use stable identifiers such as:

- `platform:software-delivery`
- `runtime:reference`
- `capability:project-intelligence`
- `platform:enterprise-ai`

Brand configuration may map those identifiers to Devsembly, Genesis, PIE, CompanyOS, or future names.

## 11. Industry-standard terminology

Devsembly uses common technical terms when they accurately describe a capability:

| Stable capability | Preferred industry term |
| --- | --- |
| Coordinating specialized AI workers | Multi-agent orchestration |
| Running agent and model work | Agent runtime |
| Coordinating durable multi-step execution | Workflow orchestration |
| Registered integrations and executable functions | Tool or capability registry |
| Selecting and assembling relevant information | Context management |
| Persistent reusable project knowledge | Long-term memory and knowledge layer |
| Connected project entities and relationships | Knowledge, capability, and dependency graphs |
| Rules, approval, identity, and authorization | Governance and policy enforcement |
| Logs, metrics, traces, health, and cost signals | Observability and telemetry |
| Provider synchronization and correction | Reconciliation |
| Proof supporting project claims | Evidence and provenance |

Branded names may be used for market positioning, but product documentation must also state the corresponding technical category.

## 12. Primary product workflow

The foundational end-to-end workflow is:

1. Capture business intent and constraints.
2. Convert intent into structured requirements and canonical project state.
3. Identify capabilities, dependencies, risks, budget, and required approvals.
4. Produce a dependency-aware roadmap and recommended next work.
5. Create or synchronize work items with the selected provider.
6. Assign governed agents, tools, and workflows.
7. Persist workflow intent and dispatch durable execution.
8. Generate code, migrations, tests, documentation, and operational artifacts.
9. Validate the work and attach evidence.
10. Reconcile repository and provider changes into canonical state.
11. Update risks, technical debt, cost, confidence, and completion forecasts.
12. Present the result for approval, release, or the next work cycle.

## 13. What Devsembly is not

Devsembly is not:

- merely a chatbot;
- merely a code-generation model or IDE extension;
- merely an issue tracker or project-management dashboard;
- a collection of independent agents with no shared authority;
- a replacement for source control, CI, workflow engines, or model providers;
- a system that treats generated text as verified truth;
- a promise of unsupervised autonomy without policy, validation, and evidence;
- a requirement to use one cloud, one model vendor, or one project-management provider.

## 14. Differentiation

Devsembly is differentiated by the combination of:

- canonical, versioned project intelligence rather than chat-centered context;
- a full intent-to-production lifecycle rather than isolated code generation;
- provider-neutral synchronization and durable reconciliation;
- evidence-backed validation, confidence, and completion forecasting;
- explicit human and machine authority boundaries;
- built-in cost, token, budget, risk, and technical-debt governance;
- recoverable workflow execution and transactional event publication;
- reuse as the software-delivery foundation for future CompanyOS applications;
- dogfooding, where Devsembly uses its own project-intelligence model to manage Devsembly.

## 15. Security and governance principles

Devsembly must:

- deny access by default;
- isolate organizations and projects;
- authenticate humans through trusted identity providers;
- treat machine identity separately from human identity;
- derive material decision provenance from authenticated actors;
- protect secrets, tokens, credentials, and customer evidence;
- record important state changes and authorization decisions;
- require explicit authority for sensitive operations;
- preserve immutable evidence and decision history where required;
- support recovery without duplicate execution or publication;
- expose uncertainty and conflicts rather than silently overwriting them.

## 16. Success measures

Product success should be measured by outcomes such as:

- reduction in repeated explanation and context transfer;
- percentage of project documentation generated from canonical state;
- percentage of work with linked requirements, decisions, tests, and evidence;
- workflow recovery rate without duplicate execution;
- provider reconciliation freshness and conflict-resolution time;
- human intervention required per completed work item;
- validation pass rate and escaped-defect rate;
- forecast accuracy for cost and completion;
- token and infrastructure cost per accepted capability;
- time from business intent to validated software increment;
- user trust in recommendations, status, and auditability.

## 17. Product boundaries and current maturity

Devsembly is being built incrementally. The current Genesis reference implementation establishes the core persistence, API, workflow, cost, identity, evidence, audit, event-publication, Temporal-dispatch, and Project Intelligence foundations.

The existence of a documented capability does not imply that every part is implemented. Canonical project state and validation evidence determine current status. Product projections must distinguish among proposed, accepted, implemented, validated, deferred, and deprecated capabilities.

## 18. Documentation and source-of-truth policy

`.devsembly/project-state.json` is the canonical machine-readable project-state source for the current repository bootstrap. Accepted ADRs govern architectural decisions. The Genesis Constitution governs foundational principles.

This Product Specification is the primary human-readable product definition. Until automated rendering is fully implemented, changes to this document must be reconciled back into canonical project state. Once the documentation renderer is active, this file should be generated or validated from canonical state and marked as generated.

No generated view may silently become a competing source of truth. CI should eventually verify:

- schema validity;
- required product-definition fields;
- stable identifier usage;
- source-to-view consistency;
- generated-file drift;
- valid links to decisions and evidence;
- absence of hardcoded branding where stable identifiers are required.

## 19. Near-term product priorities

The near-term product priorities are:

1. complete the remaining PIE delivery sequence;
2. extend canonical state with explicit product identity, positioning, audience, principles, and naming configuration;
3. implement generated product and architecture views from canonical state;
4. add provider-neutral AI usage and cost ledgers;
5. implement governed project memory and context retrieval;
6. generate recommendations, completion forecasts, and executive dashboards;
7. connect workflow admission and escalation to cost decisions;
8. connect durable workflow steps to provider execution and evidence;
9. build the operator control surface;
10. prepare a validated development-environment release.

## 20. Governing statement

Devsembly is the governed software-delivery platform. The Project Intelligence Engine owns canonical project truth. Agents perform authorized work. Durable workflows coordinate execution. Providers supply capabilities and synchronized views. Evidence supports claims. Humans retain accountable control over material decisions.
