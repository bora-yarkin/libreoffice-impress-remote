#!/usr/bin/env bash
# SPDX-FileCopyrightText: 2026 Bora Yarkın
# SPDX-License-Identifier: GPL-3.0-only

set -euo pipefail

if [ "$(id -u)" -ne 0 ]; then
  echo "Run this installer with sudo or as root."
  exit 1
fi

SOURCE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SERVICE_NAME="${SERVICE_NAME:-impress-remote-relay}"
SERVICE_USER="${SERVICE_USER:-$SERVICE_NAME}"
INSTALL_DIR="${INSTALL_DIR:-/opt/$SERVICE_NAME}"
PYTHON_BIN="${PYTHON_BIN:-python3}"
CONFIG_PATH="$INSTALL_DIR/data/service.json"
SERVICE_PATH="/etc/systemd/system/$SERVICE_NAME.service"

if ! command -v systemctl >/dev/null 2>&1; then
  echo "systemctl is required to install the relay as a service."
  exit 1
fi

if ! command -v "$PYTHON_BIN" >/dev/null 2>&1; then
  echo "Python was not found at $PYTHON_BIN."
  exit 1
fi

if systemctl list-unit-files | grep -Fq "$SERVICE_NAME.service"; then
  systemctl disable --now "$SERVICE_NAME" >/dev/null 2>&1 || true
fi

if id -u "$SERVICE_USER" >/dev/null 2>&1; then
  true
else
  NOLOGIN_BIN="$(command -v nologin || true)"
  if [ -z "$NOLOGIN_BIN" ]; then
    NOLOGIN_BIN="/usr/bin/false"
  fi
  useradd --system --home "$INSTALL_DIR" --shell "$NOLOGIN_BIN" "$SERVICE_USER"
fi

rm -rf "$INSTALL_DIR"
mkdir -p "$INSTALL_DIR"
cp -a "$SOURCE_DIR"/. "$INSTALL_DIR"/
mkdir -p "$INSTALL_DIR/data"

"$PYTHON_BIN" -m venv "$INSTALL_DIR/.venv"
"$INSTALL_DIR/.venv/bin/python" -m pip install --upgrade pip
"$INSTALL_DIR/.venv/bin/python" -m pip install -r "$INSTALL_DIR/requirements.txt"
"$INSTALL_DIR/.venv/bin/python" "$INSTALL_DIR/run-relay.py" --config "$CONFIG_PATH" --ensure-config-only >/dev/null
PORT="$("$INSTALL_DIR/.venv/bin/python" "$INSTALL_DIR/run-relay.py" --config "$CONFIG_PATH" --print-port)"

chown -R "$SERVICE_USER":"$SERVICE_USER" "$INSTALL_DIR"

cat >"$SERVICE_PATH" <<EOF
[Unit]
Description=LibreOffice Impress Remote Relay
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
User=$SERVICE_USER
Group=$SERVICE_USER
WorkingDirectory=$INSTALL_DIR
ExecStart=$INSTALL_DIR/.venv/bin/python $INSTALL_DIR/run-relay.py --config $CONFIG_PATH
Restart=on-failure
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
systemctl enable --now "$SERVICE_NAME"

echo "Installed $SERVICE_NAME"
echo "Install directory: $INSTALL_DIR"
echo "Listening port: $PORT"
echo "Health URL: http://<server-host>:$PORT/health"
