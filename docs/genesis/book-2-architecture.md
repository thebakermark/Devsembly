# Book II — Architecture

**Status:** Binding blueprint with staged future-state sections
**Version:** 0.1.0

## Architecture objectives

Devsembly separates organizational intent and policy from provider implementations. It
must remain understandable on a single supported Development Host, stay compatible with
the Genesis budget, and preserve a path to greater scale without prebuilding that scale.

## State labels

- **Binding/current:** accepted and represented in the Genesis v0.1 repository.
- **Binding/planned:** required by the accepted Genesis plan but not yet fully implemented.
- **Proposed:** future-state architecture requiring an accepted ADR before it becomes
  binding.
- **Deferred:** explicitly outside Genesis v0.1.

## Dependency model

```text
Applications and business modules
        |
Application services and Executive Core policy
        |
Domain capabilities and Organizational Genome
        |
Kernel contracts and ports
        |
Provider adapters
        |
External systems and infrastructure
```

Dependencies point inward toward domain policy and stable contracts. Domain code must
not import provider SDKs, ORM models, web frameworks, or deployment tooling. Cross-domain
writes go through application services and the Unit of Work. External events use the
transactional outbox.

## Genesis v0.1 binding architecture

The following accepted decisions remain controlling:

| Concern | Binding decision |
|---|---|
| Runtime | Python 3.12+, FastAPI, and Pydantic modular monolith |
| Workflow | Temporal behind a `WorkflowProvider` interface |
| Identity | External OIDC/OAuth 2.0; internal authorization remains in Devsembly |
| Structured state | PostgreSQL with SQLAlchemy 2.x and Alembic |
| Persistence boundary | Repository and Unit of Work contracts |
| Integration events | Transactional outbox in the business transaction |
| Large evidence | MinIO-compatible object storage; metadata in PostgreSQL |
| Ephemeral state | Redis only for cache, locks, rate limits, and coordination |
| Initial source control | GitHub adapter as a provider and system of delivery evidence |

GitHub is not the Devsembly brain. Organization, policy, workflow correlation, budget,
decision, and audit state belong to Devsembly's canonical data and knowledge services.
GitHub is initially authoritative for its repositories, issues, commits, pull requests,
reviews, checks, and releases.

## Future-state platform components

### Devsembly Kernel — proposed

The Kernel supplies capability discovery, provider lifecycle, events, workflow ports,
identity and policy enforcement, memory ports, configuration, observability, and plugin
isolation. It is a logical boundary first; Genesis does not require a separate Kernel
service. See the [Kernel specification](kernel/kernel-specification.md).

### Executive Core / Mayor — proposed

The Executive Core interprets authorized objectives, evaluates policy and budget,
selects capabilities, coordinates plans, requests approvals, and records decisions. It
does not bypass workflows or providers and cannot enlarge its own authority. Genesis
implements this behavior incrementally through application services and governed
Temporal workflows.

### Organizational Genome — foundation current, runtime integration planned

The Organizational Genome defines reusable, versioned organization models and
tenant-specific overlays. Its Phase 1 ontology and schemas exist under
[`docs/architecture/organizational-genome/`](../architecture/organizational-genome/README.md).
The Genesis book defines its governance and runtime separation.

### MemoryOS — proposed

MemoryOS is the governed memory capability spanning records, knowledge objects,
provenance, retrieval, summarization, retention, correction, and access policy. It may
use relational, object, search, vector, or graph providers behind separate contracts.
No single storage product is MemoryOS, and no model context window is authoritative
memory.

### Workflow engine — current adapter, planned business workflows

Workflow business definitions belong to Devsembly. The selected workflow provider owns
durable execution mechanics. Workflow definitions must be versioned, deterministic
where required, correlated to audit records, and portable at the contract boundary.

### Capability registry — proposed

The registry resolves capability requirements to compatible provider instances using
version, health, policy, data residency, cost, and support evidence. Static configuration
is sufficient for Genesis until dynamic resolution is justified.

### Provider manager — proposed

The provider manager validates configuration, starts and stops adapters, monitors health,
applies circuit and timeout policy, and coordinates replacement. It does not expose
provider credentials to domain logic.

### Event bus — planned

Domain events are recorded transactionally. Delivery is asynchronous, idempotent, and
observable. Genesis begins with a PostgreSQL outbox; a broker is deferred until measured
needs justify it.

### Identity and policy — planned

External providers authenticate principals. Devsembly maps principals, memberships,
roles, delegations, data scopes, approval rules, and budget authority. All material
authorization decisions produce audit evidence.

### Plugin model — proposed

Plugins package providers, capabilities, schemas, migrations, permissions, and
conformance evidence. Plugins run with declared permissions and isolation. A marketplace
is deferred.

### Knowledge graph — deferred

Graph relationships are useful for the Organizational Genome and provenance, but Genesis
does not require a dedicated graph database. Canonical relational models and explicit
relationship schemas come first.

### Business modules and applications — deferred except Genesis control surface

Business modules consume platform capabilities and own their domain rules. Applications
are interaction surfaces. Neither may bypass policy, budget, identity, audit, or provider
contracts. CompanyOS and industry modules remain outside Genesis v0.1.

## Provider boundary

LLMs, coding agents, source control, work tracking, identity, databases, object stores,
workflow engines, container runtimes, infrastructure, deployment systems, and monitoring
systems are providers. Each provider must satisfy the
[Provider SDK](provider-sdk/README.md), including conformance, security, cost, lifecycle,
failure, and exit requirements.

## Data authority

| Record | Authoritative location |
|---|---|
| Organization, policy, budget, workflow correlation, decision, audit | Devsembly PostgreSQL in Genesis |
| Large evidence object | Object-storage provider, with checksum and metadata in PostgreSQL |
| Source, issue, commit, PR, review, CI check | Selected source-control/work-tracking provider |
| Durable workflow execution history | Selected workflow provider |
| Canonical governance and architecture | Versioned repository documentation |
| Agent working context | Non-authoritative cache derived from canonical sources |

## Extraction rules

A module becomes a separate deployable service only when measured scaling, isolation,
compliance, ownership, or release needs justify the operational cost. Extraction must
preserve contracts, data ownership, audit correlation, migration, and rollback.

## Architecture acceptance

An architecture change is acceptable only when it:

- passes the constitutional test;
- names current, proposed, and deferred scope;
- preserves accepted Genesis ADRs or supersedes them explicitly;
- defines capability and provider boundaries;
- states data authority and dependency direction;
- addresses security, budget, migration, rollback, observability, and validation;
- avoids claiming unimplemented capabilities as current.
