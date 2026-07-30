# Provider Authentication Contract

**Status:** Binding baseline
**Contract version:** 0.1.0

## Requirements

Providers use the least-privilege approved authentication method. Preferred order is
workload identity or short-lived federation, scoped application installation, short-lived
token, and long-lived secret only when no safer option is practical.

Credential material remains in the secret capability or provider runtime boundary.
Domain and workflow histories receive references and identity metadata, never raw secret
values.

## Credential metadata

Record credential reference, principal type, issuer, provider account, organization and
environment scope, permissions, created and expiry times, rotation and revocation policy,
and owner. Do not store the credential value in metadata.

## Runtime behavior

Adapters validate scope before use, refresh only within policy, avoid logging credentials,
distinguish authentication from authorization, and stop automatic retries on invalid or
revoked credentials. Provider permission changes produce health and audit signals.

## Validation

Tests cover missing, expired, revoked, wrong-environment, insufficient-scope, rotation,
concurrent refresh, redaction, account mismatch, and revocation during active work.
