# Book VI — Organizational Genome

**Status:** Binding conceptual model; runtime integration planned
**Version:** 0.1.0

The Organizational Genome is the canonical, versioned model for describing how an
organization is structured, authorized, capable, measured, funded, and improved. The
existing [Phase 1 foundation](../architecture/organizational-genome/README.md) remains
the machine-readable schema authority until superseded through its lifecycle.

## Separation of canonical and tenant data

| Canonical reusable asset | Tenant-specific operational data |
|---|---|
| Organization, department, team, role, and position templates | A tenant's legal identity and actual structure |
| Capability, skill, competency, policy, process, and metric definitions | Assignments, permissions, policies, workflows, and actual measurements |
| Reference authority and responsibility patterns | Delegations, approvals, exceptions, and access grants |
| Industry and organization blueprints | Initiatives, projects, budgets, evidence, and audit records |

Canonical assets are immutable by identifier and version. Tenants create overlays,
selections, and operational records; they do not mutate the reusable source. Promotion
of tenant learning into a canonical template requires provenance, licensing, review,
de-identification where required, and a new canonical version.

## Core models

### Organization

A governed system with purpose, legal and operating identity, policy, resources,
capabilities, boundaries, and accountable human authority.

### Organizational unit

A recursive structural unit such as business unit, division, department, branch, or
team. Every non-root unit has one active parent and an accountable leader or explicit
vacancy.

### Department

An organizational unit accountable for a durable business function, related
capabilities, policies, measures, and resources.

### Team

An organizational unit formed to perform related responsibilities or outcomes. A team
may be durable or time-bounded.

### Role

A reusable expectation of outcomes, responsibilities, competencies, and authority
constraints independent of a specific organization slot or assignee.

### Position

A versioned slot in an organizational unit that applies one or more roles, reporting
relationships, authority profile, measures, and assignment constraints.

### Person and agent assignment

An effective-dated link from a person or agent principal to a position or responsibility.
Assignment does not create permissions beyond the associated active delegation and
policy. An agent instance references exactly one primary active position version.

### Capability

The ability to produce a defined outcome under stated conditions and service levels.
Capabilities have owners, inputs, outputs, policies, measures, maturity, dependencies,
and provider implementations.

### Responsibility

An accountable obligation to produce or protect an outcome. Responsibility is distinct
from authority: being accountable does not automatically grant permission.

### Authority

An explicit, scoped, effective-dated grant to decide, approve, access, spend, direct, or
act. Authority identifies grantor, recipient, action, target, limit, conditions,
delegability, and revocation.

### Policy

A versioned rule or constraint issued by a recognized authority. Policy records scope,
precedence, enforcement, exceptions, evidence, and review date.

### Process and workflow

A process defines intended repeatable work and controls. A workflow is an executable,
versioned coordination of tasks, decisions, events, timeouts, and escalation.

### Skill and competency

A skill is a learnable ability. Competency combines skills, knowledge, judgment, and
demonstrated performance for a context and proficiency level. Neither grants authority.

### Knowledge object

A governed unit of information with type, source, owner, version, confidence, access,
retention, relationships, and correction history.

### Objective and metric

An objective states a desired outcome, scope, owner, horizon, and rationale. A metric
defines a repeatable measure, unit, source, calculation, target, cadence, and quality
limits. Metrics inform decisions but do not replace judgment.

### Initiative and project

An initiative coordinates outcomes and investment toward an objective. A project is a
bounded delivery effort within an initiative with scope, acceptance, resources, risk,
budget, timeline, and evidence.

### Budget

An authorized financial constraint with owner, scope, period, currency, categories,
hard and warning limits, forecast, actuals, flexibility, and approval rules.

### Evidence and audit records

Evidence is a verifiable artifact supporting a claim. An audit record is an append-only
account of a material action or decision, including actor, authority, time, target,
result, and evidence references.

## Required relationships

- Organizations contain organizational units, positions, capabilities, policies,
  initiatives, budgets, and knowledge.
- Positions apply roles and belong to one organizational unit.
- Assignments connect principals to active positions or responsibilities.
- Authority grants connect principals to actions, targets, limits, and approvers.
- Processes realize capabilities; workflows execute process versions.
- Objectives drive initiatives; initiatives contain projects; budgets constrain both.
- Decisions and audit records link authority, policy, evidence, cost, and outcome.
- Knowledge objects preserve provenance to sources, decisions, workflows, and evidence.

## Invariants

1. Structural parent and reporting graphs contain no cycles.
2. Permission is never inferred solely from role, position, capability grade, skill, or
   agent access.
3. Every authority grant is explicit, scoped, revocable, and auditable.
4. Canonical versions remain immutable; correction creates a successor.
5. Tenant overlays cannot alter canonical records.
6. High-risk actions have an independent human approval path.
7. Budget consumption cannot exceed a hard limit without authorized change.
8. Material decisions retain provenance and evidence.

## Lifecycle

Genome records use stable identifiers, semantic versions, lifecycle state, effective
dates, source and license provenance, review dates, and superseding links. Runtime
assignments reference an immutable version so historical actions remain explainable.

## Validation

Machine validation must cover schema, references, cycles, effective dates, policy
precedence, authority scope, assignment readiness, provenance, licensing, budget rules,
and separation of canonical and tenant data. Human review remains required for meaning,
legal suitability, and high-risk authority design.
