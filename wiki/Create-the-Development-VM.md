# Provision the Development Host

A **Development Host** is the server that runs Devsembly. It may be hosted by a cloud provider, virtualization platform, or compatible on-premises infrastructure.

Ubuntu LTS is currently required because it is the only host operating system built, tested, and supported by the project. Do not use a short-lived interim Ubuntu release unless the compatibility documentation explicitly marks it as tested.

## Baseline requirements

1. Provision a server with a supported Ubuntu LTS image.
2. Select a region or location appropriate for the users and connected services.
3. Start with at least 8 vCPU, 16 GB RAM, and 250 GB SSD-backed storage where available.
4. Add an SSH public key rather than relying only on a root password.
5. Enable provider backups or snapshots when appropriate, while still configuring independent off-host backups.
6. Give the host a clear label such as `devsembly-dev-01`.
7. Record the assigned address and provider details in a password manager or infrastructure inventory.
8. Limit firewall or security-group access to the approved access architecture.

## Provider-specific provisioning

Provider-specific instructions—such as instance types, image names, startup-script controls, firewalls, networking, and snapshots—belong in the provider guides under [`docs/providers/`](../docs/providers/).

Vultr is the first tested provider. Follow [`docs/providers/vultr.md`](../docs/providers/vultr.md) when provisioning there.

## First-login validation

Use the provider web console only when SSH is not yet available. After connecting to the Development Host, run:

```bash
uname -a
lsb_release -a
free -h
df -h
ip addr
```

Confirm that the detected Ubuntu release is supported, the expected CPU and memory are available, storage is correctly attached, and networking matches the planned access model.

Do not install a publicly exposed RDP or VNC service as the primary access method. Devsembly is designed around browser access, SSH tunnels, private networking, or a secure reverse proxy.
