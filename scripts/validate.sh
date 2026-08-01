#!/usr/bin/env bash
set -Eeuo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

FAILURES=0

run_check() {
    local name="$1"
    shift

    echo
    echo "=================================================="
    echo "CHECK: $name"
    echo "=================================================="

    if "$@"; then
        echo "PASS: $name"
    else
        echo "FAIL: $name"
        FAILURES=$((FAILURES + 1))
    fi
}

check_required_files() {
    local files=(
        "README.md"
        "SECURITY.md"
        "CONTRIBUTING.md"
    )

    local missing=0

    for file in "${files[@]}"; do
        if [[ ! -f "$file" ]]; then
            echo "Missing required file: $file"
            missing=1
        fi
    done

    return "$missing"
}

check_shell() {
    mapfile -t files < <(
        find . \
            -path './.git' -prune -o \
            -type f -name '*.sh' -print
    )

    if [[ "${#files[@]}" -eq 0 ]]; then
        echo "No shell scripts found."
        return 0
    fi

    shellcheck "${files[@]}"
}

check_compose() {
    mapfile -t files < <(
        find . \
            -path './.git' -prune -o \
            -type f \
            \( -name 'compose.yml' -o \
               -name 'compose.yaml' -o \
               -name 'docker-compose.yml' -o \
               -name 'docker-compose.yaml' \) \
            -print
    )

    for file in "${files[@]}"; do
        docker compose -f "$file" config --quiet
    done
}

run_check "Required repository files" check_required_files
run_check "ShellCheck" check_shell
run_check "Docker Compose syntax" check_compose
run_check "Git diff check" git diff --check

echo
if [[ "$FAILURES" -gt 0 ]]; then
    echo "VALIDATION FAILED: $FAILURES check(s) failed."
    exit 1
fi

echo "ALL VALIDATION CHECKS PASSED."
