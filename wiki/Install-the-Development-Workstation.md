# Install the development workstation

The final installer will automate this procedure. Until then, this page defines the intended result.

## Installed components

- Docker Engine and Compose plugin
- Git and GitHub CLI
- Node.js LTS and Python 3
- code-server
- Claude Code
- OpenAI Codex CLI
- OpenClaw
- Archon
- Playwright dependencies
- Trivy, Semgrep, and Gitleaks
- PostgreSQL, Redis, and MinIO development services

## Installation rules

- Run development tools under a normal sudo-enabled user, not root.
- Store repositories below `/srv/devsembly/workspaces` or the user's home directory.
- Store secrets outside repositories.
- Give each agent a separate worktree and task directory.
- Keep production credentials off this VM.

## Validation checklist

```bash
docker version
docker compose version
git --version
gh --version
node --version
python3 --version
```

Then run the repository validation:

```bash
make validate
```
