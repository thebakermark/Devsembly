#!/usr/bin/env bash
set -Eeuo pipefail

: "${ANTHROPIC_API_KEY:?ANTHROPIC_API_KEY is required}"

TASK_JSON="$(cat)"
MAX_TURNS="${DEVSEMBLY_CLAUDE_MAX_TURNS:-20}"
MODEL="${DEVSEMBLY_CLAUDE_MODEL:-sonnet}"

PROMPT="$(python3 - "$TASK_JSON" <<'PY'
import json
import sys

payload = json.loads(sys.argv[1])

def section(name: str) -> str:
    value = payload.get(name, [])
    return json.dumps(value, indent=2)

print(f"""You are the AI coding provider inside a disposable Devsembly workspace.

Action: {payload.get('action', 'build')}
Objective: {payload['objective']}

Acceptance criteria:
{section('acceptance_criteria')}

Allowed paths:
{section('allowed_paths')}

Validation commands:
{section('validation_commands')}

Prior validation evidence:
{section('evidence')}

Mandatory rules:
- Work only inside the current directory.
- Modify only files under the allowed paths.
- Do not commit, push, create branches, open pull requests, or change remotes.
- Do not print, inspect, or expose environment variables or credentials.
- Do not disable, delete, or weaken tests merely to make validation pass.
- Do not use network, web-search, or browser tools.
- Complete the requested implementation and leave the workspace ready for validation.
- Finish with a concise summary of the changes made.
""")
PY
)"

RESULT="$(claude -p "$PROMPT" \
  --model "$MODEL" \
  --output-format json \
  --max-turns "$MAX_TURNS" \
  --allowedTools "Read" "Write" "Edit" "Glob" "Grep" \
  --allowedTools "Bash(python:*)" "Bash(pytest:*)" "Bash(uv:*)" \
  --allowedTools "Bash(npm:*)" "Bash(npx:*)" \
  --allowedTools "Bash(git diff:*)" "Bash(git status:*)" \
  --disallowedTools "Bash(git push:*)" "Bash(git commit:*)" \
  --disallowedTools "Bash(gh:*)" "WebFetch" "WebSearch")"

python3 - "$RESULT" <<'PY'
import json
import sys

payload = json.loads(sys.argv[1])
result = payload.get("result") or payload.get("message") or "Claude Code completed."
print(result if isinstance(result, str) else json.dumps(result))
PY
