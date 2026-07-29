#!/usr/bin/env bash
set -Eeuo pipefail

ROOT_DIR="${DEVSEMBLY_ROOT:-/opt/devsembly}"
cd "$ROOT_DIR"

printf '=== DEVSEMBLY STATUS ===\n'
date -u
printf '\nRepository:\n'
git status --short --branch
printf '\nContainers:\n'
docker compose ps
printf '\nAPI liveness:\n'
curl --fail --silent --show-error http://127.0.0.1:${DEVSEMBLY_API_PORT:-8000}/health/live
printf '\n\nAPI readiness:\n'
curl --fail --silent --show-error http://127.0.0.1:${DEVSEMBLY_API_PORT:-8000}/health/ready
printf '\n\nTemporal UI:\n'
curl --fail --silent --show-error --output /dev/null http://127.0.0.1:${TEMPORAL_UI_PORT:-8088}
printf 'reachable\n'
