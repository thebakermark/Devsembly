# Claude Code provider

This provider is the first concrete implementation of Devsembly's AI Coding capability. The control plane remains provider-neutral; Claude Code is invoked only through the command-provider boundary.

## Development Host configuration

Copy `.env.example` to `.env` and set:

```bash
DEVSEMBLY_CODING_PROVIDER_COMMAND=/app/scripts/providers/claude-code.sh
ANTHROPIC_API_KEY=replace-with-an-anthropic-console-api-key
DEVSEMBLY_CLAUDE_MODEL=sonnet
DEVSEMBLY_CLAUDE_MAX_TURNS=20
DEVSEMBLY_SOURCE_CONTROL_TOKEN=replace-with-a-limited-source-control-token
```

Never commit `.env`. The source-control token should be limited to reading the fixture repository, pushing factory branches, and opening draft change requests.

## Start or rebuild

```bash
docker compose up -d --build
bash scripts/devsembly-status.sh
```

## Provider smoke check

Confirm the worker image contains the provider and CLI:

```bash
docker compose exec worker claude --version
docker compose exec worker bash -n /app/scripts/providers/claude-code.sh
```

The coding provider receives only an explicit environment allowlist. In particular, `DEVSEMBLY_SOURCE_CONTROL_TOKEN`, database credentials, and unrelated host secrets are not inherited by Claude Code. The control plane uses the source-control token separately to create the traceable issue and publish the draft pull request.

## First live run

Use a disposable fixture repository before targeting Devsembly. Submit a bounded task with explicit allowed paths and validation commands. The expected outcome is a traceable issue, factory branch, draft change request, validation evidence, and—when canonical project IDs are supplied—a governed MemoryOS proposal. The system does not merge or deploy the result.

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

Claude Code may read and edit the isolated checkout and run a small allowlist of development commands. It is explicitly denied source-control publication commands and web tools. Devsembly separately enforces changed-path boundaries, validation, retry limits, and draft-only publication.
