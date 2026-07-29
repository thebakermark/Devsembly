#!/usr/bin/env bash
set -Eeuo pipefail

DEVSEMBLY_USER="${DEVSEMBLY_USER:-devsembly}"
ADMIN_USER="${ADMIN_USER:-mark}"
DEVSEMBLY_REPO="${DEVSEMBLY_REPO:-https://github.com/thebakermark/Devsembly.git}"
DEVSEMBLY_REF="${DEVSEMBLY_REF:-build/workstation-automation-v1}"
DEVSEMBLY_HOME="${DEVSEMBLY_HOME:-/opt/devsembly}"

if [[ $EUID -ne 0 ]]; then
  echo "Run this installer as root."
  exit 1
fi

configure_admin_ssh() {
  local source_keys="/root/.ssh/authorized_keys"
  local admin_home="/home/$ADMIN_USER"

  if [[ ! -s "$source_keys" ]]; then
    echo "No Vultr-provided root SSH key was found at $source_keys."
    echo "Recreate the VM with your SSH key selected; refusing to disable password access."
    exit 1
  fi

  if ! id "$ADMIN_USER" >/dev/null 2>&1; then
    useradd --create-home --shell /bin/bash "$ADMIN_USER"
  fi
  usermod -aG sudo "$ADMIN_USER"

  install -d -o "$ADMIN_USER" -g "$ADMIN_USER" -m 0700 "$admin_home/.ssh"
  install -o "$ADMIN_USER" -g "$ADMIN_USER" -m 0600 \
    "$source_keys" "$admin_home/.ssh/authorized_keys"

  install -d -m 0755 /etc/sudoers.d
  printf '%s ALL=(ALL) NOPASSWD:ALL\n' "$ADMIN_USER" \
    > "/etc/sudoers.d/90-devsembly-$ADMIN_USER"
  chmod 0440 "/etc/sudoers.d/90-devsembly-$ADMIN_USER"

  cat > /etc/ssh/sshd_config.d/99-devsembly-access.conf <<'EOF'
PubkeyAuthentication yes
PasswordAuthentication no
KbdInteractiveAuthentication no
PermitRootLogin prohibit-password
EOF

  sshd -t
  systemctl restart ssh
  ufw allow 22/tcp
  ufw reload

  [[ -s "$admin_home/.ssh/authorized_keys" ]]
  systemctl is-active --quiet ssh
  ss -lnt | awk '{print $4}' | grep -Eq '(^|:)(22)$'
  echo "SSH key access configured for $ADMIN_USER; password login is disabled."
}

if [[ -d "$DEVSEMBLY_HOME/.git" ]]; then
  id "$DEVSEMBLY_USER" >/dev/null 2>&1 || {
    echo "Existing checkout found, but service user '$DEVSEMBLY_USER' is missing."
    exit 1
  }
  chown -R "$DEVSEMBLY_USER:$DEVSEMBLY_USER" "$DEVSEMBLY_HOME"
  runuser -u "$DEVSEMBLY_USER" -- git -C "$DEVSEMBLY_HOME" remote \
    set-branches --add origin "$DEVSEMBLY_REF"
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

configure_admin_ssh

DEVSEMBLY_USER="$DEVSEMBLY_USER" DEVSEMBLY_HOME="$DEVSEMBLY_HOME" \
  "$DEVSEMBLY_HOME/bootstrap/install-workstation.sh"

printf '\nDevsembly full installation completed.\n'
printf 'Validate with: devsembly-validate && devsembly-workstation-validate\n'
printf 'Connect with: ssh %s@YOUR_VM_IP\n' "$ADMIN_USER"
printf 'Retrieve the browser IDE password with: sudo cat /root/devsembly-code-server-password.txt\n'
