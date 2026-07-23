<!-- SPDX-FileCopyrightText: 2026 Bora Yarkın -->
<!-- SPDX-License-Identifier: GPL-3.0-only -->

# Python Relay Bundle

This bundle contains only the self-hosted Python relay runtime, the bundled phone web UI, and helper scripts for foreground use or service installation.

The bundle root contains only:

- `configure.sh`
- `configure.ps1`

Everything else lives under `relay-runtime/`.

It serves:

- `/` for the phone UI
- `/ws` for the relay websocket transport
- `/api/session` for admission-controlled session status
- `/health` for runtime and limit information
- `/asset-manifest.json` for bundle verification

## When To Use It

Use this relay only when Local network mode is not enough and the phone cannot reach LibreOffice directly. Local network mode is simpler and should be tried first.

The relay should be reachable by the phone over HTTPS. A public URL such as `https://remote.example.com` should proxy to the relay port and support WebSockets.

## Linux Or macOS

Extract the relay zip, enter the extracted folder, then run:

```bash
chmod +x configure.sh
./configure.sh
```

Use `sudo ./configure.sh` when installing or uninstalling a Linux system service.

The configure script asks what to do:

- run once in the current terminal
- install as a service
- uninstall the service

It also asks for a port. Leave the port empty to use the default random-port behavior. The chosen runtime configuration is stored in `relay-runtime/data/service.json` for foreground runs, or in the installed service directory for service installs.

For a Linux service:

```bash
sudo ./configure.sh
sudo systemctl status impress-remote-relay
sudo journalctl -u impress-remote-relay -f
```

## Windows

Extract the relay zip, open PowerShell as Administrator in the extracted folder, then run:

```powershell
Set-ExecutionPolicy -Scope Process Bypass
.\configure.ps1
```

Choose run once, install service, or uninstall service when prompted.

## Health Check

After the relay starts, test it locally:

```bash
curl http://127.0.0.1:<port>/health
```

The response should contain `"ok": true`.

Then test the public URL that you will enter in LibreOffice:

```bash
curl https://remote.example.com/health
```

If `/health` works but phones get stuck connecting, check that your proxy supports WebSockets for `/ws`.

## LibreOffice Settings

In LibreOffice Impress:

1. Open `Slide Show -> Remote Settings`.
2. Select `Relay Server`.
3. Enter the public relay URL, for example `https://remote.example.com`.
4. Choose `Save`.
5. Choose `Slide Show -> Start Remote`.
6. Scan the QR code.
