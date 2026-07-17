<!-- SPDX-FileCopyrightText: 2026 Bora Yarkın -->
<!-- SPDX-License-Identifier: GPL-3.0-only -->

# Getting Started

This guide matches the `0.5.0` release line.

```bash
git clone https://github.com/bora-yarkin/libreoffice-impress-remote.git
cd libreoffice-impress-remote
make venv
make sdk-download
make test
make oxt
make install-oxt
make release-bundle
make cloudflare-bundle
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

## Relay Mode

```bash
make server-dev
```

Then:

1. Open the LibreOffice settings dialog from the extension menu.
2. Enable relay mode, enter the relay base URL, and save.
3. Start the remote from the same dialog.
4. Change the route dropdown to `Relay server only` if you want to force relay mode during testing.
5. Scan the QR code on the phone, or open the full pairing link with its `#...` fragment intact if you are testing the hosted relay page manually.
6. When the phone joins successfully, LibreOffice should detect the relay session and start the slideshow automatically.

The relay host now serves:

- `/` for the phone UI
- `/ws` for the relay websocket transport
- `/api/session` for admission-controlled session status
- `/health` for runtime and limit checks
- `/asset-manifest.json` for bundle verification

## Release Bundles

```bash
make release-bundle
make cloudflare-bundle
```

- `make release-bundle` produces a stripped standalone Python relay bundle with the relay Python sources, bundled phone web UI, and Linux or Windows service helper scripts under `dist/`.
- `make cloudflare-bundle` produces a Cloudflare Worker plus Durable Object relay bundle that serves the same shared phone UI from a `public/` assets directory.
- `make release-full` builds `dist/libreoffice-impress-remote.oxt` plus both relay bundle variants in one command.

Useful relay checks:

```bash
curl http://127.0.0.1:17865/health
curl 'http://127.0.0.1:17865/api/session?session=<session-id>&a=<admission-token>'
curl http://127.0.0.1:17865/asset-manifest.json
```

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
