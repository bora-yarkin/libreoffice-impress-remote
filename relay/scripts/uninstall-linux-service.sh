#!/usr/bin/env bash
# SPDX-FileCopyrightText: 2026 Bora Yarkın
# SPDX-License-Identifier: GPL-3.0-only

set -euo pipefail

if [ "$(id -u)" -ne 0 ]; then
  echo "Run this uninstaller with sudo or as root."
  exit 1
fi

SERVICE_NAME="${SERVICE_NAME:-impress-remote-relay}"
SERVICE_USER="${SERVICE_USER:-$SERVICE_NAME}"
INSTALL_DIR="${INSTALL_DIR:-/opt/$SERVICE_NAME}"
SERVICE_PATH="/etc/systemd/system/$SERVICE_NAME.service"

if command -v systemctl >/dev/null 2>&1; then
  systemctl disable --now "$SERVICE_NAME" >/dev/null 2>&1 || true
  rm -f "$SERVICE_PATH"
  systemctl daemon-reload || true
fi

rm -rf "$INSTALL_DIR"

if id -u "$SERVICE_USER" >/dev/null 2>&1; then
  userdel "$SERVICE_USER" >/dev/null 2>&1 || true
fi

echo "Removed $SERVICE_NAME"
