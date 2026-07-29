# Devsembly Genesis Bootstrap v1

This directory contains the first executable bootstrap for turning a fresh Ubuntu Server 24.04 LTS VM into a reproducible Devsembly host.

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
- Vultr-compatible cloud-init entry point

## New Vultr VM installation

1. Create an Ubuntu Server 24.04 LTS VM.
2. Use the contents of `bootstrap/cloud-init.yaml` as the Vultr startup script or cloud-init user data.
3. Wait for cloud-init to finish.
4. Log in through SSH and run:

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

From an existing Ubuntu 24.04 host:

```bash
curl -fsSL https://raw.githubusercontent.com/thebakermark/Devsembly/build/genesis-bootstrap-v1/bootstrap/devsembly-bootstrap.sh \
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

This v1 bootstrap prepares and secures the host and starts the repository's development Compose stack when `infrastructure/docker/compose.dev.yaml` is present. Domain-based HTTPS, secret-provider enrollment, off-host backups, and the browser setup wizard belong to the next bootstrap iterations.
