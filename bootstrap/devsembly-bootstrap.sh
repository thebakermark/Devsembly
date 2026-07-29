#!/usr/bin/env bash
set -Eeuo pipefail

BOOTSTRAP_VERSION="1.0.0-rc4"
DEVSEMBLY_USER="${DEVSEMBLY_USER:-devsembly}"
DEVSEMBLY_HOME="${DEVSEMBLY_HOME:-/opt/devsembly}"
DEVSEMBLY_REPO="${DEVSEMBLY_REPO:-https://github.com/thebakermark/Devsembly.git}"
DEVSEMBLY_REF="${DEVSEMBLY_REF:-main}"
LOG_FILE="${LOG_FILE:-/var/log/devsembly-bootstrap.log}"
STATUS_FILE="${STATUS_FILE:-/var/lib/devsembly/bootstrap-status}"
APT_LOCK_TIMEOUT="${APT_LOCK_TIMEOUT:-900}"

exec > >(tee -a "$LOG_FILE") 2>&1

on_error() {
  local exit_code=$?
  local line_no=${1:-unknown}
  mkdir -p "$(dirname "$STATUS_FILE")"
  printf 'status=failed\nline=%s\nexit_code=%s\nversion=%s\ntimestamp=%s\n' \
    "$line_no" "$exit_code" "$BOOTSTRAP_VERSION" "$(date --iso-8601=seconds)" > "$STATUS_FILE"
  echo "ERROR: Devsembly bootstrap failed near line $line_no with exit code $exit_code."
  exit "$exit_code"
}
trap 'on_error $LINENO' ERR

require_root() {
  if [[ "${EUID}" -ne 0 ]]; then
    echo "Run this script as root."
    exit 1
  fi
}

wait_for_package_manager() {
  local elapsed=0
  local retry_interval=5
  local output
  local exit_code

  echo "Waiting for Ubuntu package manager to become available..."

  while true; do
    set +e
    output="$(dpkg --configure -a 2>&1)"
    exit_code=$?
    set -e

    if (( exit_code == 0 )); then
      [[ -n "$output" ]] && printf '%s\n' "$output"
      return 0
    fi

    if grep -qiE 'lock.*(held|locked)|unable to acquire.*lock' <<<"$output"; then
      if (( elapsed >= APT_LOCK_TIMEOUT )); then
        printf '%s\n' "$output"
        echo "Timed out after ${APT_LOCK_TIMEOUT}s waiting for the dpkg lock."
        return 100
      fi

      if (( elapsed == 0 || elapsed % 30 == 0 )); then
        printf '%s\n' "$output"
        echo "Package manager is busy; retrying..."
      fi

      sleep "$retry_interval"
      elapsed=$((elapsed + retry_interval))
      continue
    fi

    printf '%s\n' "$output"
    return "$exit_code"
  done
}

apt_get() {
  wait_for_package_manager
  apt-get \
    -o DPkg::Lock::Timeout="$APT_LOCK_TIMEOUT" \
    -o APT::Get::Lock-Timeout="$APT_LOCK_TIMEOUT" \
    "$@"
}

install_base_packages() {
  export DEBIAN_FRONTEND=noninteractive
  apt_get update
  apt_get install -y \
    ca-certificates curl git gnupg jq openssl rsync unzip \
    openssh-server ufw fail2ban unattended-upgrades apt-transport-https
}

configure_updates() {
  cat >/etc/apt/apt.conf.d/20auto-upgrades <<'EOF'
APT::Periodic::Update-Package-Lists "1";
APT::Periodic::Unattended-Upgrade "1";
EOF
  systemctl enable --now unattended-upgrades
}

configure_ssh_access() {
  systemctl enable --now ssh

  if ! sshd -t; then
    echo "OpenSSH configuration validation failed."
    exit 1
  fi

  if ! ss -lnt | awk '{print $4}' | grep -Eq '(^|:)(22)$'; then
    echo "OpenSSH is not listening on TCP port 22."
    exit 1
  fi
}

configure_firewall() {
  ufw default deny incoming
  ufw default allow outgoing
  ufw allow 22/tcp comment 'OpenSSH'
  ufw --force enable
  ufw reload
}

configure_fail2ban() {
  cat >/etc/fail2ban/jail.d/devsembly.conf <<'EOF'
[sshd]
enabled = true
maxretry = 5
findtime = 10m
bantime = 1h
EOF
  systemctl enable --now fail2ban
}

install_docker() {
  install -m 0755 -d /etc/apt/keyrings
  rm -f /etc/apt/keyrings/docker.gpg /etc/apt/keyrings/docker.asc
  curl -fsSL https://download.docker.com/linux/ubuntu/gpg \
    | gpg --dearmor -o /etc/apt/keyrings/docker.gpg
  chmod a+r /etc/apt/keyrings/docker.gpg

  . /etc/os-release
  cat >/etc/apt/sources.list.d/docker.list <<EOF
deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu ${VERSION_CODENAME} stable
EOF

  apt_get update
  apt_get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
  systemctl enable --now docker
}

create_service_user() {
  if ! id "$DEVSEMBLY_USER" >/dev/null 2>&1; then
    useradd --create-home --shell /bin/bash "$DEVSEMBLY_USER"
  fi
  usermod -aG docker "$DEVSEMBLY_USER"
  install -d -o "$DEVSEMBLY_USER" -g "$DEVSEMBLY_USER" -m 0750 "$DEVSEMBLY_HOME"
}

run_git_as_service_user() {
  runuser -u "$DEVSEMBLY_USER" -- git -C "$DEVSEMBLY_HOME" "$@"
}

checkout_repository() {
  if [[ -d "$DEVSEMBLY_HOME/.git" ]]; then
    chown -R "$DEVSEMBLY_USER:$DEVSEMBLY_USER" "$DEVSEMBLY_HOME"
    run_git_as_service_user fetch --all --prune
    run_git_as_service_user checkout "$DEVSEMBLY_REF"
    run_git_as_service_user reset --hard "origin/$DEVSEMBLY_REF"
  else
    rm -rf "$DEVSEMBLY_HOME"
    install -d -o "$DEVSEMBLY_USER" -g "$DEVSEMBLY_USER" -m 0750 "$DEVSEMBLY_HOME"
    runuser -u "$DEVSEMBLY_USER" -- \
      git clone --branch "$DEVSEMBLY_REF" --single-branch "$DEVSEMBLY_REPO" "$DEVSEMBLY_HOME"
  fi
  chown -R "$DEVSEMBLY_USER:$DEVSEMBLY_USER" "$DEVSEMBLY_HOME"
}

normalize_repository_permissions() {
  find "$DEVSEMBLY_HOME/bootstrap" -maxdepth 1 -type f -name '*.sh' -exec chmod 0755 {} +
  chown -R "$DEVSEMBLY_USER:$DEVSEMBLY_USER" "$DEVSEMBLY_HOME/bootstrap"
}

install_systemd_unit() {
  cat >/etc/systemd/system/devsembly.service <<EOF
[Unit]
Description=Devsembly control plane
Requires=docker.service
After=docker.service network-online.target
Wants=network-online.target

[Service]
Type=oneshot
RemainAfterExit=yes
User=$DEVSEMBLY_USER
Group=$DEVSEMBLY_USER
WorkingDirectory=$DEVSEMBLY_HOME
ExecStart=/usr/bin/docker compose -f infrastructure/docker/compose.dev.yaml up -d --remove-orphans
ExecStop=/usr/bin/docker compose -f infrastructure/docker/compose.dev.yaml down
TimeoutStartSec=0

[Install]
WantedBy=multi-user.target
EOF

  systemctl daemon-reload
  systemctl enable devsembly.service
}

start_stack_if_available() {
  local compose_file="$DEVSEMBLY_HOME/infrastructure/docker/compose.dev.yaml"
  if [[ -f "$compose_file" ]]; then
    systemctl restart devsembly.service
  else
    echo "Compose file not present at $compose_file; infrastructure bootstrap completed without starting the stack."
  fi
}

install_validation_command() {
  cat >/usr/local/sbin/devsembly-validate <<EOF
#!/usr/bin/env bash
set -Eeuo pipefail
exec /usr/bin/env bash "$DEVSEMBLY_HOME/bootstrap/validate-bootstrap.sh"
EOF
  chmod 0755 /usr/local/sbin/devsembly-validate
}

write_completion_status() {
  mkdir -p "$(dirname "$STATUS_FILE")"
  printf 'status=complete\nversion=%s\ntimestamp=%s\nrepository=%s\nref=%s\nhome=%s\n' \
    "$BOOTSTRAP_VERSION" "$(date --iso-8601=seconds)" "$DEVSEMBLY_REPO" "$DEVSEMBLY_REF" "$DEVSEMBLY_HOME" > "$STATUS_FILE"
}

main() {
  require_root
  echo "Starting Devsembly Genesis bootstrap $BOOTSTRAP_VERSION."
  install_base_packages
  configure_updates
  configure_ssh_access
  configure_firewall
  configure_fail2ban
  install_docker
  create_service_user
  checkout_repository
  normalize_repository_permissions
  install_systemd_unit
  install_validation_command
  start_stack_if_available
  write_completion_status
  /usr/local/sbin/devsembly-validate
  echo "Devsembly Genesis bootstrap completed successfully."
}

main "$@"
