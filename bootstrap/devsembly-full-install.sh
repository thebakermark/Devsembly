#!/usr/bin/env bash
set -Eeuo pipefail

DEVSEMBLY_USER="${DEVSEMBLY_USER:-devsembly}"
DEVSEMBLY_REPO="${DEVSEMBLY_REPO:-https://github.com/thebakermark/Devsembly.git}"
DEVSEMBLY_REF="${DEVSEMBLY_REF:-build/workstation-automation-v1}"
DEVSEMBLY_HOME="${DEVSEMBLY_HOME:-/opt/devsembly}"

if [[ $EUID -ne 0 ]]; then
  echo "Run this installer as root."
  exit 1
fi

if [[ -d "$DEVSEMBLY_HOME/.git" ]]; then
  id "$DEVSEMBLY_USER" >/dev/null 2>&1 || {
    echo "Existing checkout found, but service user '$DEVSEMBLY_USER' is missing."
    exit 1
  }
  chown -R "$DEVSEMBLY_USER:$DEVSEMBLY_USER" "$DEVSEMBLY_HOME"
  runuser -u "$DEVSEMBLY_USER" -- git -C "$DEVSEMBLY_HOME" fetch \
    origin "+refs/heads/$DEVSEMBLY_REF:refs/remotes/origin/$DEVSEMBLY_REF"
  runuser -u "$DEVSEMBLY_USER" -- git -C "$DEVSEMBLY_HOME" checkout \
    -B "$DEVSEMBLY_REF" "origin/$DEVSEMBLY_REF"
else
  DEVSEMBLY_REF="$DEVSEMBLY_REF" DEVSEMBLY_HOME="$DEVSEMBLY_HOME" \
    bash <(curl -fsSL "https://raw.githubusercontent.com/thebakermark/Devsembly/$DEVSEMBLY_REF/bootstrap/devsembly-bootstrap.sh")
fi

chmod 0755 \
  "$DEVSEMBLY_HOME/bootstrap/devsembly-bootstrap.sh" \
  "$DEVSEMBLY_HOME/bootstrap/install-workstation.sh"

# Genesis is idempotent and safely refreshes the base VM services.
DEVSEMBLY_USER="$DEVSEMBLY_USER" DEVSEMBLY_REF="$DEVSEMBLY_REF" DEVSEMBLY_HOME="$DEVSEMBLY_HOME" \
  "$DEVSEMBLY_HOME/bootstrap/devsembly-bootstrap.sh"

DEVSEMBLY_USER="$DEVSEMBLY_USER" DEVSEMBLY_HOME="$DEVSEMBLY_HOME" \
  "$DEVSEMBLY_HOME/bootstrap/install-workstation.sh"

printf '\nDevsembly full installation completed.\n'
printf 'Validate with: devsembly-validate && devsembly-workstation-validate\n'
printf 'Retrieve the browser IDE password with: cat /root/devsembly-code-server-password.txt\n'
