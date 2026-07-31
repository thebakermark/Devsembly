# Project Intelligence Enterprise Patterns

Status: research baseline for PIE architecture, reviewed 2026-07-31.

## Scope

This review focuses on reusable architecture rather than copying a vendor user interface. Product
documentation is treated as evidence of a pattern, not as authority over Devsembly's domain model.

## Findings

| System | Useful pattern | Devsembly response |
|---|---|---|
| Microsoft Foundry | A unified management plane governs agents, models, tools, identity, policy, evaluation, and observability. Memory is scoped and persistent rather than reconstructed per chat. | Adopt a provider-neutral project control plane, scoped memory, policy checks, traces, and evaluation evidence. Do not make Azure the canonical store. |
| GitHub | Issues, sub-issues, milestones, dependencies, custom fields, pull requests, and Actions provide strong delivery evidence and adaptable projections. | Adapt GitHub as the first source-control and work-tracking provider. Retain GitHub node IDs and URLs as external identities while assigning PIE stable IDs. |
| Jira and Rovo | Configurable work hierarchies, linked dependencies, cross-product knowledge, and coding agents ground work in issue and repository context. | Adopt configurable work types, typed relationships, and retrieval across evidence. Reject vendor-specific hierarchy names as canonical domain constraints. |
| Linear | Initiatives, projects, milestones, cycles, issue relations, and concise status updates separate executive intent from delivery detail. | Adopt a small default planning hierarchy and time-box projection. Keep the ontology extensible rather than hard-code one methodology. |
| Temporal | Durable history, replay, idempotent Activities, message deduplication, resumable human approvals, and recovery after worker failure. | Reuse Genesis Temporal dispatch for reconciliation and long-running forecasts. Keep canonical project facts in PostgreSQL; Temporal owns execution history, not business truth. |
| OpenAI | Agent runs expose structured context, usage, tool calls, handoffs, guardrails, approvals, traces, and evaluation results. | Record provider-neutral run, usage, trace, approval, and evaluation facts. Use agents as bounded specialists while PIE remains shared context. |
| Anthropic | Subagents use isolated contexts and permissions; prompt caching and explicit cost guidance show that full chat replay is expensive and context should be curated. | Give each agent a least-privilege PIE view and token budget. Return evidence-backed summaries instead of copying all source material into every prompt. |
| W3C PROV | Provenance distinguishes entities, activities, and responsible agents so consumers can assess quality and trustworthiness. | Adapt the Entity/Activity/Agent vocabulary into lightweight source, observation, transformation, and actor metadata without requiring RDF infrastructure in Genesis v0.1. |

## Adopt

- An immutable canonical revision log plus rebuildable read projections.
- Stable internal identifiers with provider identifiers stored as aliases.
- Facts, inferences, disputes, and human decisions as distinct states.
- Source URI or identifier, source event time, observation time, actor, transformation, checksum,
  and evidence references on material state.
- At-least-once ingestion with idempotency keys, request fingerprints, ordering metadata, and
  periodic reconciliation.
- Durable workflows for ingestion, approval, forecast recomputation, and recovery.
- Least-privilege agent context assembled from authorized projections.
- Per-call token and cost actuals with budget-policy evaluation before expensive work.
- Traces and evaluation evidence as validation inputs, not self-asserted proof.

## Adapt

- Use `Vision -> Milestone -> Epic -> Feature -> Task` as the default planning view, while the
  canonical `WorkItem` type and typed parent edge permit other hierarchies.
- Store graph nodes and edges relationally first. Add graph-specific infrastructure only after
  traversal volume or latency demonstrates need.
- Use deterministic forecasting first: dependency-aware remaining effort distributions, delivery
  history, validation status, and risk adjustments. Machine learning remains optional and must be
  calibrated against outcomes.
- Use GitHub Issues and milestones for collaborative planning, but regard them as synchronized
  projections of PIE rather than the platform brain.

## Reject or defer

- Chat transcripts as authoritative project memory.
- Last-write-wins reconciliation across sources with different authority.
- A model-generated confidence number without factors, evidence, and calibration history.
- A separate graph database, event-stream platform, or data warehouse in the first slice.
- Provider-specific IDs as primary keys.
- Automatic approval of high-risk, security-sensitive, compliance-sensitive, or over-budget work.
- A single opaque completion date. PIE will expose ranges, assumptions, confidence, and model
  version.

## Primary sources

- [Microsoft Foundry overview](https://learn.microsoft.com/en-us/azure/foundry/what-is-foundry)
- [Foundry Agent Service memory](https://learn.microsoft.com/en-us/azure/foundry/agents/concepts/what-is-memory)
- [GitHub sub-issues](https://docs.github.com/en/issues/tracking-your-work-with-issues/using-issues/adding-sub-issues)
- [GitHub Projects](https://docs.github.com/en/issues/planning-and-tracking-with-projects)
- [GitHub Project insights](https://docs.github.com/en/issues/planning-and-tracking-with-projects/viewing-insights-from-your-project/about-insights-for-projects)
- [Jira custom hierarchy](https://support.atlassian.com/jira-software-cloud/docs/configure-custom-hierarchy-levels-in-advanced-roadmaps/)
- [Jira linked work items](https://support.atlassian.com/jira-software-cloud/docs/link-issues/)
- [Jira Coding Agent](https://support.atlassian.com/jira-software-cloud/docs/what-is-the-jira-coding-agent/)
- [Linear initiatives](https://linear.app/docs/initiatives)
- [Linear project milestones](https://linear.app/docs/project-milestones)
- [Temporal message idempotency](https://docs.temporal.io/handling-messages)
- [Temporal pre-production testing](https://docs.temporal.io/best-practices/pre-production-testing)
- [Temporal human approval workflow](https://docs.temporal.io/guides/reliable-document-approvals)
- [OpenAI agent orchestration](https://developers.openai.com/api/docs/guides/agents/orchestration)
- [OpenAI tracing and observability](https://developers.openai.com/api/docs/guides/agents/integrations-observability)
- [OpenAI agent evaluation](https://developers.openai.com/api/docs/guides/agent-evals)
- [OpenAI Agents SDK usage](https://openai.github.io/openai-agents-python/usage/)
- [Anthropic Claude Code subagents](https://docs.anthropic.com/en/docs/claude-code/sub-agents)
- [Anthropic Claude Code costs](https://docs.anthropic.com/en/docs/claude-code/costs)
- [W3C PROV data model](https://www.w3.org/TR/prov-dm/)
