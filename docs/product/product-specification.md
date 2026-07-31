<!-- GENERATED FILE: edit .devsembly/product-definition.json, not this file. -->
# Devsembly Product Specification

**Stable ID:** `platform:software-delivery`

**Specification:** 1.0

**Status:** accepted

**Category:** Governed AI-native software delivery platform

**Tagline:** From business intent to validated software through governed AI work.

## General description

Devsembly is an AI-first software factory and project operating system that plans, builds, validates, documents, governs, and continuously understands software projects through coordinated AI agents and durable project state.

## Plain-language description

A user describes what they want to build, the constraints they must work within, and the outcome they need. Devsembly turns that intent into organized work, coordinates specialized AI agents and development tools, validates the results, and keeps the project's knowledge current across sessions and systems.

## Technical description

Devsembly is a provider-neutral enterprise AI development platform combining canonical project intelligence, multi-agent orchestration, durable workflows, governed tools and capabilities, memory and context management, provider synchronization, identity and policy enforcement, evidence-backed validation, cost governance, observability, recommendations, and forecasting.

## Mission

Make enterprise-grade software creation accessible, repeatable, auditable, and economically sustainable by combining AI labor with disciplined engineering and governance.

## Vision

Enable a person, team, or enterprise to move from business intent to production software through a durable, governed, and increasingly autonomous delivery system.

## Target audiences

- Founders and business leaders who need software without managing a conventional engineering organization.
- Product and technology executives who need reliable visibility across AI-assisted delivery.
- Software teams adopting coding agents without sacrificing governance or traceability.
- Enterprises building internal AI development platforms or agent factories.
- Consultants and managed-service providers operating multiple client projects.
- CompanyOS applications that need a shared project-intelligence and delivery foundation.

## Design principles

### One canonical truth, many views

Maintain project knowledge as schema-versioned canonical state and generate human and machine views from it.

### Governed AI authority

Allow AI agents to reason and execute only within explicit identity, policy, approval, and budget boundaries.

### Durable systems over chat memory

Persist important facts, decisions, evidence, risks, and work state outside transient conversations.

### Provider neutrality

Keep repositories, model vendors, clouds, workflow engines, and trackers replaceable behind stable contracts.

### Evidence before confidence

Base status, recommendations, confidence, and forecasts on provenance, validation, and known uncertainty.

### Incremental autonomy

Increase autonomy only as policies, tests, evidence, and operational history justify it.

### Cost as an architectural constraint

Treat token usage, model cost, infrastructure expense, and explicit budgets as first-class design inputs.

### Stable identifiers, changeable names

Separate persisted technical identifiers from configurable product, runtime, capability, and platform display names.

## Problems solved

1. AI tools lose project context and repeat or contradict prior work.
2. Repositories, tickets, documents, chats, and dashboards become competing sources of truth.
3. Coding agents can act without shared priorities, authority, evidence, or cost boundaries.
4. Long-running development work is difficult to recover, validate, and audit.
5. Business users must manually translate intent into technical work and repeatedly coordinate tools.

## Core capabilities

| Stable capability | Product capability | Intended outcome |
| --- | --- | --- |
| `capability:project-intelligence` | Project intelligence | Maintain schema-versioned project truth, provenance, work hierarchy, graphs, validation, risk, debt, recommendations, and forecasts. |
| `capability:agent-orchestration` | Governed AI workforce | Coordinate specialized agents with explicit roles, permissions, context, budgets, and escalation rules. |
| `capability:durable-workflows` | Durable workflow orchestration | Persist intent before execution and recover long-running work without duplicate side effects. |
| `capability:memory-context` | Memory and context | Assemble authorized, relevant, provenance-aware working context from durable project knowledge. |
| `capability:provider-integration` | Provider integration | Use replaceable source-control, model, cloud, workflow, and tool providers through stable contracts. |
| `capability:governance` | Identity and governance | Enforce identity, authorization, policy, approval, budget, audit, and human-authority boundaries. |
| `capability:validation-evidence` | Validation and evidence | Connect claims and completion status to tests, reviews, artifacts, provenance, and immutable evidence. |
| `capability:operations` | Operations and observability | Expose health, execution, cost, risk, failures, and recovery controls to operators. |

## Foundational delivery workflow

1. Capture business intent, constraints, and success measures.
2. Create canonical requirements and a traceable work item.
3. Build authorized task context and evaluate policy, risk, and budget.
4. Create an isolated branch and workspace.
5. Execute bounded agent implementation.
6. Run deterministic validation and bounded repair.
7. Publish a draft pull request with evidence for human review.
8. Propose the run outcome to governed project memory.
9. Reconcile provider state and recommend the next work.

## Product boundaries

- Unsupervised production changes without policy-required human approval.
- Replacing source control, CI, workflow engines, or model providers.
- Treating generated text or a vector index as authoritative project truth.
- Requiring one model vendor, cloud, repository host, or issue tracker.
- Building every CompanyOS business module before the delivery platform works end to end.

## Success measures

- Time from accepted business intent to a validated draft change request.
- Percentage of completed work linked to requirements, evidence, decisions, and project memory.
- Workflow recovery rate without duplicate work items, branches, or pull requests.
- Human interventions and repeated context explanations per accepted increment.
- Validation pass rate, escaped-defect rate, and cost per accepted capability.

## Current maturity

**Stage:** Genesis reference implementation

**Implemented foundation:** Core persistence, APIs, durable workflow dispatch, identity, policy, cost governance, evidence, audit, outbox publication, GitHub reconciliation, PIE projections, and governed context assembly.

**Not yet proven:** A live development-host demonstration of the complete business-intent to traceable issue, isolated implementation, validated draft pull request, and updated project-memory loop.

## Next milestone

**First governed autonomous delivery loop** (`milestone:first-governed-delivery-loop`)

- An authorized request starts a durable workflow through the control-plane API.
- The run creates or links a traceable work item before implementation.
- Agent changes remain inside an isolated workspace and declared path boundary.
- Validation evidence is captured and bounded repair is enforced.
- A draft, unmerged pull request is published for human review.
- The outcome is proposed to governed project memory with provider links and evidence.

## Source authority

| Information | Authority |
| --- | --- |
| Code, commits, pull requests, reviews, and CI evidence | Source-control provider |
| Effective project operating state | PIE canonical revision store |
| Portable repository state package | Generated .devsembly modules |
| Durable workflow recovery state | Workflow engine history |
| Large immutable validation artifacts | Evidence storage |
| Agent working context | Rebuildable non-authoritative context package |

## Naming configuration

| Stable identifier | Display name | Industry-standard term |
| --- | --- | --- |
| `platform:software-delivery` | Devsembly | AI-native software delivery platform |
| `runtime:reference` | Genesis | Reference agent runtime and control plane |
| `capability:project-intelligence` | Project Intelligence Engine (PIE) | Canonical project intelligence layer |
| `platform:enterprise-ai` | CompanyOS | Enterprise AI operating platform |

## Governing rule

This specification is generated from `.devsembly/product-definition.json`, a module
of the canonical `.devsembly` state package. Edit the canonical module and regenerate
this view; do not maintain a competing product specification by hand.
