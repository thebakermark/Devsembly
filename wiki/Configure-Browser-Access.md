# Configure browser access

## Primary access

Use code-server for daily coding and terminal access. Protect it with HTTPS and strong authentication through a reverse proxy or identity-aware access layer.

Suggested hostname:

```text
code.dev.example.com
```

## Management dashboards

Suggested endpoints:

- `code.dev.example.com` — browser IDE
- `agents.dev.example.com` — OpenClaw control interface
- `deploy.dev.example.com` — Coolify
- `monitor.dev.example.com` — Grafana or monitoring dashboard

## Emergency access

Keep the Vultr web console available for recovery when SSH, DNS, or the reverse proxy is unavailable.

## Security rules

- Do not expose VNC directly.
- Do not expose PostgreSQL, Redis, Docker, or MinIO administrative ports publicly.
- Restrict dashboards by authentication and, where practical, IP or private-network controls.
