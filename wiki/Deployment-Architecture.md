# Deployment architecture

## Recommended initial layout

### VM 1: Development control server

- Ubuntu 24.04 LTS
- 8 vCPU recommended
- 16–32 GB RAM
- 250 GB NVMe
- OpenClaw, Archon, Claude Code, Codex, code-server, Docker, Git worktrees, test services

### VM 2: Coolify management and staging

- Ubuntu 24.04 LTS
- 4 vCPU
- 8 GB RAM
- Coolify and staging workloads during the initial phase

### External services

- GitHub repositories and Actions
- S3-compatible off-server backup storage
- DNS provider
- Optional hosted model APIs

## Later production layout

Move production to its own server. Never install OpenClaw, Archon, code-server, development workspaces, or development credentials on the production server.
