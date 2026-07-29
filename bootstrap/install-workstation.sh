#!/usr/bin/env bash
set -Eeuo pipefail

DEVSEMBLY_USER="${DEVSEMBLY_USER:-devsembly}"
DEVSEMBLY_HOME="${DEVSEMBLY_HOME:-/opt/devsembly}"
CODE_SERVER_BIND="${CODE_SERVER_BIND:-127.0.0.1:8080}"
PASSWORD_FILE="${PASSWORD_FILE:-/root/devsembly-code-server-password.txt}"
STATUS_FILE="${STATUS_FILE:-/var/lib/devsembly/workstation-status}"
LOG_FILE="${LOG_FILE:-/var/log/devsembly-workstation.log}"

exec > >(tee -a "$LOG_FILE") 2>&1

fail() {
  local code=$?
  mkdir -p "$(dirname "$STATUS_FILE")"
  printf 'status=failed\nexit_code=%s\ntimestamp=%s\n' "$code" "$(date --iso-8601=seconds)" > "$STATUS_FILE"
  exit "$code"
}
trap fail ERR

[[ $EUID -eq 0 ]] || { echo "Run as root."; exit 1; }
id "$DEVSEMBLY_USER" >/dev/null 2>&1 || { echo "Missing user: $DEVSEMBLY_USER"; exit 1; }

install_code_server() {
  if ! command -v code-server >/dev/null 2>&1; then
    curl -fsSL https://code-server.dev/install.sh | sh
  fi

  install -d -o "$DEVSEMBLY_USER" -g "$DEVSEMBLY_USER" -m 0700 \
    "/home/$DEVSEMBLY_USER/.config/code-server"

  if [[ ! -s "$PASSWORD_FILE" ]]; then
    openssl rand -hex 24 > "$PASSWORD_FILE"
    chmod 0600 "$PASSWORD_FILE"
  fi

  local password
  password="$(cat "$PASSWORD_FILE")"
  cat > "/home/$DEVSEMBLY_USER/.config/code-server/config.yaml" <<EOF
bind-addr: $CODE_SERVER_BIND
auth: password
password: $password
cert: false
EOF
  chown "$DEVSEMBLY_USER:$DEVSEMBLY_USER" "/home/$DEVSEMBLY_USER/.config/code-server/config.yaml"
  chmod 0600 "/home/$DEVSEMBLY_USER/.config/code-server/config.yaml"

  systemctl daemon-reload
  systemctl enable --now "code-server@$DEVSEMBLY_USER"
}

install_claude_code() {
  if ! runuser -u "$DEVSEMBLY_USER" -- bash -lc 'command -v claude >/dev/null 2>&1'; then
    runuser -u "$DEVSEMBLY_USER" -- bash -lc 'curl -fsSL https://claude.ai/install.sh | bash'
  fi
}

install_codex() {
  if ! runuser -u "$DEVSEMBLY_USER" -- bash -lc 'command -v codex >/dev/null 2>&1'; then
    runuser -u "$DEVSEMBLY_USER" -- bash -lc 'curl -fsSL https://chatgpt.com/codex/install.sh | sh'
  fi
}

configure_shell_path() {
  local profile="/home/$DEVSEMBLY_USER/.profile"
  touch "$profile"
  chown "$DEVSEMBLY_USER:$DEVSEMBLY_USER" "$profile"
  if ! grep -q 'DEVSEMBLY LOCAL BIN' "$profile"; then
    cat >> "$profile" <<'EOF'

# DEVSEMBLY LOCAL BIN
export PATH="$HOME/.local/bin:$PATH"
EOF
  fi
}

install_secrets_directory() {
  install -d -o root -g "$DEVSEMBLY_USER" -m 0750 /etc/devsembly
  if [[ ! -f /etc/devsembly/devsembly.env ]]; then
    cat > /etc/devsembly/devsembly.env <<'EOF'
# Devsembly secrets and runtime configuration.
# Add credentials here; never commit this file to GitHub.
EOF
  fi
  chown root:"$DEVSEMBLY_USER" /etc/devsembly/devsembly.env
  chmod 0640 /etc/devsembly/devsembly.env
}

install_validation_command() {
  cat > /usr/local/sbin/devsembly-workstation-validate <<'EOF'
#!/usr/bin/env bash
set -Eeuo pipefail
failures=0
pass(){ printf 'PASS: %s\n' "$1"; }
fail(){ printf 'FAIL: %s\n' "$1"; failures=$((failures+1)); }
command -v code-server >/dev/null 2>&1 && pass 'code-server installed' || fail 'code-server missing'
systemctl is-active --quiet code-server@devsembly && pass 'code-server active' || fail 'code-server inactive'
ss -lnt | awk '{print $4}' | grep -q '127.0.0.1:8080$' && pass 'code-server bound locally' || fail 'code-server not bound to 127.0.0.1:8080'
runuser -u devsembly -- bash -lc 'command -v claude >/dev/null 2>&1' && pass 'Claude Code installed' || fail 'Claude Code missing'
runuser -u devsembly -- bash -lc 'command -v codex >/dev/null 2>&1' && pass 'Codex installed' || fail 'Codex missing'
[[ $(stat -c '%a' /etc/devsembly/devsembly.env) == 640 ]] && pass 'secrets permissions correct' || fail 'secrets permissions incorrect'
[[ -w /opt/devsembly ]] && pass 'repository writable' || fail 'repository not writable'
(( failures == 0 )) || exit 1
printf '\nAll workstation checks passed.\n'
EOF
  chmod 0755 /usr/local/sbin/devsembly-workstation-validate
}

main() {
  install_code_server
  configure_shell_path
  install_claude_code
  install_codex
  install_secrets_directory
  install_validation_command
  /usr/local/sbin/devsembly-workstation-validate
  mkdir -p "$(dirname "$STATUS_FILE")"
  printf 'status=complete\ntimestamp=%s\ncode_server=%s\n' \
    "$(date --iso-8601=seconds)" "$CODE_SERVER_BIND" > "$STATUS_FILE"
  echo "Workstation setup complete."
  echo "Code-server password: $PASSWORD_FILE"
}

main "$@"
