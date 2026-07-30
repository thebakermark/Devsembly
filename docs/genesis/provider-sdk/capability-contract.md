# Capability Contract

**Status:** Binding baseline
**Contract version:** 0.1.0

## Definition

A capability contract declares:

- stable capability ID, name, owner, semantic version, and lifecycle;
- outcome and boundary;
- required and optional operations;
- typed request, response, error, and event schemas;
- authentication and authorization requirements;
- data ownership, classification, retention, and residency;
- timeout, cancellation, retry, and idempotency behavior;
- health and service-level indicators;
- usage and cost units;
- observability and evidence;
- conformance tests and compatibility rules.

## Operation definition

Each operation identifies whether it reads or mutates, required authority, input and
output schemas, side effects, provider correlations, idempotency mode, default deadline,
retryable errors, events, cost estimate availability, and evidence.

## Required versus optional

Required operations must exist for any conforming provider at the declared contract
version. Optional operations use named feature flags with their own versions and tests.
An absent optional feature returns `unsupported`, never a partial silent substitute.

## Evolution

Backward-compatible additions increment the minor version. Clarifications and
nonbehavioral fixes increment the patch version. Breaking request, response, semantic,
security, or side-effect changes require a major version and migration plan.

## Selection

Capability fit is evaluated before provider selection. Provider extensions may improve
fitness but cannot become an undeclared requirement in core workflows.
