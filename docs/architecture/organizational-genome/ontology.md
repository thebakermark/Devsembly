# Organizational Genome Ontology

## Primary entities

### Organization

A governed operating system composed of one or more legal entities, business units, departments, teams, positions, and agent instances.

### Legal entity

A jurisdiction-specific company, nonprofit, public body, partnership, or other legally recognized entity.

### Organizational unit

A generic parent type for business unit, department, division, branch, and team.

### Position

A versioned definition of mission, responsibilities, duties, skills, knowledge, tools, policies, authority, memory, training, performance measures, and reporting relationships.

### Agent instance

A runtime worker assigned to exactly one active position version and governed by that position's approved configuration.

## Supporting entities

- Industry
- Profession
- Job family
- Occupation
- Capability
- Competency
- Skill
- Knowledge area
- Duty
- Task
- Responsibility
- Workflow
- Policy
- Procedure
- Control
- Permission
- Tool
- Data scope
- Memory scope
- Training module
- Assessment
- Certification
- KPI
- Risk class
- Escalation rule
- Source document
- License record
- Provenance event
- Blueprint
- Tenant overlay

## Required relationships

- An organization contains one or more legal entities or organizational units.
- An organizational unit may contain child units and positions.
- A position belongs to one organizational unit.
- A position may report to one parent position.
- A position may supervise zero or more child positions.
- An agent instance must reference one position version.
- A position may reference many skills, policies, workflows, tools, training modules, KPIs, and source records.
- Source records may support many normalized entities.
- Tenant overlays extend but do not mutate canonical records.

## Capability grades

| Grade | Name | Default operating posture |
|---|---|---|
| A0 | Trainee | Observe, simulate, and practice only |
| A1 | Assistant | Prepare work for review |
| A2 | Operator | Complete standard low-risk work |
| A3 | Senior Specialist | Handle exceptions and review junior work |
| A4 | Lead | Coordinate a team and approve limited work |
| A5 | Manager | Allocate work and enforce departmental policy |
| A6 | Director | Set functional plans and cross-team priorities |
| A7 | Executive | Make enterprise recommendations and delegated decisions |
| A8 | Governor | Enforce organization-wide controls and constitutional rules |

Capability is descriptive. Authorization is enforced separately through permissions, limits, approvals, risk controls, and runtime policy.

## Policy precedence

1. Law and regulation
2. Platform constitutional controls
3. Tenant governance policy
4. Department policy
5. Position procedure
6. Workflow instruction
7. Individual task instruction

A lower layer must never override a higher layer.

## Versioning

Every canonical entity must include a stable identifier, semantic version, lifecycle status, effective date, superseded-by reference when applicable, source provenance, and immutable historical versions.
