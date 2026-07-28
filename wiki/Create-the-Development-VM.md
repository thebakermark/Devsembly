# Create the development VM

## Recommended Vultr settings

1. Create a new Cloud Compute instance.
2. Select a nearby region.
3. Select Ubuntu 24.04 LTS x64.
4. Start with at least 8 vCPU, 16 GB RAM, and 250 GB storage where available.
5. Add an SSH key rather than relying only on a root password.
6. Enable automatic backups if the budget allows, but still configure independent off-server backups.
7. Give the instance a clear label such as `devsembly-dev-01`.
8. Record the public IP address in a password manager or infrastructure inventory.

## First-login validation

Run from the Vultr web console if SSH is not yet available:

```bash
uname -a
lsb_release -a
free -h
df -h
ip addr
```

Do not install a public RDP or VNC server as the primary access method. Devsembly is designed around browser access and SSH tunnels or a secure reverse proxy.
