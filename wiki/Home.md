# Devsembly Wiki

Devsembly is a self-hosted, agent-powered software factory for planning, building, testing, reviewing, securing, deploying, and maintaining software products.

Devsembly runs on a **Development Host**. Ubuntu LTS is currently the only host operating system built, tested, and supported. Infrastructure-provider details belong in dedicated provider guides; shared installation and operating guidance remains provider-neutral.

## Start here

1. [Platform overview](Platform-Overview)
2. [Capability and provider model](Capability-and-Provider-Model)
3. [Deployment architecture](Deployment-Architecture)
4. [Provision the Development Host](Create-the-Development-VM)
5. [Install the development workstation](Install-the-Development-Workstation)
6. Configure the Source Control Provider
7. Configure the conversational intake and AI Coding Providers
8. Configure the Workflow Provider
9. Configure the Deployment Provider
10. [Run your first project](Run-Your-First-Project)
11. [Daily operating guide](Daily-Operations)

Existing provider-specific setup pages remain implementation guides. Their titles may contain the current implementation name, but the core workflow and architecture should refer to the capability.

## Terminology

- **Development Host:** the Ubuntu LTS server that runs Devsembly.
- **Development Workstation:** the machine or browser environment used to access and operate Devsembly.
- **Capability:** a stable function required by Devsembly, such as source control, deployment, or secrets management.
- **Provider interface:** the stable contract used by Devsembly core services.
- **Provider implementation:** the selected product or service fulfilling a capability.
- **Infrastructure Provider:** the cloud, virtualization, or hosting platform supplying the Development Host.

Provider-specific steps belong in provider guides. Shared wiki pages should not hardcode a product, provider, or Ubuntu point release unless that detail is operationally required.

## Core principles

- The Source Control Provider is the authoritative system of record.
- Capabilities are stable; implementations are replaceable.
- Agents never approve their own work.
- No direct pushes to protected branches.
- Development agents never receive production credentials.
- Every change is tied to a work item, tests, review evidence, and a rollback plan.
- Production deployment requires explicit human approval.
