# Claude Code provider

This provider is the first concrete implementation of Devsembly's AI Coding capability. The control plane remains provider-neutral; Claude Code is invoked only through the command-provider boundary.

## Development Host configuration

Copy `.env.example` to `.env` and set:

```bash
DEVSEMBLY_CODING_PROVIDER_COMMAND=/app/scripts/providers/claude-code.sh
DEVSEMBLY_CLAUDE_MODEL=sonnet
DEVSEMBLY_CLAUDE_MAX_TURNS=20
DEVSEMBLY_SOURCE_CONTROL_TOKEN=replace-with-a-limited-source-control-token
DEVSEMBLY_MODEL_GATEWAY_URL=http://model-gateway:8080
DEVSEMBLY_SANDBOX_NETWORK=devsembly-sandbox-egress
DEVSEMBLY_MODEL_GATEWAY_SECRET=replace-with-at-least-32-random-bytes
DEVSEMBLY_MODEL_PROVIDER_API_KEY=replace-with-a-disposable-provider-key
DEVSEMBLY_MODEL_PROVIDER_ALLOWED_HOSTS=api.anthropic.com
DEVSEMBLY_MODEL_GATEWAY_ALLOWED_MODELS=replace-with-an-exact-model-id
```

Never commit `.env`. The source-control token should be limited to reading the fixture repository,
pushing factory branches, and opening draft change requests. Use only a disposable provider key for
commissioning. The gateway holds that key; the task receives only a five-minute signed token.

## Start or rebuild

```bash
docker build --file Dockerfile.sandbox --tag devsembly-sandbox:latest .
docker compose --profile model-egress up -d --build
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

The coding provider receives a fixed environment plus `ANTHROPIC_BASE_URL` and a short-lived
`ANTHROPIC_AUTH_TOKEN` for the internal gateway. `DEVSEMBLY_SOURCE_CONTROL_TOKEN`, the provider API
key, database credentials, and unrelated host secrets are not inherited by Claude Code. The control
plane uses the source-control token separately to create the traceable issue and publish the draft
pull request.

## First live run

Coding and validation fail closed through the ephemeral, non-root Docker boundary required by the
trust model. Validation uses `--network none`. Coding may use only the Docker-internal gateway network,
and the runtime rejects a network that is missing or not internal. The gateway fixes the upstream
origin, path set, and model allowlist and never exposes its provider key to the task. Do not substitute
bridge networking or a long-lived key inside the sandbox. Run the credentialed fixture only after the
Docker and gateway tests pass on the controlled development host, using a disposable repository and
disposable provider/source-control access before targeting Devsembly.

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

The repository provides two commissioning entrypoints:

```bash
# On a MacBook control console:
bash scripts/commission-from-macbook.sh <tailscale-host-or-ip> [ssh-user]

# Or directly on the development VM:
bash scripts/commission-first-run.sh
```

The MacBook entrypoint finds or recovers the established checkout, refuses to overwrite local
changes, fast-forwards only the existing PR #17 branch, and starts the VM workflow over SSH. The VM
entrypoint performs command, Docker, repository, branch, fixture, gateway-network, trusted-worker,
and API readiness checks before submitting work.

The script asks through masked terminal prompts for a temporary human OIDC access token, a temporary
GitHub token restricted to the public disposable fixture repository, and a disposable Anthropic API
key. It also asks for the exact OIDC issuer, API audience, and allowed model identifier. Never paste
these credentials into chat. The fixture repository must be publicly readable for credential-free
checkout and permit the temporary GitHub token to create issues, branches, commits, and draft pull
requests. If the standard `thebakermark/devsembly-factory-fixture` repository does not exist, the
workflow can create and initialize it as a public disposable repository after an explicit terminal
confirmation; that one-time path requires a token authorized to create a public repository. A
narrower repository-only token is preferred after the fixture exists.

Commissioning uses `docker-compose.commissioning.yml` in addition to the default Compose file. Only
the trusted worker receives the host Docker socket and a host-visible temporary-workspace mount. A
task sandbox receives neither the socket nor source-control, model-provider, OIDC, database, cloud,
or control-plane credentials. Normal Compose startup does not apply this commissioning override and
therefore remains fail-closed.

On success, sanitized evidence is written under `commissioning-evidence/<UTC timestamp>/`. The
temporary secrets file is removed after the stack stops. Use `--keep-stack` only for controlled
inspection; it deliberately retains the credential file until the operator stops the stack and
removes that file.

## Safety expectations

Claude Code may read and edit only the task-specific checkout and run a small allowlist of development
commands inside the sandbox. Git metadata is read-only, the Docker socket is absent, network is denied,
and source-control publication stays in the controlled outer provider. Devsembly separately enforces
changed-path boundaries, bounded validation and repair, and draft-only publication.
