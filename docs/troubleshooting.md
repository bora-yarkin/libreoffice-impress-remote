<!-- SPDX-FileCopyrightText: 2026 Bora Yarkın -->
<!-- SPDX-License-Identifier: GPL-3.0-only -->

# Troubleshooting

This guide focuses on extension loading, installation, and first-run problems.

## Rebuild And Reinstall Cleanly

Use this baseline when the installed extension behaves differently from the repository:

```bash
make oxt
make install-oxt
```

Close LibreOffice before reinstalling. LibreOffice can keep extension code cached while any LibreOffice process is still running.

The expected package name is versioned:

```text
dist/libreoffice-impress-remote-<version>.oxt
```

## `premature end of file ... component.py`

This usually means LibreOffice cached or unpacked a broken `.oxt`, not that `component.py` literally ends early in the repository.

Fix:

1. Quit LibreOffice completely.
2. Remove the extension from `Tools -> Extensions` if it is visible there.
3. Build a fresh OXT with `make oxt`.
4. Install `dist/libreoffice-impress-remote-<version>.oxt`.
5. Start LibreOffice Impress again.

On macOS, stale extension cache entries live under:

```text
~/Library/Application Support/LibreOffice/4/user/uno_packages/cache/uno_packages/
```

If the error still points to an old temporary `*.tmp_` folder after reinstalling, remove the extension from Extension Manager, quit LibreOffice, and install the freshly built OXT again.

## `No module named 'impress_remote'`

This means LibreOffice loaded `component.py`, but the extension package did not contain the expected Python package layout.

Check:

```bash
make oxt
unzip -l dist/libreoffice-impress-remote-*.oxt | grep 'python/impress_remote/component.py'
unzip -l dist/libreoffice-impress-remote-*.oxt | grep 'python/impress_remote/localization'
```

If either path is missing, rebuild from a clean repository state and reinstall the generated OXT.

## `NameError` During Extension Install

Errors like this:

```text
NameError: name 'RemoteServer' is not defined
```

usually come from evaluated type annotations or imports that LibreOffice's Python loader cannot resolve at registration time.

Fix:

1. Pull or apply the latest repository changes.
2. Run `python -m compileall -q extension/python`.
3. Run `make oxt`.
4. Reinstall the generated OXT.

The current codebase uses postponed annotations and import-safe component registration paths to avoid this class of failure.

## `No module named 'com'`

LibreOffice UNO modules such as `com.sun.star.*` are only available inside LibreOffice's Python/UNO runtime. Importing them at module load time can break extension registration.

The extension should avoid hard imports from `com.sun.star` in top-level module scope. If you see this error after local edits, move the UNO-specific import behind a runtime guard or into the function that needs it.

## Extension Installs But Menu Is Missing

The Presentation Remote menu is intentionally Impress-only.

Check:

1. Open a real Impress presentation, not Writer, Calc, Draw, or the LibreOffice Start Center.
2. Look under `Slide Show -> Presentation Remote`.
3. If it is still missing, restart LibreOffice after installation.
4. If it remains missing, remove and reinstall the OXT.

Toolbar integration depends on the active LibreOffice UI mode. The Slide Show submenu is the canonical entry point.

## Settings Dialog Does Not Open

Try this sequence:

1. Open an Impress document.
2. Choose `Slide Show -> Presentation Remote -> Advanced Remote Settings`.
3. If nothing happens, quit LibreOffice and start it again.
4. Reinstall the extension if the menu exists but every command is inert.

When reporting this bug, include the LibreOffice version, operating system, and whether `Start Remote` works.

## Phone Shows `Remote unavailable`

If Safari says:

```text
This browser does not expose Web Crypto required for encrypted remote transport.
```

make sure you installed a build at or after `0.6.12`. Local mode should fall back to authenticated plaintext polling when Safari does not expose Web Crypto on a LAN HTTP address.

Relay and direct IPv6 still require Web Crypto. If you forced Relay only or Direct IPv6 only, use a browser/context that exposes Web Crypto or switch back to Auto/Local for same-network testing.

## QR Code Is Empty Or Manual Link Is Missing

Open `Advanced Remote Settings` and check:

- local listener is enabled for local mode
- relay is enabled only if a relay URL is configured
- direct IPv6 is enabled only if the network provides public IPv6
- the remote is running

If Auto cannot find any route, enable local mode and restart the remote.

## Local Pairing Does Not Connect

Try:

1. Put the phone and computer on the same Wi-Fi or the same phone hotspot.
2. Disable VPNs or firewall rules that block local device connections.
3. Use the Manual Link in Advanced Remote Settings as a backup.
4. If public Wi-Fi blocks device-to-device traffic, use a phone hotspot or relay mode.

The local URL often starts with a private address such as `192.168.x.x`, `10.x.x.x`, or `172.20.x.x`.

## Relay Pairing Does Not Connect

Check:

1. The relay URL is saved in Advanced Remote Settings.
2. The relay is reachable over HTTPS or the expected HTTP test URL.
3. `/health` works on the relay.
4. The phone opens the full relay link with the `#mode=relay&s=...&k=...&a=...` fragment intact.
5. Reverse proxy websocket forwarding is enabled for `/ws`.

See [Relay Server](relay-server.md) for deployment details.
