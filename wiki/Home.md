# Devsembly Wiki

Devsembly is a self-hosted, agent-powered software factory for planning, building, testing, reviewing, securing, deploying, and maintaining CompanyOS and other applications.

Devsembly runs on a **Development Host**. Ubuntu LTS is currently the only host operating system built, tested, and supported. Vultr is the first documented provider, but shared installation and operating guidance is provider-neutral.

## Start here

1. [Platform overview](Platform-Overview)
2. [Deployment architecture](Deployment-Architecture)
3. [Provision the Development Host](Create-the-Development-VM)
4. [Install the development workstation](Install-the-Development-Workstation)
5. [Configure GitHub](Configure-GitHub)
6. [Configure OpenClaw and agents](Configure-OpenClaw-and-Agents)
7. [Configure Archon workflows](Configure-Archon-Workflows)
8. [Install and configure Coolify](Configure-Coolify)
9. [Run your first project](Run-Your-First-Project)
10. [Daily operating guide](Daily-Operations)

## Terminology

- **Development Host:** the Ubuntu LTS server that runs Devsembly.
- **Development Workstation:** the machine or browser environment used to access and operate Devsembly.
- **Infrastructure provider:** the cloud, virtualization, or hosting platform supplying the Development Host.

Provider-specific steps belong in provider guides. Shared wiki pages should not hardcode a provider or Ubuntu point release unless that detail is operationally required.

## Core principles

- GitHub is the source of truth.
- Agents never approve their own work.
- No direct pushes to protected branches.
- Development agents never receive production credentials.
- Every change is tied to an issue, tests, review evidence, and a rollback plan.
- Production deployment requires explicit human approval.