# ADR 0011 — Capability-Based Architecture

- **Status:** Accepted
- **Date:** 2026-07-30
- **Decision owners:** Devsembly Architecture
- **Applies to:** Platform and product architecture

## Context

Product names, vendors, modules, teams, and deployment topology change faster than the
outcomes the organization needs. Designing around current tools makes documentation,
workflows, and applications brittle.

## Decision

Devsembly architecture is organized around named capabilities with owners, outcomes,
contracts, policies, measures, dependencies, maturity, and provider implementations.
Capabilities precede provider and build-versus-adopt selection.

Applications consume capabilities. Providers implement capability contracts. The
capability catalog records current, planned, proposed, and deferred maturity honestly.

## Consequences

Architecture remains stable while implementations evolve. Capability modeling and
contract ownership require ongoing governance, and overly broad capabilities must be
split when they obscure responsibility.

## Alternatives considered

- **Vendor-based architecture:** rejected as temporary and lock-in prone.
- **Application-based architecture:** rejected because capabilities cross interfaces.
- **Microservice-based catalog:** rejected because deployment units are not business
  capabilities.

## Security impact

Each capability declares data, permissions, trust boundaries, abuse cases, and evidence.
Provider selection cannot weaken the capability's security contract.

## Budget impact

Capability-level cost makes build, buy, self-host, and defer decisions comparable.
Maturity and service-level targets must fit the approved budget.

## Implementation constraints

- Capability names and versions are stable identifiers.
- Contracts define required and optional operations.
- Catalog maturity follows evidence.
- A deployment unit may implement several capabilities in Genesis.
- Provider product names remain in adapter and implementation documentation.

## Validation criteria

Architecture and workflow specifications resolve external needs through named capability
contracts, and provider substitution does not change unrelated domain policy.

## Review triggers

Review when capability boundaries repeatedly overlap, lack ownership, or fail to support
measurable outcomes.

## References

- [Capability catalog](../../genesis/capability-catalog.md)
- [Provider SDK](../../genesis/provider-sdk/README.md)
- [ADR 0005](0005-provider-independence.md)
