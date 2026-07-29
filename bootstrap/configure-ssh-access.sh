#!/usr/bin/env bash
set -Eeuo pipefail

ADMIN_USER="${ADMIN_USER:-mark}"
ADMIN_HOME="${ADMIN_HOME:-/home/$ADMIN_USER}"
ROOT_AUTHORIZED_KEYS="${ROOT_AUTHORIZED_KEYS:-/root/.ssh/authorized_keys}"
ADMIN_AUTHORIZED_KEYS="$ADMIN_HOME/.ssh/authorized_keys"
SSH_PASSWORD_AUTH="${SSH_PASSWORD_AUTH:-no}"
STATUS_FILE="${SSH_STATUS_FILE:-/var/lib/devsembly/ssh-status}"
LOG_FILE="${SSH_LOG_FILE:-/var/log/devsembly-ssh.log}"

exec > >(tee -a "$LOG_FILE") 2>&1

on_error() {
  local code=$?
  mkdir -p "$(dirname "$STATUS_FILE")"
  printf 'status=failed\nexit_code=%s\ntimestamp=%s\n' \
    "$code" "$(date --iso-8601=seconds)" > "$STATUS_FILE"
  echo "ERROR: Devsembly SSH access configuration failed with exit code $code."
  exit "$code"
}
trap on_error ERR

[[ $EUID -eq 0 ]] || { echo "Run as root."; exit 1; }
[[ "$SSH_PASSWORD_AUTH" == "yes" || "$SSH_PASSWORD_AUTH" == "no" ]] || {
  echo "SSH_PASSWORD_AUTH must be 'yes' or 'no'."
  exit 1
}

if ! id "$ADMIN_USER" >/dev/null 2>&1; then
  useradd --create-home --shell /bin/bash "$ADMIN_USER"
fi
usermod -aG sudo "$ADMIN_USER"

install -d -o "$ADMIN_USER" -g "$ADMIN_USER" -m 0700 "$ADMIN_HOME/.ssh"

if [[ -s "$ADMIN_AUTHORIZED_KEYS" ]]; then
  echo "Existing SSH key retained for $ADMIN_USER."
elif [[ -s "$ROOT_AUTHORIZED_KEYS" ]]; then
  install -o "$ADMIN_USER" -g "$ADMIN_USER" -m 0600 \
    "$ROOT_AUTHORIZED_KEYS" "$ADMIN_AUTHORIZED_KEYS"
  echo "Vultr-provided root SSH key copied to $ADMIN_USER."
else
  echo "No authorized SSH key found for root or $ADMIN_USER."
  echo "Select an SSH key during VM deployment; refusing to change SSH authentication."
  exit 1
fi

chown "$ADMIN_USER:$ADMIN_USER" "$ADMIN_AUTHORIZED_KEYS"
chmod 0600 "$ADMIN_AUTHORIZED_KEYS"

install -d -m 0755 /etc/sudoers.d
printf '%s ALL=(ALL) NOPASSWD:ALL\n' "$ADMIN_USER" \
  > "/etc/sudoers.d/90-devsembly-$ADMIN_USER"
chmod 0440 "/etc/sudoers.d/90-devsembly-$ADMIN_USER"
visudo -cf "/etc/sudoers.d/90-devsembly-$ADMIN_USER" >/dev/null

cat > /etc/ssh/sshd_config.d/99-devsembly-access.conf <<EOF
PubkeyAuthentication yes
PasswordAuthentication $SSH_PASSWORD_AUTH
KbdInteractiveAuthentication no
PermitRootLogin prohibit-password
EOF

sshd -t
systemctl enable --now ssh
systemctl restart ssh
ufw allow 22/tcp
ufw reload

cat > /usr/local/sbin/devsembly-ssh-validate <<EOF
#!/usr/bin/env bash
set -Eeuo pipefail
failures=0
pass(){ printf 'PASS: %s\\n' "\$1"; }
fail(){ printf 'FAIL: %s\\n' "\$1"; failures=\$((failures+1)); }
id '$ADMIN_USER' >/dev/null 2>&1 && pass 'administrator account exists' || fail 'administrator account missing'
[[ -s '$ADMIN_AUTHORIZED_KEYS' ]] && pass 'administrator SSH key installed' || fail 'administrator SSH key missing'
[[ \$(stat -c '%a' '$ADMIN_HOME/.ssh') == 700 ]] && pass 'SSH directory permissions correct' || fail 'SSH directory permissions incorrect'
[[ \$(stat -c '%a' '$ADMIN_AUTHORIZED_KEYS') == 600 ]] && pass 'authorized_keys permissions correct' || fail 'authorized_keys permissions incorrect'
sshd -t && pass 'SSH configuration valid' || fail 'SSH configuration invalid'
systemctl is-active --quiet ssh && pass 'SSH service active' || fail 'SSH service inactive'
ss -lnt | awk '{print \$4}' | grep -Eq '(^|:)(22)\$' && pass 'SSH listening on port 22' || fail 'SSH not listening on port 22'
ufw status | grep -Eq '22/tcp.*ALLOW' && pass 'UFW allows SSH' || fail 'UFW does not allow SSH'
(( failures == 0 )) || exit 1
printf '\\nAll SSH access checks passed.\\n'
EOF
chmod 0755 /usr/local/sbin/devsembly-ssh-validate

/usr/local/sbin/devsembly-ssh-validate
mkdir -p "$(dirname "$STATUS_FILE")"
printf 'status=complete\nadmin_user=%s\npassword_auth=%s\ntimestamp=%s\n' \
  "$ADMIN_USER" "$SSH_PASSWORD_AUTH" "$(date --iso-8601=seconds)" > "$STATUS_FILE"

echo "SSH access configuration complete for $ADMIN_USER."
