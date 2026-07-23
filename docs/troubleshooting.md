<!-- SPDX-FileCopyrightText: 2026 Bora Yarkın -->
<!-- SPDX-License-Identifier: GPL-3.0-only -->

# Troubleshooting

This guide covers install, pairing, and runtime failures for the current local-first extension.

## Rebuild And Reinstall Cleanly

```bash
make oxt
make install-oxt
```

Quit LibreOffice before reinstalling. LibreOffice can keep old extension code loaded while any LibreOffice process is still running.

The expected package name is:

```text
dist/libreoffice-impress-remote-<version>.oxt
```

## `premature end of file ... component.py`

This usually means LibreOffice cached or unpacked a broken OXT.

1. Quit LibreOffice completely.
2. Remove the extension from `Tools -> Extensions` if visible.
3. Run `make oxt`.
4. Install the freshly generated versioned OXT.
5. Start LibreOffice Impress again.

On macOS, stale unpacked extension cache entries are under:

```text
~/Library/Application Support/LibreOffice/4/user/uno_packages/cache/uno_packages/
```

If an error still points to an old temporary `*.tmp_` folder, remove the extension, quit LibreOffice, and reinstall the fresh OXT.

## Import Errors During Install

`No module named 'impress_remote'` means the OXT package layout is wrong or stale. Check:

```bash
unzip -l dist/libreoffice-impress-remote-*.oxt | grep 'python/impress_remote/component.py'
```

`No module named 'com'` means a LibreOffice UNO module was imported outside LibreOffice's runtime or too early during registration. Top-level extension imports must remain UNO-loader safe.

`NameError` during registration usually means a runtime-only class leaked into an evaluated annotation or top-level import path. Run compile checks, rebuild, and reinstall:

```bash
.venv/bin/python -m compileall -q extension/python
make oxt
```

## Menu Is Missing

The extension is Impress-only.

1. Open an actual Impress presentation.
2. Look under `Slide Show -> Start Remote` and `Slide Show -> Remote Settings`.
3. Restart LibreOffice after installation.
4. Reinstall the OXT if the commands remain missing.

Toolbar and notebookbar integration depends on LibreOffice UI mode. The Slide Show menu entries are the canonical controls.

## Remote Settings Does Not Open

1. Open an Impress document.
2. Choose `Slide Show -> Remote Settings`.
3. Restart LibreOffice if nothing happens.
4. Reinstall the OXT if both Start Remote and Remote Settings are inert.

When reporting this, include OS, LibreOffice version, extension version, and whether Start Remote works.

## QR Code Or Copy URL Is Missing

Use `Slide Show -> Start Remote`; the QR popup owns both the QR code and `Copy URL` fallback. Remote Settings only controls mode and relay settings.

If no QR/link is available:

- choose Local network for same-Wi-Fi or hotspot testing
- choose LocalTunnel only when a public tunnel is desired
- choose Direct IPv6 only when public IPv6 is available
- choose Relay Server only after saving a relay URL
- restart the remote after changing settings

## Phone Shows `Remote unavailable`

If Safari says Web Crypto is unavailable, use Local network mode on same Wi-Fi or hotspot. Local mode can use authenticated LAN-only fallback endpoints.

LocalTunnel, Direct IPv6, and Relay Server modes require Web Crypto and fail closed if the browser does not expose it.

## Local Pairing Does Not Connect

- Put phone and computer on the same Wi-Fi or the same phone hotspot.
- Disable VPNs that isolate local traffic.
- Allow inbound connections to the selected local port in the desktop firewall.
- Use `Copy URL` in the QR popup if the camera scanner fails.
- If public Wi-Fi blocks device-to-device traffic, use a phone hotspot first. LocalTunnel and Relay Server mode are experimental fallbacks.

Local URLs usually start with `192.168.x.x`, `10.x.x.x`, or `172.20.x.x`.

## LocalTunnel Does Not Connect

- Confirm Remote Settings is set to LocalTunnel.
- Start the remote again after saving settings.
- Wait for the tunnel URL before scanning.
- Treat provider interstitials, rate limits, or blocked tunnel domains as provider issues.
- Switch back to Local network for same-room testing when possible.

## Direct IPv6 Does Not Connect

- Confirm the desktop has a globally reachable IPv6 address.
- Confirm the desktop firewall allows the remote port.
- Confirm the phone network can reach that IPv6 address.
- If Remote Settings reports missing public IPv6 or failed self-test, use Local network, LocalTunnel, or Relay Server instead.

## Relay Pairing Does Not Connect

1. Save the relay base URL in Remote Settings while Relay Server mode is selected.
2. Confirm `/health` works on the relay.
3. Confirm websocket forwarding works on `/ws` if behind a reverse proxy.
4. Start the remote again after saving.
5. Scan the relay QR or copy the full URL with its `#mode=relay&s=...&k=...&a=...` fragment intact.

If LibreOffice reports `HTTP 403` on `/health` while a browser or `curl` can open it, check the reverse proxy/security product in front of the relay. Some providers block generic `Python-urllib` clients. Extension `1.0.0` sends a product User-Agent for relay health, session, and websocket requests.

See [Relay And Deployment](relay.md) for deployment details.
