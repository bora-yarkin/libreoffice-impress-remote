<!-- SPDX-FileCopyrightText: 2026 Bora Yarkın -->
<!-- SPDX-License-Identifier: GPL-3.0-only -->

# Getting Started

This guide matches the `1.0.3` release line.

```bash
git clone https://github.com/bora-yarkin/libreoffice-impress-remote.git
cd libreoffice-impress-remote
make venv
make refresh
make sdk-download
make test
make oxt
make install-oxt
make localization-import ARGS="path/to/de-DE.json"
make relay-compat RELAY_URL=https://relay.example.com
```

On macOS, `make sdk-download` downloads the matching LibreOffice SDK disk image from the official archive and installs its SDK directory into `third_party/libreoffice-sdk/`.

Use `make refresh` when the local environment feels stale. It runs the full generated-file cleanup, removes `.venv` and the project uv cache, then recreates the uv-managed environment.

Close LibreOffice before running `make install-oxt` so `unopkg` can replace the existing extension cleanly.

## Testing the local remote

After `make install-oxt`, open LibreOffice Impress and use:

```text
Slide Show -> Start Remote
Slide Show -> Remote Settings
```

1. Open `Remote Settings` if you want to choose Local network, LocalTunnel, Direct IPv6, or Relay Server.
2. Keep the mode on `Local network` for normal same-Wi-Fi and hotspot testing. LocalTunnel, Direct IPv6, and Relay Server are experimental.
3. Save any settings changes, then use `Start Remote` to bring up the embedded local server and QR pairing dialog.
4. Scan the QR code shown by LibreOffice with your phone.
5. Use `Copy URL` in the QR popup if you also want to open the current route in a desktop browser.

## Testing Localization

The extension ships English and Turkish catalogs in `shared/localizations/`.

- Set `IMPRESS_REMOTE_LANG=tr` before launching LibreOffice to force Turkish extension strings during development.
- Add `?lang=tr` to the phone UI URL, or `lang=tr` in the pairing fragment, to force Turkish browser strings.
- Omit the override to let the extension and browser fall back to their detected language, then English.

## Relay Mode

```bash
make server-dev
```

Then:

1. Open `Remote Settings` from the Slide Show menu.
2. Select `Relay Server`, enter the relay base URL, and save.
3. Use `Start Remote` from the Slide Show menu.
4. Scan the QR code on the phone, or open the full pairing link with its `#...` fragment intact if you are testing the hosted relay page manually.
5. When the phone joins successfully, LibreOffice should detect the relay session and start the slideshow automatically.

The relay host now serves:

- `/` for the phone UI
- `/ws` for the relay websocket transport
- `/api/session` for admission-controlled session status
- `/health` for runtime and limit checks
- `/asset-manifest.json` for bundle verification

## Extension Packages

- `make oxt` builds the versioned complete extension package, for example `dist/libreoffice-impress-remote-1.0.3.oxt`, with local, LocalTunnel, direct IPv6, relay mode, documentation export, Python relay export, and Cloudflare relay export included.
- The installed `.oxt` embeds the matching documentation, stripped Python relay bundle, and Cloudflare relay bundle so users can export matching resources from Remote Settings without visiting GitHub.

Useful relay checks:

```bash
curl http://127.0.0.1:17865/health
curl 'http://127.0.0.1:17865/api/session?session=<session-id>&a=<admission-token>'
curl http://127.0.0.1:17865/asset-manifest.json
```

## Troubleshooting

For the full install and runtime guide, see [Troubleshooting](../troubleshooting.md).

If LibreOffice reports:

```text
premature end of file:///.../python/impress_remote/component.py
```

check the installed cache version under `~/Library/Application Support/LibreOffice/4/user/uno_packages/cache/uno_packages/`. If that cache still contains an older `description.xml` version than the current `dist/libreoffice-impress-remote-<version>.oxt`, LibreOffice is loading a stale package. Rebuild and reinstall with:

```bash
make oxt
make install-oxt
```

If the stale cache persists, remove the extension from LibreOffice Extension Manager, quit LibreOffice, then install the freshly built `dist/libreoffice-impress-remote-<version>.oxt` again.
