#!/usr/bin/env bash
set -Eeuo pipefail

SRC_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
APP_DIR="/opt/morse-whisperer-pi"
SERVICE_USER="morsewhisperer"

echo "[mw-install] The Morse Whisperer recovery installer"
echo "[mw-install] Source: $SRC_DIR"
echo "[mw-install] Target: $APP_DIR"

if [ "$(id -u)" -ne 0 ]; then
  echo "[mw-install] ERROR: run with sudo"
  exit 1
fi

echo "[mw-install] Installing apt packages"
apt-get update
DEBIAN_FRONTEND=noninteractive apt-get install -y \
  python3 python3-venv python3-pip python3-numpy python3-pil python3-rpi.gpio \
  alsa-utils network-manager wireless-tools iw curl ca-certificates unzip \
  polkitd

if ! id "$SERVICE_USER" >/dev/null 2>&1; then
  echo "[mw-install] Creating service user: $SERVICE_USER"
  useradd --system --home "$APP_DIR" --shell /usr/sbin/nologin "$SERVICE_USER"
fi

echo "[mw-install] Creating app directory"
mkdir -p "$APP_DIR"
rsync -a --delete \
  --exclude 'venv' \
  --exclude 'patch-backups' \
  --exclude '__pycache__' \
  "$SRC_DIR"/ "$APP_DIR"/

echo "[mw-install] Creating Python venv"
python3 -m venv --system-site-packages "$APP_DIR/venv"
"$APP_DIR/venv/bin/python" -m pip install --upgrade pip wheel
"$APP_DIR/venv/bin/python" -m pip install flask numpy pillow

echo "[mw-install] Permissions"
chown -R root:root "$APP_DIR"
chmod -R a+rX "$APP_DIR"
chmod +x "$APP_DIR/tools/"*.sh || true
chmod +x "$APP_DIR/tools/"*.py || true

echo "[mw-install] Installing Polkit rule for NetworkManager"
cat >/etc/polkit-1/rules.d/49-morse-whisperer-networkmanager.rules <<EOF
// Allow The Morse Whisperer web service user to manage NetworkManager Wi-Fi
// for appliance setup/recovery.
// Scope is limited to the morse-whisperer service user.
polkit.addRule(function(action, subject) {
    if (
        subject.user == "$SERVICE_USER" &&
        (
            action.id == "org.freedesktop.NetworkManager.network-control" ||
            action.id == "org.freedesktop.NetworkManager.enable-disable-wifi" ||
            action.id == "org.freedesktop.NetworkManager.wifi.scan" ||
            action.id == "org.freedesktop.NetworkManager.settings.modify.system" ||
            action.id == "org.freedesktop.NetworkManager.settings.modify.own" ||
            action.id == "org.freedesktop.NetworkManager.settings.modify.hostname"
        )
    ) {
        return polkit.Result.YES;
    }
});
EOF
chmod 0644 /etc/polkit-1/rules.d/49-morse-whisperer-networkmanager.rules
chown root:root /etc/polkit-1/rules.d/49-morse-whisperer-networkmanager.rules
systemctl restart polkit 2>/dev/null || systemctl restart polkit.service 2>/dev/null || true

echo "[mw-install] Installing main systemd service"
cat >/etc/systemd/system/morse-whisperer.service <<EOF
[Unit]
Description=The Morse Whisperer CW Decoder Appliance
After=network-online.target sound.target
Wants=network-online.target

[Service]
Type=simple
User=$SERVICE_USER
Group=$SERVICE_USER
WorkingDirectory=$APP_DIR
Environment=PYTHONUNBUFFERED=1
ExecStartPre=/usr/bin/timeout 6s $APP_DIR/venv/bin/python $APP_DIR/tools/safe_splash_v2.py
ExecStart=$APP_DIR/venv/bin/python -m morse_whisperer
Restart=on-failure
RestartSec=4
NoNewPrivileges=yes

[Install]
WantedBy=multi-user.target
EOF

echo "[mw-install] Installing button sidecar service"
cat >/etc/systemd/system/morse-whisperer-buttons.service <<EOF
[Unit]
Description=The Morse Whisperer TFT Button Sidecar
After=morse-whisperer.service
Wants=morse-whisperer.service

[Service]
Type=simple
User=root
WorkingDirectory=$APP_DIR
ExecStart=$APP_DIR/tools/button_sidecar.sh
Restart=on-failure
RestartSec=2

[Install]
WantedBy=multi-user.target
EOF

echo "[mw-install] Installing NetworkManager fallback hotspot service disabled by default"
cat >/etc/systemd/system/morse-whisperer-network-fallback.service <<EOF
[Unit]
Description=The Morse Whisperer Wi-Fi setup hotspot fallback
After=NetworkManager.service
Wants=NetworkManager.service

[Service]
Type=oneshot
RemainAfterExit=yes
ExecStart=$APP_DIR/tools/network_fallback.sh start-if-needed
ExecStop=$APP_DIR/tools/network_fallback.sh stop
TimeoutStartSec=45
TimeoutStopSec=20

[Install]
WantedBy=multi-user.target
EOF

echo "[mw-install] Validating Python"
"$APP_DIR/venv/bin/python" -m py_compile \
  "$APP_DIR"/morse_whisperer/*.py \
  "$APP_DIR"/tools/network_connect_helper.py

echo "[mw-install] Enabling services"
systemctl daemon-reload
systemctl enable morse-whisperer.service
systemctl enable morse-whisperer-buttons.service
# fallback hotspot deliberately installed but not enabled yet
systemctl disable morse-whisperer-network-fallback.service >/dev/null 2>&1 || true

echo "[mw-install] Starting service"
systemctl restart morse-whisperer.service
systemctl restart morse-whisperer-buttons.service || true

sleep 4

echo
echo "[mw-install] Status:"
systemctl status morse-whisperer --no-pager -l | sed -n '1,35p' || true
echo
echo "[mw-install] IP address(es):"
hostname -I || true
echo
echo "[mw-install] Open:"
echo "  http://<pi-ip>:8080"
echo
echo "[mw-install] Fallback hotspot service is installed but disabled:"
echo "  sudo systemctl enable --now morse-whisperer-network-fallback.service"
