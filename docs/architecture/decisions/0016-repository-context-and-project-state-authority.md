# ADR-0016: Repository context and project-state authority

- Status: Accepted
- Date: 2026-08-01

## Context

AI work sessions are temporary and cannot be trusted to retain repository, branch, milestone, validation, or architectural context. Reconstructing the complete project from GitHub, workflow history, evidence, and documentation on every session is reliable but inefficient. A single hand-maintained context document is fast to read but becomes stale, conflict-prone, and ambiguous as multiple agents and providers participate.

Devsembly already maintains a schema-controlled product definition, an immutable PIE revision model, rebuildable projections, provider synchronization, and a portable `.devsembly/project-state.json` package. The authority and intended use of those layers must be explicit.

## Decision

Devsembly will use a layered authority model:

1. `AGENTS.md` defines stable repository-wide operating instructions for human and AI contributors.
2. GitHub is authoritative for source-control and development-provider facts: commits, branches, issues, pull requests, reviews, and CI evidence.
3. The PIE canonical revision store is authoritative for effective project operating state.
4. `.devsembly/project-state.json` is a compact, read-optimized, schema-versioned, rebuildable projection used for portable context and fast session startup.
5. Temporal event history is authoritative for durable workflow recovery state.
6. Evidence storage is authoritative for immutable validation artifacts.
7. Agent context packages, summaries, dashboards, and generated documents are derived views and never override their cited sources.

When sources disagree, the system must prefer the authoritative source for that information class, record freshness and provenance, and regenerate stale projections. The portable state package must remain bounded and must reference rather than duplicate unbounded provider history.

Requirements must be measurable records with stable identifiers and acceptance criteria. Broad qualities such as “extensible” are design goals until expressed as testable behavior, such as registering a provider without modifying orchestration core code and passing a shared provider contract suite.

## Consequences

- New sessions can start quickly without depending on chat history.
- Project state remains inspectable beside the code while scaling to database-backed projections and provider event ingestion.
- The state file can be deleted and rebuilt without loss of canonical history.
- CI and reconciliation workflows must detect malformed, stale, or unsupported projections.
- Multiple agents should update authoritative records or events rather than concurrently hand-editing a large shared snapshot.
- Repository instructions must remain concise; detailed requirements, decisions, risks, and evidence stay in their dedicated records.

## Rejected alternatives

### Chat history as project memory

Rejected because sessions are temporary, incomplete, and not auditable.

### One large manually maintained context file

Rejected as the sole source because it creates stale data, merge conflicts, duplication, and unclear authority.

### GitHub-only reconstruction on every run

Rejected as the only startup path because repeated provider scans add latency, cost, and unnecessary context volume.

### Database-only project state

Rejected because repository-local portability, code review, offline inspection, and bootstrap behavior remain important.
