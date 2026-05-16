#!/usr/bin/env bash
set -Eeuo pipefail

APP_DIR="/opt/morse-whisperer-pi"
SERVICE_USER="morsewhisperer"
REPO_ZIP="https://github.com/smegoff/The-Morse-Whisperer/archive/refs/heads/main.zip"
TMP_DIR="$(mktemp -d)"
CONFIG_TXT="/boot/firmware/config.txt"

log(){ echo "[morse-whisperer] $*"; }
fail(){ echo "[morse-whisperer] ERROR: $*" >&2; exit 1; }

[ "$(id -u)" -eq 0 ] || fail "run with sudo"
trap 'rm -rf "$TMP_DIR"' EXIT

log "Installing packages"
apt-get update
DEBIAN_FRONTEND=noninteractive apt-get install -y \
  python3 python3-venv python3-pip python3-numpy python3-pil python3-rpi.gpio \
  alsa-utils network-manager wireless-tools iw curl ca-certificates unzip rsync \
  polkitd fonts-dejavu-core

log "Downloading current repository"
curl -fsSL "$REPO_ZIP" -o "$TMP_DIR/repo.zip"
unzip -q "$TMP_DIR/repo.zip" -d "$TMP_DIR"
SRC_DIR="$(find "$TMP_DIR" -maxdepth 1 -type d -name 'The-Morse-Whisperer-*' | head -1)"
[ -n "$SRC_DIR" ] || fail "could not unpack repository"

if ! id "$SERVICE_USER" >/dev/null 2>&1; then
  log "Creating service user: $SERVICE_USER"
  useradd --system --home "$APP_DIR" --shell /usr/sbin/nologin "$SERVICE_USER"
fi

log "Installing app into $APP_DIR"
mkdir -p "$APP_DIR"
rsync -a --delete \
  --exclude '.git' \
  --exclude 'docs' \
  --exclude 'systemd' \
  --exclude 'polkit' \
  --exclude 'screenshots' \
  --exclude '__pycache__' \
  --exclude 'venv' \
  "$SRC_DIR"/ "$APP_DIR"/

if [ ! -f "$APP_DIR/config.json" ]; then
  cp "$APP_DIR/config.example.json" "$APP_DIR/config.json"
fi

log "Creating Python virtual environment"
python3 -m venv --system-site-packages "$APP_DIR/venv"
"$APP_DIR/venv/bin/python" -m pip install --upgrade pip wheel
"$APP_DIR/venv/bin/python" -m pip install -r "$APP_DIR/requirements.txt"

log "Installing systemd units"
install -m 0644 "$SRC_DIR/systemd/morse-whisperer.service" /etc/systemd/system/morse-whisperer.service
install -m 0644 "$SRC_DIR/systemd/morse-whisperer-buttons.service" /etc/systemd/system/morse-whisperer-buttons.service

log "Installing NetworkManager Polkit rule"
install -d -m 0755 /etc/polkit-1/rules.d
install -m 0644 "$SRC_DIR/polkit/49-morse-whisperer-networkmanager.rules" /etc/polkit-1/rules.d/49-morse-whisperer-networkmanager.rules
systemctl reload polkit 2>/dev/null || systemctl restart polkit 2>/dev/null || true

log "Setting permissions"
chown -R root:root "$APP_DIR"
chmod -R a+rX "$APP_DIR"
chmod +x "$APP_DIR/tools/"*.py "$APP_DIR/tools/"*.sh 2>/dev/null || true
chown root:"$SERVICE_USER" "$APP_DIR" "$APP_DIR/config.json"
chmod 775 "$APP_DIR"
chmod 664 "$APP_DIR/config.json"

if [ -f "$CONFIG_TXT" ]; then
  log "Checking TFT boot overlay in $CONFIG_TXT"
  cp -a "$CONFIG_TXT" "$CONFIG_TXT.bak-morse-whisperer-$(date +%Y%m%d-%H%M%S)"
  grep -q '^dtparam=spi=on' "$CONFIG_TXT" || echo 'dtparam=spi=on' >> "$CONFIG_TXT"
  if grep -q '^dtoverlay=vc4-kms-v3d' "$CONFIG_TXT"; then
    sed -i 's/^dtoverlay=vc4-kms-v3d/#dtoverlay=vc4-kms-v3d/' "$CONFIG_TXT"
  fi
  if ! grep -q '^dtoverlay=pitft28-resistive,rotate=90,speed=32000000,fps=20' "$CONFIG_TXT"; then
    cat >> "$CONFIG_TXT" <<'EOF'

# Morse Whisperer XC9022 / GoodTFT 2.8 inch SPI LCD
dtparam=spi=on
dtoverlay=pitft28-resistive,rotate=90,speed=32000000,fps=20
EOF
  fi
fi

log "Enabling services"
systemctl daemon-reload
systemctl enable morse-whisperer.service
systemctl enable morse-whisperer-buttons.service || true
systemctl restart morse-whisperer.service
systemctl restart morse-whisperer-buttons.service || true

sleep 3
systemctl status morse-whisperer --no-pager -l | sed -n '1,50p' || true

IP_ADDR="$(hostname -I 2>/dev/null | awk '{print $1}')"
log "Done"
log "Open: http://${IP_ADDR:-<pi-ip>}:8080"
log "If this is a fresh TFT install, reboot now: sudo reboot"
