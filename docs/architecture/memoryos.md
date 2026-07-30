# Devsembly MemoryOS

Status: Proposed foundational architecture

## Purpose

MemoryOS is Devsembly's governed memory and context subsystem. It prevents agents from treating every document, message, log, and decision as equivalent. It classifies information, stores it in the correct backend, retrieves only what is relevant, and builds a token-bounded context package for each model call.

The core design rule is:

> Agents do not read or write memory stores directly. They request memory operations through the Memory Governor.

## Goals

- Preserve important decisions and institutional knowledge.
- Keep model prompts below configurable token and cost budgets.
- Separate temporary state from durable knowledge.
- Route retrieval by task, sensitivity, recency, confidence, and importance.
- Maintain provenance and access control for every memory item.
- Compress and summarize aging information without destroying source records.
- Support multiple model providers and context-window sizes.
- Allow project, tenant, department, agent, and user-level isolation.

## Non-goals

- Replacing authoritative business databases.
- Treating vector similarity as factual truth.
- Injecting all available history into every prompt.
- Allowing agents to silently promote guesses into durable facts.

## Memory hierarchy

### 1. Working memory

Current prompt, current task, current files, current tool outputs, and immediate reasoning inputs.

- Lifetime: one model invocation or task step
- Preferred storage: in-process state or Redis
- Default retention: minutes to hours
- Prompt priority: highest

### 2. Scratch memory

Temporary calculations, hypotheses, intermediate plans, and partial outputs.

- Lifetime: task or workflow
- Preferred storage: Redis, JSON, or temporary object storage
- Default retention: hours to days
- Promotion rule: only validated outcomes may become durable memory

### 3. Session memory

Task history, completed steps, unresolved blockers, and resumable workflow state.

- Lifetime: session or run
- Preferred storage: PostgreSQL plus Redis cache
- Default retention: configurable, typically 30–90 days

### 4. Agent memory

Agent-specific operating knowledge, learned preferences, failure patterns, and role-specific procedures.

- Scope: agent definition and tenant
- Preferred storage: PostgreSQL, versioned Markdown, embeddings
- Examples: QA flake history, architecture conventions, marketing voice

### 5. Project memory

PRDs, ADRs, code maps, schemas, decisions, incidents, releases, and project-specific terminology.

- Scope: project or repository
- Preferred storage: Git, PostgreSQL, pgvector, object storage
- Default retention: durable

### 6. Organization memory

Policies, standards, reusable templates, security controls, approved vendors, brand standards, and shared processes.

- Scope: tenant, organization, department, or business unit
- Preferred storage: PostgreSQL, Git, object storage, vector index
- Default retention: durable and versioned

### 7. Historical archive

Raw logs, old conversations, superseded documents, telemetry, artifacts, and audit records.

- Preferred storage: MinIO/S3-compatible object storage and cold archive
- Retrieval: explicit or evidence-driven only
- Default prompt priority: low

## Storage responsibilities

### PostgreSQL

Authoritative metadata and structured state:

- memory records
- scopes and permissions
- importance and confidence scores
- lifecycle state
- provenance
- links to source artifacts
- summarization lineage
- token and cost accounting
- retention policies

### pgvector

Semantic retrieval for text chunks and summaries. PostgreSQL with pgvector is the default first implementation to avoid unnecessary operational complexity.

### Redis

Fast, short-lived state:

- working memory
- session cache
- retrieval cache
- locks
- queues
- rate limits
- context-package cache

### Git and Markdown

Human-reviewable, versioned knowledge:

- architecture decisions
- standards
- runbooks
- agent definitions
- prompts
- policies
- project documentation

### MinIO or S3-compatible object storage

Large and immutable source artifacts:

- PDFs
- images
- audio
- video
- build artifacts
- raw exports
- archived transcripts

### Knowledge graph

Introduce only when relationship queries justify it. Begin with relational edges in PostgreSQL. Evaluate Apache AGE, Memgraph, or Neo4j later.

Typical relationships:

- decision supersedes decision
- task produced artifact
- incident affected service
- agent owns capability
- project depends on service
- requirement implemented by pull request

## Core services

### Memory Governor

The central policy and routing service. It decides:

- whether information should be stored
- memory class and scope
- retention period
- importance and confidence
- destination backend
- whether review or approval is required
- whether existing memory should be updated, linked, or superseded

### Context Builder

Builds the smallest useful context package for a model call.

Inputs:

- task intent
- agent identity and role
- tenant and project scope
- model context limit
- token budget
- cost budget
- latency target
- sensitivity policy

Outputs:

- system and policy context
- task instructions
- recent working state
- retrieved memories
- source citations and provenance
- remaining token allowance

### Knowledge Curator

Performs asynchronous maintenance through scheduled jobs:

- deduplication
- clustering
- conflict detection
- summarization
- stale-memory review
- promotion and demotion
- archival
- deletion under retention policy

### Relationship Index

Maintains typed links between memories, code, people, agents, projects, tasks, tools, and artifacts.

### Learning Engine

Detects repeated workflows, recurring failures, and reusable patterns. It may propose new automations or standards, but it cannot publish durable organizational memory without policy approval.

### Cost and Token Optimizer

Tracks model usage and chooses retrieval depth, summarization level, and model tier under policy constraints.

## The Mayor: intelligent call routing

The higher-level orchestration component is called the **Mayor**. The Mayor routes work; the Memory Governor routes memory.

The Mayor evaluates:

- task type
- risk and importance
- required tools
- required expertise
- model capability
- latency target
- context size
- privacy boundary
- estimated cost
- confidence threshold

Example routing:

1. Classify the request as coding, research, planning, operations, or approval.
2. Determine risk: low, normal, high, or regulated.
3. Select an agent or agent team.
4. Ask MemoryOS for a task-specific context package.
5. Select a model tier based on required reasoning and budget.
6. Execute tools under least-privilege policy.
7. Evaluate output confidence and validation results.
8. Store only approved outcomes and provenance.

The Mayor must never use importance alone. A high-importance task may still require a small context package if the correct authoritative records are known.

## Token management policy

### Budget allocation

Each call receives a maximum input budget divided into categories:

- 10% system and policy instructions
- 10% task definition and output contract
- 20% recent working state
- 45% retrieved knowledge and source excerpts
- 15% safety margin and tool-result growth

These are defaults, not fixed limits. The Context Builder may rebalance by task type.

### Retrieval sequence

1. Exact structured lookup.
2. Recent session and task state.
3. High-importance project or organization memory.
4. Semantic retrieval.
5. Relationship expansion.
6. Historical archive only when needed.

### Ranking score

A retrieval candidate should be ranked using a weighted score such as:

`score = relevance + authority + recency + importance + scope_match + relationship_strength - redundancy - staleness - access_risk`

Weights are policy-controlled and observable.

### Hierarchical summarization

MemoryOS stores multiple levels:

- raw source
- chunk summary
- document summary
- topic summary
- project summary
- organization summary

The Context Builder starts with the highest useful summary level and expands only when evidence or detail is required.

### Overflow behavior

When the candidate context exceeds the budget:

1. Remove duplicates.
2. Prefer authoritative sources over conversational recollections.
3. Replace raw chunks with summaries.
4. Reduce relationship expansion depth.
5. Drop low-confidence and low-importance candidates.
6. Split the task into stages if the output contract allows it.
7. Escalate to a larger-context model only when policy and budget permit.

## Memory record model

Minimum fields:

```text
id
memory_class
scope_type
scope_id
tenant_id
project_id
agent_id
subject
content
content_hash
source_type
source_uri
source_version
provenance
importance
confidence
authority
sensitivity
created_at
updated_at
expires_at
last_accessed_at
access_count
lifecycle_state
supersedes_id
summary_of_id
embedding_model
embedding_version
```

Lifecycle states:

- candidate
- active
- disputed
- superseded
- archived
- expired
- deleted

## Importance and confidence

Importance and confidence are separate.

- Importance answers: how costly would it be to forget this?
- Confidence answers: how likely is this to be correct?

A critical but unverified statement can be high importance and low confidence. It must remain visible for review but cannot be treated as authoritative.

Suggested importance levels:

1. disposable
2. temporary
3. useful
4. durable
5. critical

## Provenance and conflict handling

Every durable memory must identify its origin. Derived summaries must link to source memories.

When sources conflict:

- preserve both records
- mark the conflict
- prefer higher-authority and newer applicable sources for retrieval
- never overwrite an authoritative source with an agent-generated summary
- require human or policy-based resolution for critical conflicts

## Security model

- Tenant isolation is mandatory.
- Retrieval is filtered before ranking, not after.
- Sensitive memory is encrypted at rest and in transit.
- Agents receive only role-appropriate scopes.
- Tool outputs inherit the sensitivity of their source.
- Prompt and retrieval logs must avoid duplicating secrets.
- Deletion requests must propagate to embeddings, summaries, caches, and archives according to policy.

## Initial API surface

```text
POST /memory/ingest
POST /memory/search
POST /memory/context/build
POST /memory/promote
POST /memory/supersede
POST /memory/dispute
POST /memory/summarize
GET  /memory/{id}
GET  /memory/{id}/lineage
GET  /memory/usage
```

## Events

```text
memory.candidate.created
memory.promoted
memory.superseded
memory.disputed
memory.expired
memory.archived
context.built
context.budget.exceeded
retrieval.conflict.detected
retention.action.completed
```

## Observability

Track:

- tokens requested, retrieved, injected, and discarded
- retrieval latency
- cache hit rate
- cost per task and agent
- source diversity
- stale-memory rate
- summary compression ratio
- retrieval precision from evaluation sets
- number of conflicts and unresolved disputes
- percentage of prompts with complete provenance

## Implementation phases

### Phase 1: governed memory foundation

- PostgreSQL schema
- pgvector extension
- Redis working/session cache
- Memory Governor API
- Context Builder API
- basic importance, confidence, scope, and retention policies
- token accounting
- provenance links

### Phase 2: curation and compression

- deduplication
- hierarchical summaries
- stale-memory review
- conflict detection
- scheduled retention jobs
- retrieval evaluation harness

### Phase 3: Mayor integration

- task classifier
- agent router
- model-tier router
- cost and latency policies
- role-based context packages
- escalation and validation rules

### Phase 4: relationship intelligence

- typed relationship model
- graph-style traversal
- impact analysis
- cross-project knowledge reuse
- learning-engine proposals

## Acceptance criteria for the first production slice

- No agent directly accesses pgvector, Redis, or memory tables.
- Every retrieved memory is tenant- and scope-filtered.
- Every injected memory includes provenance.
- Context packages respect configurable token budgets.
- Overflow produces deterministic degradation rather than prompt failure.
- Durable memory requires confidence, authority, and retention metadata.
- Raw source records remain available after summarization.
- Deleting a memory invalidates associated embeddings and caches.
- Usage metrics report token and cost consumption by tenant, project, task, agent, and model.

## Architectural decision

Devsembly will implement MemoryOS as a platform capability shared by all agents and products. The Mayor will consume MemoryOS through stable APIs and will not own persistence logic. PostgreSQL, pgvector, Redis, Git, and MinIO form the initial storage stack. A dedicated graph database is deferred until measured relationship-query requirements justify it.
