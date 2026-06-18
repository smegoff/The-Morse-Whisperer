#!/usr/bin/env bash
set -Eeuo pipefail

SRC_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
APP_DIR="/opt/morse-whisperer-pi"
SERVICE_USER="morsewhisperer"
SERVICE_GROUP="morsewhisperer"
CONFIG_BACKUP=""

cleanup() {
  if [ -n "$CONFIG_BACKUP" ] && [ -f "$CONFIG_BACKUP" ]; then
    rm -f "$CONFIG_BACKUP"
  fi
}
trap cleanup EXIT

echo "[mw-install] The Morse Whisperer one-shot installer"
echo "[mw-install] Source: $SRC_DIR"
echo "[mw-install] Target: $APP_DIR"

if [ "$(id -u)" -ne 0 ]; then
  echo "[mw-install] ERROR: run with sudo"
  exit 1
fi

echo
echo "[mw-install] Installing apt packages"
apt-get update
DEBIAN_FRONTEND=noninteractive apt-get install -y \
  python3 python3-venv python3-pip python3-numpy python3-pil python3-rpi.gpio \
  alsa-utils network-manager wireless-tools iw curl ca-certificates unzip rsync \
  polkitd

if ! getent group "$SERVICE_GROUP" >/dev/null 2>&1; then
  echo "[mw-install] Creating service group: $SERVICE_GROUP"
  groupadd --system "$SERVICE_GROUP"
fi

if ! id "$SERVICE_USER" >/dev/null 2>&1; then
  echo "[mw-install] Creating service user: $SERVICE_USER"
  useradd --system --home "$APP_DIR" --shell /usr/sbin/nologin --gid "$SERVICE_GROUP" "$SERVICE_USER"
else
  usermod -a -G "$SERVICE_GROUP" "$SERVICE_USER" || true
fi

echo
echo "[mw-install] Creating app directory"
mkdir -p "$APP_DIR"

if [ -f "$APP_DIR/config.json" ]; then
  CONFIG_BACKUP="$(mktemp)"
  cp -a "$APP_DIR/config.json" "$CONFIG_BACKUP"
  echo "[mw-install] Preserving existing runtime config"
fi

rsync -a --delete \
  --exclude '.git' \
  --exclude 'venv' \
  --exclude 'patch-backups' \
  --exclude 'mw-recovery-backups' \
  --exclude 'recovery-backups' \
  --exclude '__pycache__' \
  --exclude '*.pyc' \
  --exclude '*.tmp' \
  "$SRC_DIR"/ "$APP_DIR"/

if [ -n "$CONFIG_BACKUP" ]; then
  cp -a "$CONFIG_BACKUP" "$APP_DIR/config.json"
fi

echo
echo "[mw-install] Creating Python venv"
python3 -m venv --system-site-packages "$APP_DIR/venv"
"$APP_DIR/venv/bin/python" -m pip install --upgrade pip wheel
"$APP_DIR/venv/bin/python" -m pip install -r "$APP_DIR/requirements.txt"

echo
echo "[mw-install] Ensuring profile files exist"
mkdir -p "$APP_DIR/profiles"

if [ ! -f "$APP_DIR/profiles/clean.json" ]; then
  cat >"$APP_DIR/profiles/clean.json" <<'JSON'
{
  "decoder_profile": "clean",
  "decoder_profile_name": "Clean CW",
  "sample_rate": 8000,
  "tone_mode": "session_auto",
  "target_tone_hz": 700,
  "allowed_tones_hz": [400, 500, 550, 600, 650, 700, 750, 800, 850, 900, 950, 1000],
  "audio_filter_enabled": true,
  "audio_filter_mode": "wide",
  "audio_filter_wide_hz": 500,
  "audio_filter_narrow_hz": 220,
  "audio_filter_bandwidth_hz": 300,
  "audio_filter_max_hz": 1200,
  "threshold_bias": 0.48,
  "min_element_fraction": 0.45,
  "copy_min_decoded_symbols": 5,
  "copy_max_failed_symbols": 0,
  "copy_min_confidence": 0.85,
  "copy_min_snr": 12.0,
  "decode_window_sec": 10,
  "char_gap_units": 2.7,
  "word_gap_units": 5.6,
  "adaptive_word_gap_enabled": true,
  "adaptive_word_gap_min_units": 5.2,
  "adaptive_word_gap_max_units": 6.8
}
JSON
fi

if [ ! -f "$APP_DIR/profiles/kiwi.json" ]; then
  cat >"$APP_DIR/profiles/kiwi.json" <<'JSON'
{
  "decoder_profile": "kiwi",
  "decoder_profile_name": "Radio CW",
  "sample_rate": 8000,
  "tone_mode": "session_auto",
  "target_tone_hz": 650,
  "allowed_tones_hz": [400, 450, 500, 550, 600, 650, 700, 750, 800, 850, 900, 950, 1000, 1050, 1100, 1150, 1200, 1250, 1300, 1350, 1400, 1450, 1500, 1550, 1600, 1650, 1700, 1750, 1800, 1850, 1900, 1950, 2000],
  "audio_filter_enabled": true,
  "audio_filter_mode": "narrow",
  "audio_filter_wide_hz": 500,
  "audio_filter_narrow_hz": 260,
  "audio_filter_bandwidth_hz": 300,
  "audio_filter_max_hz": 1200,
  "threshold_bias": 0.50,
  "min_element_fraction": 0.45,
  "copy_min_decoded_symbols": 3,
  "copy_max_failed_symbols": 1,
  "copy_min_confidence": 0.70,
  "copy_min_snr": 7.0,
  "decode_window_sec": 16,
  "char_gap_units": 2.7,
  "word_gap_units": 5.6,
  "adaptive_word_gap_enabled": true,
  "adaptive_word_gap_min_units": 5.0,
  "adaptive_word_gap_max_units": 7.2
}
JSON
fi

echo
echo "[mw-install] Permissions"
chown -R root:"$SERVICE_GROUP" "$APP_DIR"
chmod 775 "$APP_DIR"
chmod -R a+rX "$APP_DIR"
chmod 775 "$APP_DIR/tools" 2>/dev/null || true
chmod 775 "$APP_DIR/patch-backups" 2>/dev/null || true
mkdir -p "$APP_DIR/patch-backups/profile-switch-runtime"
chown -R root:"$SERVICE_GROUP" "$APP_DIR/patch-backups"
chmod -R 775 "$APP_DIR/patch-backups"

if [ -f "$APP_DIR/config.json" ]; then
  chown root:"$SERVICE_GROUP" "$APP_DIR/config.json"
  chmod 664 "$APP_DIR/config.json"
fi

mkdir -p /etc/morse-whisperer
touch /etc/morse-whisperer/ai.env
chown root:"$SERVICE_GROUP" /etc/morse-whisperer /etc/morse-whisperer/ai.env
chmod 775 /etc/morse-whisperer
chmod 660 /etc/morse-whisperer/ai.env

chmod +x "$APP_DIR/tools/"*.sh 2>/dev/null || true
chmod +x "$APP_DIR/tools/"*.py 2>/dev/null || true

echo
echo "[mw-install] Installing Polkit rule for NetworkManager"
cat >/etc/polkit-1/rules.d/49-morse-whisperer-networkmanager.rules <<POLKIT
// Allow The Morse Whisperer web service user to manage NetworkManager Wi-Fi
// for appliance setup/recovery.
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
POLKIT
chmod 0644 /etc/polkit-1/rules.d/49-morse-whisperer-networkmanager.rules
chown root:root /etc/polkit-1/rules.d/49-morse-whisperer-networkmanager.rules

echo
echo "[mw-install] Installing Polkit rule for profile restart"
cat >/etc/polkit-1/rules.d/49-morse-whisperer-profile-restart.rules <<POLKIT
// Allow The Morse Whisperer service group to restart only the main decoder service.
// This is used by the web UI profile switch.
polkit.addRule(function(action, subject) {
    if (
        subject.isInGroup("$SERVICE_GROUP") &&
        action.id == "org.freedesktop.systemd1.manage-units"
    ) {
        var unit = action.lookup("unit");
        var verb = action.lookup("verb");

        if (
            unit == "morse-whisperer.service" &&
            (verb == "restart" || verb == "start" || verb == "stop")
        ) {
            return polkit.Result.YES;
        }
    }
});
POLKIT
chmod 0644 /etc/polkit-1/rules.d/49-morse-whisperer-profile-restart.rules
chown root:root /etc/polkit-1/rules.d/49-morse-whisperer-profile-restart.rules

systemctl restart polkit 2>/dev/null || systemctl restart polkit.service 2>/dev/null || true

echo
echo "[mw-install] Installing main systemd service"
cat >/etc/systemd/system/morse-whisperer.service <<SYSTEMD
[Unit]
Description=The Morse Whisperer CW Decoder Appliance
After=network-online.target sound.target
Wants=network-online.target

[Service]
Type=simple
User=$SERVICE_USER
Group=$SERVICE_GROUP
SupplementaryGroups=audio video input
WorkingDirectory=$APP_DIR
Environment=PYTHONUNBUFFERED=1
EnvironmentFile=-/etc/morse-whisperer/ai.env
ExecStartPre=/usr/bin/timeout 6s $APP_DIR/venv/bin/python $APP_DIR/tools/safe_splash_v2.py
ExecStart=$APP_DIR/venv/bin/python -m morse_whisperer
Restart=on-failure
RestartSec=4
NoNewPrivileges=yes

[Install]
WantedBy=multi-user.target
SYSTEMD

echo
echo "[mw-install] Installing button sidecar service"
cat >/etc/systemd/system/morse-whisperer-buttons.service <<SYSTEMD
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
SYSTEMD

echo
echo "[mw-install] Installing NetworkManager fallback hotspot service disabled by default"
cat >/etc/systemd/system/morse-whisperer-network-fallback.service <<SYSTEMD
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
SYSTEMD

echo
echo "[mw-install] Validating Python"
"$APP_DIR/venv/bin/python" -m py_compile \
  "$APP_DIR"/morse_whisperer/*.py \
  "$APP_DIR"/tools/*.py

echo
echo "[mw-install] Enabling services"
systemctl daemon-reload
systemctl enable morse-whisperer.service
systemctl enable morse-whisperer-buttons.service
systemctl disable morse-whisperer-network-fallback.service >/dev/null 2>&1 || true

echo
echo "[mw-install] Starting services"
systemctl restart morse-whisperer.service
systemctl restart morse-whisperer-buttons.service || true

sleep 5

echo
echo "[mw-install] Status:"
systemctl status morse-whisperer.service --no-pager -l | sed -n '1,45p' || true

echo
echo "[mw-install] Profile:"
"$APP_DIR/tools/set_decoder_profile.py" show || true

echo
echo "[mw-install] IP address(es):"
hostname -I || true

echo
echo "[mw-install] Open:"
echo "  http://<pi-ip>:8080"

echo
echo "[mw-install] Fallback hotspot service is installed but disabled:"
echo "  sudo systemctl enable --now morse-whisperer-network-fallback.service"
