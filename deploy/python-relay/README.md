<!-- SPDX-FileCopyrightText: 2026 Bora Yarkın -->
<!-- SPDX-License-Identifier: GPL-3.0-only -->

# Python Relay Bundle

This bundle contains only the self-hosted Python relay runtime, the bundled phone web UI, and helper scripts for foreground use or service installation.

It serves:

- `/` for the phone UI
- `/ws` for the relay websocket transport
- `/api/session` for admission-controlled session status
- `/health` for runtime and limit information
- `/asset-manifest.json` for bundle verification

## Quick run

Linux or macOS:

```bash
./run-relay.sh
```

Windows PowerShell:

```powershell
.\run-relay.ps1
```

The first run creates `data/service.json`, picks a random free port, installs Python dependencies into `.venv`, and starts the relay in the foreground.

Health check:

```bash
curl http://127.0.0.1:<port>/health
```

Session-status check:

```bash
curl 'http://127.0.0.1:<port>/api/session?session=<session-id>&a=<admission-token>'
```

## Install as a service

Linux systemd:

```bash
sudo ./install-linux-service.sh
```

Windows service:

```powershell
.\install-windows-service.ps1
```

## Remove the service

Linux:

```bash
sudo ./uninstall-linux-service.sh
```

Windows:

```powershell
.\uninstall-windows-service.ps1
```
