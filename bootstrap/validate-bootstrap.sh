#!/usr/bin/env bash
set -Eeuo pipefail

DEVSEMBLY_HOME="${DEVSEMBLY_HOME:-/opt/devsembly}"
STATUS_FILE="${STATUS_FILE:-/var/lib/devsembly/bootstrap-status}"
COMPOSE_FILE="$DEVSEMBLY_HOME/infrastructure/docker/compose.dev.yaml"
failures=0

pass() { printf 'PASS: %s\n' "$1"; }
fail() { printf 'FAIL: %s\n' "$1"; failures=$((failures + 1)); }

check_command() {
  if command -v "$1" >/dev/null 2>&1; then pass "$1 is installed"; else fail "$1 is missing"; fi
}

check_service() {
  if systemctl is-active --quiet "$1"; then pass "$1 is active"; else fail "$1 is not active"; fi
}

check_command git
check_command curl
check_command jq
check_command docker

docker compose version >/dev/null 2>&1 && pass 'Docker Compose plugin is available' || fail 'Docker Compose plugin is unavailable'
check_service docker
check_service fail2ban

if ufw status | grep -q 'Status: active'; then pass 'UFW is active'; else fail 'UFW is inactive'; fi
[[ -d "$DEVSEMBLY_HOME/.git" ]] && pass 'Devsembly repository is present' || fail 'Devsembly repository is missing'
[[ -f "$STATUS_FILE" ]] && pass 'Bootstrap status file exists' || fail 'Bootstrap status file is missing'

if [[ -f "$COMPOSE_FILE" ]]; then
  docker compose -f "$COMPOSE_FILE" config --quiet \
    && pass 'Compose configuration is valid' \
    || fail 'Compose configuration is invalid'

  unhealthy="$(docker compose -f "$COMPOSE_FILE" ps --format json 2>/dev/null | jq -r 'select((.Health // "") == "unhealthy" or (.State // "") == "exited") | .Service' || true)"
  if [[ -z "$unhealthy" ]]; then
    pass 'No unhealthy or exited compose services detected'
  else
    fail "Unhealthy or exited services: $unhealthy"
  fi
else
  printf 'INFO: Compose file not present; stack checks skipped.\n'
fi

if (( failures > 0 )); then
  printf '\nValidation completed with %d failure(s).\n' "$failures"
  exit 1
fi

printf '\nAll Devsembly bootstrap validation checks passed.\n'
