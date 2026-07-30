# Devsembly Genesis Bootstrap v1

This directory contains the first executable bootstrap for turning a fresh **Development Host** running a supported Ubuntu LTS release into a reproducible Devsembly host.

Ubuntu LTS is currently the only host operating system built, tested, and supported by Devsembly. The installer is intentionally Ubuntu-specific. Infrastructure-provider details should remain outside the shared installation flow wherever practical.

## Included

- Base package installation
- Unattended security updates
- UFW firewall with SSH allowed
- Fail2ban SSH protection
- Docker Engine and Docker Compose plugin
- Dedicated `devsembly` service account
- Repository checkout under `/opt/devsembly`
- Systemd unit for the Docker Compose control plane
- Bootstrap status and log files
- Post-install validation command
- Cloud-init entry point compatible with supported providers

## Provision a new Development Host

1. Provision a server using a supported Ubuntu LTS image.
2. Follow the guide for your infrastructure provider in [`../docs/providers/`](../docs/providers/).
3. Supply `bootstrap/cloud-init.yaml` as startup-script or cloud-init user data when the provider supports it.
4. Wait for cloud-init to finish.
5. Connect through SSH and run:

```bash
sudo cloud-init status --wait
sudo devsembly-validate
sudo cat /var/lib/devsembly/bootstrap-status
```

Bootstrap output is stored at:

```text
/var/log/devsembly-bootstrap.log
```

## Direct installation

From an existing Development Host running a supported Ubuntu LTS release:

```bash
curl -fsSL https://raw.githubusercontent.com/thebakermark/Devsembly/main/bootstrap/devsembly-bootstrap.sh \
  -o /tmp/devsembly-bootstrap.sh
sudo bash /tmp/devsembly-bootstrap.sh
```

## Configuration variables

The installer accepts these environment variables:

| Variable | Default |
|---|---|
| `DEVSEMBLY_USER` | `devsembly` |
| `DEVSEMBLY_HOME` | `/opt/devsembly` |
| `DEVSEMBLY_REPO` | `https://github.com/thebakermark/Devsembly.git` |
| `DEVSEMBLY_REF` | `main` |
| `LOG_FILE` | `/var/log/devsembly-bootstrap.log` |
| `STATUS_FILE` | `/var/lib/devsembly/bootstrap-status` |

## Current boundary

This v1 bootstrap prepares and secures the Development Host and starts the repository's development Compose stack when `infrastructure/docker/compose.dev.yaml` is present. Domain-based HTTPS, secret-provider enrollment, off-host backups, and the browser setup wizard belong to later bootstrap iterations.

Provider-specific provisioning, networking, image names, plans, and startup-script procedures belong in provider guides. See [`../docs/platform-support.md`](../docs/platform-support.md) for the support policy.