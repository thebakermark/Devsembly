# Capability and provider model

Devsembly documentation describes **capabilities** first and names specific products only when implementation details matter.

## Why

Products, vendors, and project names can change. The platform should remain understandable and maintainable when an implementation is renamed, replaced, self-hosted, or supplied by an enterprise customer.

## Core rule

Shared documentation should say what capability is being configured:

- Source Control Provider
- AI Coding Provider
- Workflow Provider
- Knowledge Provider
- Deployment Provider
- Infrastructure Provider
- Identity Provider
- Secrets Provider
- Observability Provider
- Database Provider
- Object Storage Provider
- Notification Provider
- Browser IDE Provider
- Backup Provider
- DNS Provider

Specific product names belong in dedicated provider guides, compatibility matrices, installation instructions, adapter configuration, and migration notes.

## Three layers

### 1. Capability

The stable function Devsembly needs, such as source control or deployment.

### 2. Provider interface

The contract the Devsembly core uses, such as `SourceControlProvider` or `DeploymentProvider`.

### 3. Provider implementation

The selected product or service implementing that contract. Implementations are chosen through configuration and may change over time.

## Documentation example

Preferred shared wording:

> Configure the Source Control Provider and verify repository access.

Provider-guide wording:

> Follow the selected implementation guide to create credentials and configure repository access.

Avoid making a temporary product name appear to be a permanent architectural requirement.

## Support requirements

A provider implementation is marked supported only when it has:

- a documented adapter and configuration schema;
- least-privilege permissions guidance;
- health and readiness checks;
- automated contract and integration tests;
- failure, retry, migration, and rollback behavior;
- provider-specific installation and operations documentation;
- verified evidence on a supported Development Host.

## Related documentation

- [Platform overview](Platform-Overview)
- [Deployment architecture](Deployment-Architecture)
- [Provision the Development Host](Create-the-Development-VM)
