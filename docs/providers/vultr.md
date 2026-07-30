# Provisioning a Development Host on Vultr

Vultr is the first infrastructure provider used to build and test Devsembly. This guide contains only Vultr-specific provisioning details. The shared installer and operating documentation should refer to the machine as the **Development Host**.

## Supported host image

Select a supported Ubuntu LTS server image. Do not select a short-lived interim Ubuntu release for a production Devsembly Host unless the project compatibility matrix explicitly lists it as tested.

## Recommended baseline

Use a server plan that satisfies the current Devsembly resource requirements. Capacity depends on which optional services are enabled, the number of concurrent agent workflows, and whether build workloads run on the same host.

At minimum, confirm that the Development Host has:

- sufficient CPU and memory for Docker and the enabled services;
- SSD-backed storage with room for images, build artifacts, logs, and backups;
- a public IPv4 or IPv6 address when remote access is required;
- SSH access using a trusted key;
- firewall rules limited to the ports required by the chosen access architecture.

## Provisioning flow

1. Create a new Vultr instance.
2. Choose a supported Ubuntu LTS image.
3. Select an appropriate region and server plan.
4. Add the administrator SSH public key.
5. Configure networking and firewall rules.
6. Attach the approved Devsembly startup script or cloud-init configuration when using automated first boot.
7. Provision the instance and record its assigned address.
8. Continue with the shared Development Host installation and verification instructions.

## Provider-specific boundaries

Vultr-specific identifiers, API endpoints, plans, regions, firewall objects, snapshots, and startup-script IDs belong in provider configuration or this guide. They should not be embedded in the core Devsembly application or general installation documentation.

## Validation before marking changes supported

Any change to Vultr provisioning should validate:

- first boot completes successfully;
- SSH and the selected private-access method work;
- Docker installs and starts;
- Devsembly services pass health checks;
- firewall rules expose only approved endpoints;
- backups or snapshots can be restored;
- the wiki and related how-to guides match the implemented process.
