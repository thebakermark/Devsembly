# Kernel Configuration

**Status:** Proposed contract; environment configuration exists in Genesis
**Version:** 0.1.0

## Principles

Configuration is typed, validated before readiness, environment-scoped, auditable by
fingerprint, and separate from secrets. Defaults are safe and budget-aware. Unknown keys
fail in strict production mode.

## Precedence

1. Compiled safe defaults
2. Versioned non-secret configuration
3. Environment-specific non-secret configuration
4. Runtime environment variables
5. Authorized administrative override

Secret references resolve through the secret provider after non-secret validation.
Secret values never appear in effective-configuration output.

## Required metadata

Every setting declares key, type, owner, description, default, required environments,
sensitivity, mutability, validation, deprecation, and restart behavior.

## Change behavior

Immutable and startup settings require controlled restart. Reloadable settings validate
atomically and roll back on failure. Changes to provider, policy, budget, identity,
network, or retention configuration create audit evidence and may require approval.

## Validation

Tests cover missing required values, unknown keys, invalid types and ranges, secret
redaction, precedence, deprecated settings, reload rollback, fingerprint stability, and
budget-safe defaults.
