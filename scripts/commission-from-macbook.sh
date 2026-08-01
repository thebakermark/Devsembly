#!/usr/bin/env bash
set -Eeuo pipefail

usage() {
  cat <<'EOF'
Usage: bash scripts/commission-from-macbook.sh <tailscale-host-or-ip> [ssh-user]

Connects the MacBook control console to the development VM, safely updates the
existing Draft PR #17 branch, and starts the guided issue #33 commissioning run.
The remote checkout must be clean. No branch, merge, force-push, or deployment is
performed.
EOF
}

if [[ ${1:-} == --help || ${1:-} == -h ]]; then
  usage
  exit 0
fi

[[ $# -ge 1 && $# -le 2 ]] || { usage >&2; exit 2; }
command -v ssh >/dev/null 2>&1 || { printf 'ssh is required\n' >&2; exit 1; }

VM_HOST=$1
VM_USER=${2:-mark}
[[ "$VM_HOST" =~ ^[A-Za-z0-9._:-]+$ ]] || { printf 'Invalid VM host\n' >&2; exit 2; }
[[ "$VM_USER" =~ ^[A-Za-z_][A-Za-z0-9_-]*$ ]] || { printf 'Invalid SSH user\n' >&2; exit 2; }

ssh -t -o StrictHostKeyChecking=accept-new "$VM_USER@$VM_HOST" '
  set -Eeuo pipefail
  branch=docs/genesis-reference-implementation-plan
  if [[ -d /opt/devsembly/.git ]]; then
    repo=/opt/devsembly
  elif [[ -d "$HOME/devsembly/.git" ]]; then
    repo="$HOME/devsembly"
  else
    repo="$HOME/devsembly"
    git clone --branch "$branch" --single-branch https://github.com/thebakermark/Devsembly.git "$repo"
  fi
  cd "$repo"
  [[ -z "$(git status --porcelain)" ]] || {
    printf "The VM checkout has preserved changes; refusing to overwrite them.\n" >&2
    exit 1
  }
  git fetch --no-tags origin "$branch"
  git checkout "$branch"
  git merge --ff-only "origin/$branch"
  exec bash scripts/commission-first-run.sh
'
