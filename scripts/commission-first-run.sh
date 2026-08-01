#!/usr/bin/env bash
set -Eeuo pipefail

ROOT_DIR="${DEVSEMBLY_ROOT:-$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)}"
COMPOSE=(docker compose -f docker-compose.yml -f docker-compose.commissioning.yml)
ENV_FILE="$ROOT_DIR/.env.commissioning"
EVIDENCE_ROOT="$ROOT_DIR/commissioning-evidence"
WORKSPACE_ROOT="${DEVSEMBLY_WORKSPACE_ROOT:-/var/lib/devsembly/workspaces}"
API_URL="http://127.0.0.1:${DEVSEMBLY_API_PORT:-8000}"
FIXTURE_REPOSITORY_URL="${DEVSEMBLY_FIXTURE_REPOSITORY_URL:-https://github.com/thebakermark/devsembly-factory-fixture}"
KEEP_STACK=false
PREFLIGHT_ONLY=false

usage() {
  cat <<'EOF'
Usage: bash scripts/commission-first-run.sh [--preflight] [--keep-stack]

Commission the controlled development host and run one disposable, governed
software-delivery fixture. Secrets are collected through masked prompts and are
removed from disk when the stack stops.

Options:
  --preflight   Check repository-independent command prerequisites only.
  --keep-stack  Leave services and the trusted host worker running for inspection.
  --help        Show this help.
EOF
}

log() {
  printf '[commission] %s\n' "$*"
}

fail() {
  printf '[commission] ERROR: %s\n' "$*" >&2
  exit 1
}

require_command() {
  command -v "$1" >/dev/null 2>&1 || fail "Required command is unavailable: $1"
}

for argument in "$@"; do
  case "$argument" in
    --preflight) PREFLIGHT_ONLY=true ;;
    --keep-stack) KEEP_STACK=true ;;
    --help|-h) usage; exit 0 ;;
    *) fail "Unknown option: $argument" ;;
  esac
done

for command in bash curl docker git python3; do
  require_command "$command"
done
docker compose version >/dev/null 2>&1 || fail "Docker Compose v2 is required"

if [[ "$PREFLIGHT_ONLY" == true ]]; then
  log "Command preflight passed."
  exit 0
fi

cd "$ROOT_DIR"
[[ -f AGENTS.md && -f .devsembly/project-state.json ]] || fail "Run from a Devsembly checkout"
[[ -S /var/run/docker.sock ]] || fail "The host Docker socket is unavailable"
docker info >/dev/null 2>&1 || fail "The current user cannot access the Docker daemon"
[[ -z "$(git status --porcelain)" ]] || fail "The Devsembly checkout has uncommitted changes"

CURRENT_BRANCH="$(git branch --show-current)"
[[ "$CURRENT_BRANCH" == "docs/genesis-reference-implementation-plan" ]] || \
  fail "Expected branch docs/genesis-reference-implementation-plan, found ${CURRENT_BRANCH:-detached HEAD}"

read -r -p "Public disposable fixture repository URL [$FIXTURE_REPOSITORY_URL]: " entered_repo
FIXTURE_REPOSITORY_URL="${entered_repo:-$FIXTURE_REPOSITORY_URL}"
[[ "$FIXTURE_REPOSITORY_URL" == https://github.com/* ]] || \
  fail "The fixture must be a public HTTPS GitHub repository"
read -r -s -p "Temporary GitHub fixture token: " SOURCE_CONTROL_TOKEN
printf '\n'
[[ ${#SOURCE_CONTROL_TOKEN} -ge 20 ]] || fail "GitHub fixture token is unexpectedly short"

github_api() {
  local method=$1
  local path=$2
  local body_file=${3:-}
  local curl_args=(--fail-with-body --silent --show-error --request "$method")
  if [[ -n "$body_file" ]]; then
    curl_args+=(--header "content-type: application/json" --data-binary "@$body_file")
  fi
  {
    printf 'header = "Authorization: Bearer %s"\n' "$SOURCE_CONTROL_TOKEN"
    printf 'header = "Accept: application/vnd.github+json"\n'
    printf 'header = "X-GitHub-Api-Version: 2022-11-28"\n'
  } | curl "${curl_args[@]}" --config - "https://api.github.com$path"
}

initialize_fixture_file() {
  local repository=$1
  local path=$2
  local content=$3
  local body_file
  body_file="$(mktemp)"
  python3 - "$content" >"$body_file" <<'PY'
import base64, json, sys
json.dump({
    "message": "Initialize disposable Devsembly fixture",
    "content": base64.b64encode(sys.argv[1].encode()).decode(),
}, sys.stdout)
PY
  github_api PUT "/repos/$repository/contents/$path" "$body_file" >/dev/null
  rm -f "$body_file"
}

if ! git ls-remote --exit-code "$FIXTURE_REPOSITORY_URL" HEAD >/dev/null 2>&1; then
  default_fixture="https://github.com/thebakermark/devsembly-factory-fixture"
  [[ "$FIXTURE_REPOSITORY_URL" == "$default_fixture" ]] || \
    fail "Fixture repository is not publicly readable: $FIXTURE_REPOSITORY_URL"
  read -r -p "The standard fixture is missing. Create it as a public disposable repository? [y/N]: " create_fixture
  [[ "$create_fixture" =~ ^[Yy]$ ]] || fail "A disposable public fixture repository is required"
  fixture_body="$(mktemp)"
  printf '%s\n' '{"name":"devsembly-factory-fixture","description":"Disposable governed-delivery commissioning fixture","private":false,"auto_init":true}' >"$fixture_body"
  created_fixture="$(github_api POST /user/repos "$fixture_body")"
  rm -f "$fixture_body"
  fixture_full_name="$(printf '%s' "$created_fixture" | python3 -c 'import json,sys; print(json.load(sys.stdin)["full_name"])')"
  FIXTURE_REPOSITORY_URL="https://github.com/$fixture_full_name"
  initialize_fixture_file "$fixture_full_name" pyproject.toml $'[project]\nname = "devsembly-factory-fixture"\nversion = "0.1.0"\nrequires-python = ">=3.12"\n'
  initialize_fixture_file "$fixture_full_name" src/app.py $'from fastapi import FastAPI\n\napp = FastAPI()\n\n@app.get("/health")\ndef health() -> dict[str, str]:\n    return {"status": "ok"}\n'
  initialize_fixture_file "$fixture_full_name" tests/test_app.py $'from fastapi.testclient import TestClient\n\nfrom src.app import app\n\n\ndef test_health() -> None:\n    response = TestClient(app).get("/health")\n    assert response.status_code == 200\n    assert response.json() == {"status": "ok"}\n'
  initialize_fixture_file "$fixture_full_name" README.md $'# Devsembly Factory Fixture\n\nDisposable public repository for the governed delivery-loop commissioning run.\n'
fi

git ls-remote --exit-code "$FIXTURE_REPOSITORY_URL" HEAD >/dev/null 2>&1 || \
  fail "Fixture repository is not publicly readable after initialization"

read -r -p "OIDC issuer URL: " OIDC_ISSUER
read -r -p "OIDC API audience: " OIDC_AUDIENCE
read -r -s -p "Temporary human OIDC access token: " HUMAN_ACCESS_TOKEN
printf '\n'
read -r -s -p "Disposable Anthropic API key: " MODEL_PROVIDER_API_KEY
printf '\n'
read -r -p "Exact allowed Anthropic model ID: " ALLOWED_MODEL

[[ "$OIDC_ISSUER" == https://* ]] || fail "OIDC issuer must use HTTPS"
[[ -n "$OIDC_AUDIENCE" && -n "$HUMAN_ACCESS_TOKEN" ]] || fail "OIDC values are required"
[[ ${#MODEL_PROVIDER_API_KEY} -ge 20 ]] || fail "Anthropic API key is unexpectedly short"
[[ "$ALLOWED_MODEL" =~ ^[A-Za-z0-9._:-]+$ ]] || fail "An exact model ID is required"

mkdir -p "$EVIDENCE_ROOT" "$WORKSPACE_ROOT"
chmod 0700 "$EVIDENCE_ROOT" "$WORKSPACE_ROOT"
RUN_STAMP="$(date -u +%Y%m%dT%H%M%SZ)"
EVIDENCE_DIR="$EVIDENCE_ROOT/$RUN_STAMP"
mkdir -m 0700 "$EVIDENCE_DIR"
random_secret() {
  python3 - <<'PY'
import secrets
print(secrets.token_urlsafe(48))
PY
}

POSTGRES_PASSWORD="$(random_secret)"
MINIO_ROOT_PASSWORD="$(random_secret)"
GATEWAY_SECRET="$(random_secret)"
INTERNAL_CONTROL_TOKEN="$(random_secret)"

umask 077
{
  printf 'POSTGRES_USER=devsembly\n'
  printf 'POSTGRES_PASSWORD=%s\n' "$POSTGRES_PASSWORD"
  printf 'POSTGRES_DB=devsembly\n'
  printf 'MINIO_ROOT_USER=devsembly\n'
  printf 'MINIO_ROOT_PASSWORD=%s\n' "$MINIO_ROOT_PASSWORD"
  printf 'DEVSEMBLY_OIDC_ISSUER=%s\n' "$OIDC_ISSUER"
  printf 'DEVSEMBLY_OIDC_AUDIENCE=%s\n' "$OIDC_AUDIENCE"
  printf 'DEVSEMBLY_INTERNAL_CONTROL_TOKEN=%s\n' "$INTERNAL_CONTROL_TOKEN"
  printf 'DEVSEMBLY_MODEL_GATEWAY_URL=http://model-gateway:8080\n'
  printf 'DEVSEMBLY_SANDBOX_NETWORK=devsembly-sandbox-egress\n'
  printf 'DEVSEMBLY_MODEL_GATEWAY_SECRET=%s\n' "$GATEWAY_SECRET"
  printf 'DEVSEMBLY_MODEL_PROVIDER_API_KEY=%s\n' "$MODEL_PROVIDER_API_KEY"
  printf 'DEVSEMBLY_MODEL_PROVIDER_BASE_URL=https://api.anthropic.com\n'
  printf 'DEVSEMBLY_MODEL_PROVIDER_ALLOWED_HOSTS=api.anthropic.com\n'
  printf 'DEVSEMBLY_MODEL_GATEWAY_ALLOWED_MODELS=%s\n' "$ALLOWED_MODEL"
  printf 'DEVSEMBLY_SOURCE_CONTROL_TOKEN=%s\n' "$SOURCE_CONTROL_TOKEN"
  printf 'DEVSEMBLY_WORKSPACE_ROOT=%s\n' "$WORKSPACE_ROOT"
} >"$ENV_FILE"
chmod 0600 "$ENV_FILE"

cleanup() {
  local exit_code=$?
  if [[ "$KEEP_STACK" != true ]]; then
    "${COMPOSE[@]}" --env-file "$ENV_FILE" --profile model-egress down --remove-orphans \
      >/dev/null 2>&1 || true
    rm -f "$ENV_FILE"
  fi
  unset HUMAN_ACCESS_TOKEN SOURCE_CONTROL_TOKEN MODEL_PROVIDER_API_KEY POSTGRES_PASSWORD
  unset MINIO_ROOT_PASSWORD GATEWAY_SECRET INTERNAL_CONTROL_TOKEN
  if [[ $exit_code -ne 0 ]]; then
    log "Commissioning stopped safely. Sanitized logs: $EVIDENCE_DIR"
  fi
  exit "$exit_code"
}
trap cleanup EXIT INT TERM

api_call() {
  local method=$1
  local path=$2
  local body_file=${3:-}
  local curl_args=(--fail-with-body --silent --show-error --request "$method")
  if [[ -n "$body_file" ]]; then
    curl_args+=(--header "content-type: application/json" --data-binary "@$body_file")
  fi
  printf 'header = "Authorization: Bearer %s"\n' "$HUMAN_ACCESS_TOKEN" | \
    curl "${curl_args[@]}" --config - "$API_URL$path"
}

json_value() {
  python3 -c 'import json,sys; data=json.load(sys.stdin); print(data'"$1"')'
}

log "Building the sandbox and starting the controlled stack."
docker build --file Dockerfile.sandbox --tag devsembly-sandbox:latest .
"${COMPOSE[@]}" --env-file "$ENV_FILE" --profile model-egress up -d --build --wait \
  --wait-timeout 300
[[ "$(docker network inspect devsembly-sandbox-egress --format '{{.Internal}}')" == true ]] || \
  fail "The model-gateway sandbox network is not internal"
docker compose -f docker-compose.yml -f docker-compose.commissioning.yml \
  --env-file "$ENV_FILE" exec -T worker docker info >/dev/null || \
  fail "The trusted worker cannot reach the host Docker daemon"

log "Creating isolated commissioning scope through the governed API."
tmp_json="$(mktemp)"
printf '{"name":"Devsembly commissioning %s"}\n' "$RUN_STAMP" >"$tmp_json"
organization="$(api_call POST /api/v1/organizations "$tmp_json")"
ORGANIZATION_ID="$(printf '%s' "$organization" | json_value "['id']")"

python3 - "$RUN_STAMP" >"$tmp_json" <<'PY'
import json, sys
json.dump({"name": f"Commissioning {sys.argv[1]}", "objective": "Prove issue 33 live loop"}, sys.stdout)
PY
initiative="$(api_call POST "/api/v1/organizations/$ORGANIZATION_ID/initiatives" "$tmp_json")"
INITIATIVE_ID="$(printf '%s' "$initiative" | json_value "['id']")"

python3 - "$FIXTURE_REPOSITORY_URL" >"$tmp_json" <<'PY'
import json, sys
json.dump({"name": "Disposable factory fixture", "repository": sys.argv[1]}, sys.stdout)
PY
project="$(api_call POST "/api/v1/organizations/$ORGANIZATION_ID/initiatives/$INITIATIVE_ID/projects" "$tmp_json")"
PROJECT_ID="$(printf '%s' "$project" | json_value "['id']")"

python3 - "$RUN_STAMP" "$FIXTURE_REPOSITORY_URL" >"$tmp_json" <<'PY'
import json, sys
stamp, repository = sys.argv[1:]
json.dump({
  "workflow_kind": "software_delivery",
  "idempotency_key": f"issue-33-{stamp}",
  "input_payload": {
    "title": "Add commissioning hello endpoint",
    "objective": "Add a /hello endpoint returning a JSON hello message and add focused tests.",
    "repository_url": repository,
    "base_branch": "main",
    "allowed_paths": ["src/", "tests/", "README.md"],
    "validation_commands": ["pytest -q"],
    "max_repair_attempts": 2
  },
  "steps": [
    {"key": "intake", "name": "Create traceable work item"},
    {"key": "implement", "name": "Implement in isolated workspace"},
    {"key": "validate", "name": "Validate and repair"},
    {"key": "publish", "name": "Publish draft pull request"},
    {"key": "remember", "name": "Propose outcome to project memory"}
  ]
}, sys.stdout)
PY
run_path="/api/v1/organizations/$ORGANIZATION_ID/initiatives/$INITIATIVE_ID/projects/$PROJECT_ID/workflow-runs"
run="$(api_call POST "$run_path" "$tmp_json")"
rm -f "$tmp_json"
RUN_ID="$(printf '%s' "$run" | json_value "['run']['id']")"

log "Run $RUN_ID accepted. Waiting for its terminal governed state."
deadline=$((SECONDS + 3600))
while (( SECONDS < deadline )); do
  detail="$(api_call GET "$run_path/$RUN_ID")"
  status="$(printf '%s' "$detail" | json_value "['run']['status']")"
  printf '%s\n' "$detail" >"$EVIDENCE_DIR/workflow-run.json"
  case "$status" in
    succeeded) break ;;
    failed|cancelled) fail "Fixture ended in terminal state: $status" ;;
  esac
  sleep 10
done
[[ "${status:-}" == succeeded ]] || fail "Fixture did not complete within 60 minutes"

"${COMPOSE[@]}" --env-file "$ENV_FILE" --profile model-egress ps --format json \
  >"$EVIDENCE_DIR/compose-services.json"
docker network inspect devsembly-sandbox-egress >"$EVIDENCE_DIR/sandbox-network.json"
python3 - "$EVIDENCE_DIR/summary.json" "$RUN_STAMP" "$RUN_ID" "$ORGANIZATION_ID" \
  "$INITIATIVE_ID" "$PROJECT_ID" "$FIXTURE_REPOSITORY_URL" <<'PY'
import json, sys
path, stamp, run_id, organization_id, initiative_id, project_id, repository = sys.argv[1:]
with open(path, "w", encoding="utf-8") as handle:
    json.dump({
        "commissioned_at": stamp,
        "workflow_run_id": run_id,
        "organization_id": organization_id,
        "initiative_id": initiative_id,
        "project_id": project_id,
        "fixture_repository": repository,
        "status": "succeeded",
    }, handle, indent=2, sort_keys=True)
    handle.write("\n")
PY

log "Issue #33 live fixture succeeded. Sanitized evidence: $EVIDENCE_DIR"
log "No merge or deployment was performed."
