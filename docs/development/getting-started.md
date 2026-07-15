<!-- SPDX-FileCopyrightText: 2026 Bora Yarkın -->
<!-- SPDX-License-Identifier: GPL-3.0-only -->

# Getting Started

This guide matches the `0.2.0` release line.

```bash
git clone https://github.com/bora-yarkin/libreoffice-impress-remote.git
cd libreoffice-impress-remote
make venv
make sdk-download
make test
make oxt
make install-oxt
```

On macOS, `make sdk-download` downloads the matching LibreOffice SDK disk image from the official archive and installs its SDK directory into `third_party/libreoffice-sdk/`.

Close LibreOffice before running `make install-oxt` so `unopkg` can replace the existing extension cleanly.

## Testing the local remote

After `make install-oxt`, open LibreOffice Impress and use:

```text
Slide Show -> Presentation Remote
```

1. Choose `Settings` to open the LibreOffice control panel.
2. Set the relay server if you want relay mode, keep the route on `Auto (Local -> IPv6 -> Relay)` unless you are forcing a specific path, and disable `Enable local` when you want a relay-only or direct-IPv6-only test.
3. Choose `Start` inside the dialog to bring up the embedded local server.
4. Scan the QR code shown by LibreOffice with your phone.
5. Choose `Open Console` if you also want to preview the current route in a desktop browser.

## Prototype Relay Mode

```bash
make server-dev
```

Then:

1. Open the LibreOffice settings dialog from the extension menu.
2. Enable relay mode, enter the relay base URL, and save.
3. Start the remote from the same dialog.
4. Change the route dropdown to `Relay server only` if you want to force relay mode during testing.
5. Scan the QR code on the phone.

The relay host now serves the phone UI at `/` and the relay WebSocket transport at `/ws`.

## Troubleshooting

If LibreOffice reports:

```text
premature end of file:///.../python/impress_remote/component.py
```

check the installed cache version under `~/Library/Application Support/LibreOffice/4/user/uno_packages/cache/uno_packages/`. If that cache still contains an older `description.xml` version than `dist/libreoffice-impress-remote.oxt`, LibreOffice is loading a stale package. Rebuild and reinstall with:

```bash
make oxt
make install-oxt
```

If the stale cache persists, remove the extension from LibreOffice Extension Manager, quit LibreOffice, then install the freshly built `dist/libreoffice-impress-remote.oxt` again.
