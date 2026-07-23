#!/usr/bin/env bash
# SPDX-FileCopyrightText: 2026 Bora Yarkın
# SPDX-License-Identifier: GPL-3.0-only

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
RUNTIME_DIR="$ROOT_DIR/relay-runtime"
PYTHON_BIN="${PYTHON_BIN:-python3}"
SERVICE_NAME="${SERVICE_NAME:-impress-remote-relay}"
SERVICE_USER="${SERVICE_USER:-$SERVICE_NAME}"
INSTALL_DIR="${INSTALL_DIR:-/opt/$SERVICE_NAME}"
CONFIG_PATH="$INSTALL_DIR/data/service.json"
SERVICE_PATH="/etc/systemd/system/$SERVICE_NAME.service"

if [ ! -d "$RUNTIME_DIR" ]; then
  echo "Could not find relay runtime folder: $RUNTIME_DIR"
  exit 1
fi

print_menu() {
  echo "LibreOffice Impress Remote Relay"
  echo
  echo "1) Run once in this terminal"
  echo "2) Install as a Linux systemd service"
  echo "3) Uninstall the Linux systemd service"
  echo
}

read_port() {
  printf "Port [leave empty for random/default behavior]: "
  read -r port
  if [ -n "$port" ] && ! [[ "$port" =~ ^[0-9]+$ ]]; then
    echo "Port must be a number."
    exit 1
  fi
}

run_once() {
  local port="$1"
  local venv_dir="${VENV_DIR:-$RUNTIME_DIR/.venv}"
  if [ ! -x "$venv_dir/bin/python" ]; then
    "$PYTHON_BIN" -m venv "$venv_dir"
  fi
  "$venv_dir/bin/python" -m pip install --upgrade pip
  "$venv_dir/bin/python" -m pip install -r "$RUNTIME_DIR/requirements.txt"
  if [ -n "$port" ]; then
    exec "$venv_dir/bin/python" "$RUNTIME_DIR/run-relay.py" --port "$port"
  else
    exec "$venv_dir/bin/python" "$RUNTIME_DIR/run-relay.py"
  fi
}

install_service_as_root() {
  local port="$1"
  local port_args=()
  if [ -n "$port" ]; then
    port_args=(--port "$port")
  fi

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

  if ! id -u "$SERVICE_USER" >/dev/null 2>&1; then
    local nologin_bin
    nologin_bin="$(command -v nologin || true)"
    if [ -z "$nologin_bin" ]; then
      nologin_bin="/usr/bin/false"
    fi
    useradd --system --home "$INSTALL_DIR" --shell "$nologin_bin" "$SERVICE_USER"
  fi

  rm -rf "$INSTALL_DIR"
  mkdir -p "$INSTALL_DIR"
  cp -a "$RUNTIME_DIR"/. "$INSTALL_DIR"/
  rm -rf "$INSTALL_DIR/.venv" "$INSTALL_DIR/data"
  mkdir -p "$INSTALL_DIR/data"

  "$PYTHON_BIN" -m venv "$INSTALL_DIR/.venv"
  "$INSTALL_DIR/.venv/bin/python" -m pip install --upgrade pip
  "$INSTALL_DIR/.venv/bin/python" -m pip install -r "$INSTALL_DIR/requirements.txt"
  "$INSTALL_DIR/.venv/bin/python" "$INSTALL_DIR/run-relay.py" --config "$CONFIG_PATH" "${port_args[@]}" --ensure-config-only >/dev/null
  local selected_port
  selected_port="$("$INSTALL_DIR/.venv/bin/python" "$INSTALL_DIR/run-relay.py" --config "$CONFIG_PATH" --print-port)"

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
  echo "Listening port: $selected_port"
  echo "Health URL: http://<server-host>:$selected_port/health"
}

install_service() {
  local port="$1"
  if [ "$(id -u)" -eq 0 ]; then
    install_service_as_root "$port"
    return
  fi
  if ! command -v sudo >/dev/null 2>&1; then
    echo "Install requires root. Re-run with sudo or install sudo."
    exit 1
  fi
  if [ -n "$port" ]; then
    sudo "$ROOT_DIR/configure.sh" --install-service "$port"
  else
    sudo "$ROOT_DIR/configure.sh" --install-service
  fi
}

uninstall_service_as_root() {
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
}

uninstall_service() {
  if [ "$(id -u)" -eq 0 ]; then
    uninstall_service_as_root
    return
  fi
  if ! command -v sudo >/dev/null 2>&1; then
    echo "Uninstall requires root. Re-run with sudo or install sudo."
    exit 1
  fi
  sudo "$ROOT_DIR/configure.sh" --uninstall-service
}

case "${1:-}" in
  --install-service)
    install_service_as_root "${2:-}"
    exit 0
    ;;
  --uninstall-service)
    uninstall_service_as_root
    exit 0
    ;;
esac

print_menu
printf "Choose an action [1-3]: "
read -r action
case "$action" in
  1)
    port=""
    read_port
    run_once "$port"
    ;;
  2)
    port=""
    read_port
    install_service "$port"
    ;;
  3)
    uninstall_service
    ;;
  *)
    echo "Unknown action: $action"
    exit 1
    ;;
esac
