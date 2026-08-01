# Claude Code provider

This provider is the first concrete implementation of Devsembly's AI Coding capability. The control plane remains provider-neutral; Claude Code is invoked only through the command-provider boundary.

## Development Host configuration

Copy `.env.example` to `.env` and set:

```bash
DEVSEMBLY_CODING_PROVIDER_COMMAND=/app/scripts/providers/claude-code.sh
DEVSEMBLY_CLAUDE_MODEL=sonnet
DEVSEMBLY_CLAUDE_MAX_TURNS=20
DEVSEMBLY_SOURCE_CONTROL_TOKEN=replace-with-a-limited-source-control-token
```

Never commit `.env`. The source-control token should be limited to reading the fixture repository,
pushing factory branches, and opening draft change requests. Do not configure a long-lived model key;
the deny-all first slice cannot pass it into the sandbox.

## Start or rebuild

```bash
docker build --file Dockerfile.sandbox --tag devsembly-sandbox:latest .
docker compose up -d --build
bash scripts/devsembly-status.sh
```

The controlled worker runtime must have access to a Docker daemon and CLI. Do not mount the Docker
socket into a task container. The Compose worker does not receive the host socket by default, so it
fails closed until the development host supplies the approved outer runtime boundary.

## Provider smoke check

Confirm the worker image contains the provider and CLI:

```bash
docker compose exec worker claude --version
docker compose exec worker bash -n /app/scripts/providers/claude-code.sh
```

The coding provider receives only a fixed credential-free environment. In particular,
`DEVSEMBLY_SOURCE_CONTROL_TOKEN`, database credentials, model keys, and unrelated host secrets are not
inherited by Claude Code. The control plane uses the source-control token separately to create the
traceable issue and publish the draft pull request.

## First live run (blocked pending controlled model egress)

Coding and validation now fail closed through the ephemeral, non-root Docker boundary required by the
trust model. The first slice intentionally uses `--network none` and provides no model credential, so
Claude Code cannot call an external model yet. Do not substitute bridge networking or a long-lived API
key. Run the credentialed fixture only after a controlled outer gateway supplies narrowly scoped,
short-lived task access and the Docker integration tests pass on the development host. Then use a
disposable fixture repository before targeting Devsembly.

Recommended first task:

```json
{
  "title": "Add fixture hello endpoint",
  "objective": "Add a /hello endpoint returning a JSON hello message and add tests.",
  "repository_url": "https://github.com/thebakermark/devsembly-factory-fixture",
  "base_branch": "main",
  "allowed_paths": ["src/", "tests/", "README.md"],
  "validation_commands": ["pytest -q", "ruff check src tests"],
  "max_repair_attempts": 2
}
```

## Safety expectations

Claude Code may read and edit only the task-specific checkout and run a small allowlist of development
commands inside the sandbox. Git metadata is read-only, the Docker socket is absent, network is denied,
and source-control publication stays in the controlled outer provider. Devsembly separately enforces
changed-path boundaries, bounded validation and repair, and draft-only publication.
