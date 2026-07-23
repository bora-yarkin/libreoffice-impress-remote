<!-- SPDX-FileCopyrightText: 2026 Bora Yarkın -->
<!-- SPDX-License-Identifier: GPL-3.0-only -->

# User Guide

LibreOffice Impress Remote turns a phone browser into a presenter remote for LibreOffice Impress. The goal is simple: start the remote from Impress, scan a QR code, see the current slide and notes on the phone, and control the slideshow without installing an app on the phone.

The main supported workflow is **Local network** mode. Use the experimental modes only when local networking is not enough.

## Install Or Update

Download the versioned OXT file from the GitHub Release. It will look like this:

```text
libreoffice-impress-remote-1.0.0.oxt
```

Install it from LibreOffice:

1. Open LibreOffice.
2. Choose `Tools -> Extension Manager`.
3. Choose `Add`.
4. Select the downloaded `.oxt` file.
5. Accept the install prompts.
6. Restart LibreOffice if it asks you to.
7. Open a presentation in LibreOffice Impress.

You can also install with `unopkg` if it is available on your system:

```bash
unopkg add -f libreoffice-impress-remote-1.0.0.oxt
```

If you are updating from an older build and LibreOffice behaves like stale code is still loaded, remove the old extension in `Tools -> Extension Manager`, restart LibreOffice, then install the new `.oxt`.

The extension is meant for Impress. The remote menu is shown under `Slide Show` when an Impress presentation is active.

To uninstall it, open `Tools -> Extension Manager`, select `LibreOffice Impress Remote`, choose `Remove`, and restart LibreOffice if asked.

## Start A Local Remote

1. Put the phone and computer on the same network.
2. Open the presentation in LibreOffice Impress.
3. Choose `Slide Show -> Start Remote`.
4. Scan the QR code with the phone.
5. Use the phone as the presenter remote.

The QR popup contains only the QR code and `Copy URL`. It closes automatically after a real phone connects. If the phone camera cannot scan the QR code, use `Copy URL` and open the copied link on the phone. Do not edit or remove the `#...` fragment in the URL; it contains pairing data.

When the phone connects, LibreOffice starts the slideshow from the first slide. The phone remote advances effects before moving to the next slide, so presentations with animations should behave like a normal clicker.

## Hotspot Workflow

Phone hotspots are often the easiest reliable setup because the phone and laptop are on a private network controlled by the phone.

1. Turn on the phone hotspot.
2. Connect the computer running LibreOffice to that hotspot.
3. Keep `Slide Show -> Remote Settings` on `Local network`.
4. Choose `Slide Show -> Start Remote`.
5. Scan the QR code with the same phone.

An iPhone hotspot URL such as `http://172.20.10.8:17865/#...` is normal. Some mobile browsers do not expose Web Crypto on plain local HTTP pages, so local mode can use an authenticated LAN-only fallback. Use local mode only on networks you trust.

## Remote Settings

Open `Slide Show -> Remote Settings` only when you need to change the connection mode.

Remote Settings contains:

- `Mode`: chooses what `Start Remote` will use next.
- `Relay Server`: appears only when Relay Server mode is selected.
- `Get Relay Server`: exports the matching Python relay bundle included in the installed extension.
- `Help`: opens this bundled user guide inside LibreOffice.
- `Save`: saves settings.
- `Close`: closes without starting a remote.

Changing settings while the remote is running stops the remote. Start it again to use the saved mode.

## Connection Modes

| Mode | Status | Use When | Notes |
| --- | --- | --- | --- |
| Local network | Recommended | Phone and computer are on the same Wi-Fi or hotspot. | This is the tested main path. Try this first. |
| Direct IPv6 | Experimental | Both devices have working public IPv6 and the desktop firewall allows the remote port. | Many home routers, hotspots, and firewalls block this even when IPv6 exists. |
| Relay Server | Experimental | You run the included Python relay on a VPS or server. | The relay forwards encrypted remote traffic. Enter the relay URL before starting. |
| LocalTunnel | Experimental | Local network access is blocked and you want a temporary public URL. | Treat the generated URL as secret. Availability depends on the tunnel service. |

If you are presenting in a normal room, office, classroom, or hotspot setup, use Local network mode.

## Phone Controls

The phone page is deliberately not a settings app. It is only the remote.

It shows:

- the current slide image pinned to the top
- the slide number as `current / total`
- presenter notes in the scrollable middle area
- previous and next controls pinned to the bottom
- tap-to-advance on the slide image
- presentation timer and current-slide timer
- fullscreen slide mode
- first slide, last slide, timer pause/resume, and go-to-slide in the menu
- reconnect/offline feedback if the connection drops

Previous and next are effect-aware. If the current slide has animations or builds, the next action should step through them before changing slides.

## Relay Server Mode

Relay Server mode is for cases where the phone cannot reach LibreOffice directly. You need your own server or VPS.

### Export The Matching Relay

The relay package is bundled inside the OXT so the server version matches the extension version.

1. Open `Slide Show -> Remote Settings`.
2. Select `Relay Server`.
3. Choose `Get Relay Server` and export the bundled relay package.
4. LibreOffice creates a folder containing a zip such as `impress-remote-relay-python-1.0.0.zip`.
5. Copy that zip to your server.

### Install On Linux

On the server:

```bash
unzip impress-remote-relay-python-1.0.0.zip
cd impress-remote-relay-python-1.0.0
chmod +x configure.sh
sudo ./configure.sh
```

The script asks what you want to do:

- `run once`: starts the relay in the current terminal, useful for quick testing.
- `install service`: installs it as a continuously running system service.
- `uninstall service`: removes the installed service.

When it asks for a port, leave it empty to let the relay choose its default random empty port, or enter a specific port if your reverse proxy expects one.

After installation, check the service:

```bash
sudo systemctl status impress-remote-relay
sudo journalctl -u impress-remote-relay -f
```

Open the health endpoint through the local port or your public domain:

```bash
curl http://127.0.0.1:PORT/health
curl https://remote.example.com/health
```

The health response should be JSON containing `"ok": true`.

### Install On Windows

Extract the relay zip, open PowerShell as Administrator in the extracted folder, then run:

```powershell
Set-ExecutionPolicy -Scope Process Bypass
.\configure.ps1
```

Choose `run once`, `install service`, or `uninstall service` when prompted. If Windows blocks the script, confirm you are running PowerShell as Administrator and that you used the temporary execution-policy command above.

### Publish The Relay URL

The phone browser should use HTTPS for relay mode. Put a reverse proxy, HTTPS tunnel, or server frontend in front of the relay port and make sure it supports WebSockets.

Your public relay URL should look like this:

```text
https://remote.example.com
```

These paths must work through the public URL:

- `/health`
- `/`
- `/ws`
- `/api/session`

### Use The Relay From LibreOffice

1. Open `Slide Show -> Remote Settings`.
2. Select `Relay Server`.
3. Enter the public relay URL, for example `https://remote.example.com`.
4. Choose `Save`.
5. Choose `Slide Show -> Start Remote`.
6. Scan the QR code with the phone.

The relay should be served over HTTPS. The relay sees encrypted frames and connection metadata, but it should not need to understand slide contents or commands.

## Troubleshooting

If the phone cannot open the link:

- Make sure the phone and computer are on the same Wi-Fi or hotspot for Local network mode.
- Try the phone hotspot workflow.
- Check whether a desktop firewall is blocking LibreOffice.
- Use `Copy URL` from the QR popup and paste it into the phone browser.
- Do not remove the URL fragment after `#`.

If LibreOffice cannot start the remote:

- Confirm the active document is an Impress presentation.
- Close and reopen LibreOffice after installing or updating the extension.
- Try a different mode only after Local network mode fails.
- If an error popup appears, use `Copy Error` and include the copied text when reporting the issue.

If Relay Server mode gets stuck:

- Open the relay URL `/health` endpoint in a browser and confirm it returns JSON.
- Confirm the Relay Server URL in Remote Settings starts with `https://` when used from a phone browser.
- Check your reverse proxy or firewall supports WebSockets.
- Restart the remote after changing the relay URL.

## Project Expectations

This is a volunteer FOSS extension. Local network mode is the main supported path right now. Direct IPv6, Relay Server, and LocalTunnel modes are useful for testing and hard networks, but they are experimental unless you have verified them in your own environment.
