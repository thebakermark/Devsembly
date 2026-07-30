# System Architecture

This page is the concise repository overview. The canonical authority, dependency rules,
current-versus-future labels, and data ownership are defined in
[Genesis Book II](../genesis/book-2-architecture.md).

## Logical architecture

```text
Human owner / operator
        |
Conversational and application interfaces
        |
Executive coordination and application services
        |
Domain capabilities, policy, budget, and Organizational Genome
        |
Kernel contracts
        |
Provider adapters
        |
External providers and infrastructure
```

Human authority controls intent, delegation, budgets, high-risk approvals, and production
release. Applications and business modules consume capabilities without depending on
provider products.

## Genesis v0.1 runtime

Genesis is a Python/FastAPI modular monolith plus workers. It uses:

- PostgreSQL with SQLAlchemy and Alembic for canonical structured state;
- Temporal behind the workflow-provider interface for durable execution;
- an external OIDC provider for authentication and internal Devsembly authorization;
- a transactional outbox for domain event delivery;
- MinIO-compatible object storage for large evidence;
- Redis only for ephemeral caching and coordination;
- Docker and Compose for the reference local deployment.

These decisions are binding through
[`docs/architecture/decisions/`](decisions/README.md). The broader Kernel, Executive Core,
MemoryOS, knowledge graph, and plugin model are staged in the Genesis Library and are not
claimed as complete runtime services.

## Planes

### Control plane

The control plane coordinates organization-scoped work, capability selection, policy,
budgets, workflows, approvals, decisions, and audit. It does not contain customer-product
business logic.

### Execution plane

Coding and validation agents operate in isolated workspaces or containers with scoped
credentials, bounded tools, and explicit delegation. Implementation and high-risk review
remain separate.

### Delivery plane

Source-control, independent-validation, and deployment providers manage repository
evidence, checks, preview, staging, rollback, and approved promotion. The initial
adapters may use GitHub and Coolify, but core workflow depends on provider contracts.

### Knowledge plane

Canonical knowledge is versioned, attributable, policy-controlled, and linked to
evidence. Repository documents, decisions, source-control records, database records, and
object evidence have explicit authority scopes. Agent context and chat history are not
the sole source of truth.

## Current development-factory mapping

The current workstation documentation names initial tools such as OpenClaw for
conversational intake, Archon for workflow specification, coding agents for execution,
GitHub for source-control evidence, and Coolify for deployment. These are provider
choices and development-factory components, not permanent platform boundaries or runtime
dependencies of products built by Devsembly.

## Initial deployment topology

- **Development Host:** control-plane application, workflow worker, browser IDE, coding
  agents, and local test services
- **Deployment management:** isolated deployment-provider control
- **Staging:** production-like validation without production data or credentials
- **Production:** isolated from development agents and promoted only with human authority

Topology may evolve only through evidence, budget analysis, security review, and an ADR
when the change is architecturally significant.
