# Genesis Schemas

**Status:** Binding schema baseline
**Schema version:** 0.1.0

| Schema | Purpose |
|---|---|
| [Provider manifest](provider-manifest.schema.json) | Provider identity, capabilities, configuration, authentication, lifecycle, events, operations, and conformance |
| [Capability definition](capability-definition.schema.json) | Provider-independent capability ownership, operations, policy, service, cost, and evidence |
| [Project Intelligence state](project-intelligence-state.schema.json) | Canonical vision, architecture, graph, plan, validation, economics, risk, memory, recommendation, and forecast bootstrap state |

Organizational Genome schemas remain canonical under
[`docs/architecture/organizational-genome/schemas/`](../../architecture/organizational-genome/README.md).
They are linked instead of copied here.

Schemas use JSON Schema 2020-12 and semantic versions. A breaking change requires a new
major schema version, migration guidance, compatibility tests, and updated examples.
