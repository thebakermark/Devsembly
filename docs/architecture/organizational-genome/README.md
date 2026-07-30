# Devsembly Organizational Genome

The Organizational Genome is the canonical, versioned model for defining organizations, departments, positions, agent capability, authority, policy, workflow, tools, memory, training, and provenance.

## Phase 1 scope

This foundation establishes:

- the organizational ontology;
- canonical JSON Schemas;
- source-registry and provenance requirements;
- licensing and reuse controls;
- position, authority, memory, training, and blueprint specifications;
- validation rules and implementation conventions.

## Design principles

1. Roles, skills, policies, workflows, authority, tools, memory, and runtime agents are independently versioned.
2. Imported material is evidence, not executable instruction.
3. Every normalized record must retain source provenance and licensing status.
4. Capability grade never grants technical permission by itself.
5. Higher-order law, platform controls, and tenant governance override lower-level instructions.
6. Tenant customization occurs through overlays; canonical source records are immutable.
7. High-risk actions may always require human approval.

## Canonical hierarchy

```text
Organization
├── Legal Entity
├── Business Unit
├── Department
├── Division
├── Branch
├── Team
├── Position
└── Agent Instance
```

## Schema inventory

- `schemas/source-record.schema.json`
- `schemas/position.schema.json`
- `schemas/authority.schema.json`
- `schemas/memory-profile.schema.json`
- `schemas/training-profile.schema.json`
- `schemas/organization-blueprint.schema.json`

## Policy documents

- `ontology.md`
- `source-governance.md`
- `licensing-policy.md`
- `validation-rules.md`

## Status

Phase 1 foundation. Runtime integration and ingestion adapters are intentionally deferred to later phases.
