# Capability Registry

**Status:** Proposed; static configuration is sufficient for Genesis
**Version:** 0.1.0

## Purpose

The registry associates a stable capability contract with compatible provider instances.
It does not select business outcomes or grant provider access.

## Capability definition

A definition contains:

- stable ID, name, semantic version, owner, and lifecycle;
- outcome, required and optional operations;
- input, output, error, event, and evidence contracts;
- security, data, policy, budget, and service-level requirements;
- dependencies and compatibility ranges;
- conformance suite and current maturity.

## Provider registration

A provider registration declares provider ID, adapter version, capability versions,
configuration schema, required permissions, environment scope, health endpoint,
conformance evidence, cost metadata, support status, and replacement guide.

## Resolution

Resolution filters by organization and environment policy, compatible contract version,
required operations, health, conformance, data location, security, support, and budget.
Tie-breaking rules must be deterministic and explainable. No match returns
`unsupported` or `unavailable`; it must not silently choose an incompatible provider.

## Genesis posture

Genesis uses typed configuration that maps one provider to each required capability.
Dynamic discovery, scoring, and multi-provider routing remain proposed until justified.

## Validation

Tests cover duplicate IDs, incompatible versions, missing operations, unhealthy
providers, policy and budget exclusion, deterministic selection, and safe removal.
