# Project Intelligence Engine Delivery Plan

## Milestone

Proposed milestone: **Genesis PIE Foundation**. Exit criteria are a canonical project-state contract,
trusted GitHub synchronization, planning and validation projections, usage and cost telemetry,
scoped agent context, and an evidence-backed executive read model.

## Dependency-ordered backlog

| Order | Slice | Depends on | Acceptance summary |
|---|---|---|---|
| 1 | Canonical state revisions | Genesis project, auth, audit, outbox | Versioned reads; idempotent reconcile; provenance; schema; migration; tests |
| 2 | [Work items, aliases, and graph edges](https://github.com/thebakermark/Devsembly/issues/25) | 1 | Stable IDs; hierarchy; capability/dependency edges; acyclic rules; projections |
| 3 | [GitHub ingestion and reconciliation](https://github.com/thebakermark/Devsembly/issues/26) | 2 | Verified webhooks; delivery dedupe; poll repair; conflict queue; freshness |
| 4 | [Validation, risk, and debt projections](https://github.com/thebakermark/Devsembly/issues/27) | 2, 3 | Evidence links; staleness; risk owners; debt impact and retirement criteria |
| 5 | [Usage and AI cost ledger](https://github.com/thebakermark/Devsembly/issues/28) | 1 | Provider-neutral tokens/tools; price snapshots; actual/estimate reconciliation |
| 6 | Budget admission and forecast | 4, 5 | Scenarios; P50/P80/P95; approval gates; calibration evidence |
| 7 | [MemoryOS context interface](https://github.com/thebakermark/Devsembly/issues/29) | 2, 4 | Authorized retrieval; token budgets; provenance; retention; invalidation |
| 8 | Recommendations and sprint planning | 4, 6, 7 | Policy filter; readiness; value/risk/cost scoring; explanations |
| 9 | [Executive dashboard and Genesis template](https://github.com/thebakermark/Devsembly/issues/30) | 6, 8 | Health, delivery, spend, risk, confidence, next work; automatic bootstrap |

## Test strategy

- Contract: JSON Schema, Pydantic/OpenAPI, compatibility fixtures, additive events.
- Domain: authority, conflict, graph invariants, confidence factors, deterministic ranking.
- Persistence: isolation, uniqueness, concurrency, audit/outbox atomicity, migration parity.
- Integration: signed webhook, missed-event repair, duplicates, and out-of-order events.
- Durable workflow: retry, crash recovery, approval pause/resume, and replay.
- Forecast: deterministic seeds, calibration backtests, range monotonicity, missing-data labels.
- Security: tenant isolation, least privilege, redaction, source spoofing, prompt injection.
- Operations: projection rebuild, restore checkpoint, stale-source alerts, readiness.

## Compatibility and migration

Revision `0010_project_intelligence` is additive. Existing runtime tables are unchanged. A future
import command will register `.devsembly/project-state.json` as revision 1 after a Genesis project ID
exists; startup never silently imports repository content.
