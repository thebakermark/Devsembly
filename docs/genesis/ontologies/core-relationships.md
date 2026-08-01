# Genesis Core Relationships

**Status:** Binding conceptual relationships
**Version:** 0.1.0

| Subject | Relationship | Object | Core invariant |
|---|---|---|---|
| Organization | contains | Organizational unit | Non-root unit has one active parent |
| Organizational unit | defines | Position | Position references an immutable version |
| Person or agent | assigned to | Position | Assignment does not itself grant permission |
| Human authority | delegates to | Principal | Delegation is scoped, effective-dated, and revocable |
| Role or position | accountable for | Responsibility | Accountability and authority remain distinct |
| Capability | realized by | Process | Process preserves capability outcome and policy |
| Workflow | executes | Process version | Execution references an immutable definition |
| Provider | implements | Capability contract | Conformance names exact versions |
| Application | consumes | Capability | Application does not own provider internals |
| Objective | drives | Initiative | Initiative records owner and success measures |
| Initiative | contains | Project | Project remains within initiative and organization |
| Budget | constrains | Initiative, project, workflow, or provider | Hard limit needs human change authority |
| Decision | applies | Policy and authority | Decision preserves context and alternatives |
| Decision | supported by | Evidence | Evidence is verifiable and provenance-linked |
| Knowledge object | derived from | Source or evidence | Derived content can be invalidated |
| Audit record | records | Action or decision | Ordinary actors cannot rewrite history |
| Tenant overlay | extends | Canonical model version | Overlay cannot mutate canonical source |

## Graph invariants

Structural parent and reporting graphs contain no cycles. Causation and provenance may
form directed acyclic graphs; corrections and superseding links never delete historical
nodes. Authorization is evaluated from explicit active records rather than graph
proximity.
