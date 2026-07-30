# Provider Configuration Contract

**Status:** Binding baseline
**Contract version:** 0.1.0

## Schema

Configuration is defined by a versioned JSON Schema or equivalent typed contract. Every
field declares type, purpose, safe default, required scope, sensitivity, mutability,
validation, and deprecation.

## Separation

Non-secret configuration may be versioned. Secret fields contain references, not values.
Provider configuration is scoped by organization and environment and must not silently
fall back to another tenant or production endpoint.

## Validation stages

1. Schema and unknown-key validation
2. Cross-field and range validation
3. Secret-reference existence and scope validation
4. Permission and endpoint validation
5. Safe functional probe where allowed
6. Budget and support-policy validation

Validation output is sanitized and does not persist secret values.

## Change

Each field states whether change is live, drain-required, restart-required, or
migration-required. Effective configuration has a stable fingerprint for audit and
support evidence.
