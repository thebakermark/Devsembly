# ADR 0003 — OIDC-Based External Identity

- **Status:** Accepted
- **Date:** 2026-07-30
- **Decision owners:** Devsembly Architecture
- **Applies to:** Genesis v0.1

## Context

Devsembly needs secure user authentication without building and maintaining password storage, account recovery, multifactor authentication, or federation infrastructure during Genesis. It must support future enterprise identity providers while remaining usable for a solo founder and small internal team.

Authentication and authorization are separate concerns. External identity should establish who the user is; Devsembly must still decide what that identity may do within an organization, project, budget, workflow, or approval boundary.

## Decision

Adopt **OpenID Connect (OIDC) and OAuth 2.0** as the identity contract.

For Genesis:

- use an external OIDC provider for interactive authentication;
- support GitHub identity as the initial bootstrap sign-in option;
- map external subject identifiers to internal Devsembly principals;
- keep organization membership, roles, delegated authority, and approval permissions inside Devsembly;
- use short-lived sessions or tokens and standards-based validation;
- do not implement local password authentication.

The application must depend on a Devsembly identity-provider interface rather than provider-specific APIs. Additional providers can later include Google Workspace, Microsoft Entra ID, Keycloak, Authentik, or another conforming OIDC service.

## Alternatives considered

### Custom username and password authentication

Rejected because secure password storage, recovery, MFA, breach monitoring, and account lifecycle management are not differentiating Genesis capabilities.

### Self-hosted Keycloak or Authentik as mandatory infrastructure

Both are viable future providers, but making either mandatory would increase deployment and administrative overhead for the first vertical slice.

### GitHub-specific authentication embedded throughout the application

Rejected because it would couple Devsembly authorization and account models to one provider.

## Consequences

### Positive

- avoids custom credential handling;
- supports future enterprise federation;
- lower implementation and security burden;
- clean separation between authentication and authorization;
- initial sign-in aligns with the source-control-centered workflow.

### Negative

- interactive login depends on an external provider;
- provider outages can prevent new sessions;
- local and automated testing require a mock OIDC issuer;
- account linking and provider migration need explicit rules.

## Budget impact

The initial GitHub OIDC/OAuth path has no additional monthly infrastructure cost. Paid enterprise identity services are deferred until customer or compliance requirements justify them.

## Security impact

- validate issuer, audience, signature, expiry, nonce, and state;
- use PKCE for browser-based authorization flows;
- store no provider passwords or long-lived browser tokens;
- encrypt refresh tokens when persistence is unavoidable;
- require explicit account-linking verification;
- log authentication and authorization events without recording secrets;
- preserve a human-controlled emergency access procedure for self-hosted deployments.

## Implementation constraints

- internal principals use stable Devsembly IDs, not email addresses, as primary keys;
- external identities are keyed by issuer plus subject;
- authorization policies are evaluated inside Devsembly;
- service accounts and agents use separate machine-identity contracts;
- tests must use a local mock issuer and deterministic claims;
- adding a provider-specific capability requires an adapter, not changes to domain authorization rules.

## Validation

This decision is validated when a user can authenticate through the initial provider, create or join an authorized organization, be denied access outside assigned scope, approve only within delegated authority, and have all access decisions recorded in the audit trail.

## Review triggers

Review when offline authentication, customer-managed identity, SAML, mandatory MFA policy control, or regulated break-glass requirements become necessary.
