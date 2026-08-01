# Devsembly AI Work Standard

## Canonical operating context

- Repository: `thebakermark/Devsembly`
- GitHub is authoritative for commits, branches, issues, pull requests, reviews, and CI evidence.
- `.devsembly/project-state.json` is a compact, rebuildable projection for fast session startup. It is not the complete history and must not override fresher provider evidence.
- The PIE revision store is authoritative for effective project operating state once populated.
- Temporal history is authoritative for durable workflow recovery.
- Evidence storage is authoritative for immutable validation artifacts.

## Session startup

1. Inspect the current pull request, head commit, reviews, CI, and active milestone.
2. Read `.devsembly/manifest.json`, `.devsembly/product-definition.json`, and `.devsembly/project-state.json`.
3. Read the relevant requirements, architecture decisions, and milestone issue before changing code.
4. Reconcile stale repository projections from authoritative sources instead of trusting chat history.
5. Continue the smallest coherent slice toward the active milestone. Do not recreate completed work or broaden scope without necessity.

## Delivery rules

- Keep stable identifiers separate from configurable display names.
- Connect implementation to a requirement, decision, issue, test, and evidence when those records exist.
- Prefer provider-neutral contracts and contract tests over hard-coded integrations.
- Preserve identity, policy, approval, budget, audit, evidence, idempotency, and recovery boundaries.
- Run the repository-supported validation suite and record exact results.
- Update generated or portable project state only from verified evidence and include provenance, confidence, and the observed commit or provider object.
- Never merge or deploy without explicit human approval. Draft PR #17 must remain draft and unmerged until Mark explicitly approves it.

## Active milestone rule

The active milestone and recommended next work come from fresh GitHub and PIE evidence. At the time this standard was introduced, issue #33—first governed autonomous delivery loop—was the immediate milestone, with isolation of coding and validation execution required before a credentialed live demonstration.
