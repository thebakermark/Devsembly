# Validation Rules

## Structural

- Every position has a stable ID, version, title, mission, organizational unit, capability grade, lifecycle status, and provenance list.
- Every active position reports to zero or one parent position.
- Reporting relationships contain no cycles.
- Every non-root organizational unit has exactly one parent.
- Every deployed agent references an active position version.
- No permission is inferred from capability grade alone.

## Governance

- High-risk actions require an explicit approval rule.
- Policy precedence is deterministic.
- Tenant overlays cannot mutate canonical source entities.
- Restricted sources cannot populate public marketplace packages.
- Imported source text cannot become executable instruction without approval.

## Runtime readiness

A deployable position requires approved authority and memory profiles, required policies and workflows, training status, an escalation path, a supervisor or root designation, a valid tool profile, and no unresolved high-severity findings.
