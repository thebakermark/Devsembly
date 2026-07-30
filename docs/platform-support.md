# Platform support

## Standard terminology

### Development Host

A **Development Host** is the Linux server that runs the Devsembly platform. It may be a cloud virtual machine, a virtualized on-premises server, or compatible dedicated hardware.

Shared documentation should use **Development Host**, **Devsembly Host**, or **host** instead of repeatedly naming a particular cloud provider or VM product.

### Development Workstation

A **Development Workstation** is the user-facing machine used to access Devsembly, GitHub, code-server, dashboards, and related tools. It may be a local desktop, laptop, or remote desktop environment.

## Current support matrix

| Layer | Current status | Notes |
|---|---|---|
| Host operating system | Ubuntu LTS required | Ubuntu is the only host OS currently built, tested, and supported. |
| Cloud provider | Provider-agnostic core | Vultr is the first documented and tested provider. |
| Application services | Docker-based | Most services are portable across compatible Docker hosts. |
| Installer | Ubuntu-specific | Uses Ubuntu package management and host service conventions. |
| Other Linux distributions | Planned | Support must not be claimed until installation and upgrade paths are tested. |

## Documentation policy

Shared documentation must:

- refer to the machine as the Development Host;
- state Ubuntu LTS when the host operating-system requirement matters;
- avoid naming Vultr unless the instruction is specific to Vultr;
- link to a provider guide for provider-specific provisioning, networking, DNS, firewall, image, or startup-script steps;
- avoid hardcoding a specific Ubuntu point release in general instructions unless that exact release is required;
- distinguish tested support from planned or experimental support.

## Installer policy

The installer may use Ubuntu-specific commands because Ubuntu is currently required. It should still isolate provider-specific behavior from the core installation flow.

The installer should detect the host operating system and fail clearly when the operating system is unsupported. Future distribution support can be added through separate adapters without changing the containerized application architecture.

Conceptual layout:

```text
install/
  common/
  ubuntu/
  debian/        # future
  rocky/         # future

providers/
  generic/
  vultr/
  digitalocean/  # future
  aws/           # future
```

## Version wording

Use wording such as:

> Provision a Development Host running a supported Ubuntu LTS release.

Avoid wording such as:

> Create an Ubuntu 25.xx Vultr VM.

A specific release should only appear in a compatibility matrix, tested configuration, migration note, or provider guide where it is operationally relevant.

## Adding a provider

Adding a new infrastructure provider requires:

1. a provider-specific provisioning guide;
2. validation of networking, DNS, firewall, storage, and startup-script behavior;
3. updates to the support matrix;
4. updates to the wiki and related how-to documentation;
5. automated installation and smoke-test evidence before the provider is marked supported.
