# Deployment architecture

## Recommended initial layout

### Development Host: control plane and development services

- Supported Ubuntu LTS release
- 8 vCPU recommended
- 16–32 GB RAM
- 250 GB NVMe or equivalent SSD-backed storage
- OpenClaw, Archon, Claude Code, Codex, code-server, Docker, Git worktrees, and test services

The Development Host may run on any validated infrastructure provider. Provider selection should not change the shared Devsembly application architecture.

### Staging Host: Coolify management and staging

- Supported Ubuntu LTS release
- 4 vCPU
- 8 GB RAM
- Coolify and staging workloads during the initial phase

This may initially be combined with the Development Host for testing, but separating it reduces operational and security risk.

### External services

- GitHub repositories and Actions
- S3-compatible off-host backup storage
- DNS provider
- Optional hosted model APIs

## Provider boundary

Provider-specific plans, images, firewalls, private networking, snapshots, object storage, and startup-script identifiers belong in provider configuration and provider-specific documentation. Shared architecture documentation should describe hosts and required capabilities rather than a particular vendor's product names.

## Later production layout

Move production to its own **Production Host**. Never install OpenClaw, Archon, code-server, development workspaces, or development credentials on the Production Host.

Production operating-system and provider support must be documented and validated separately before a configuration is marked supported.
