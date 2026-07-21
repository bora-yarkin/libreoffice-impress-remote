<!-- SPDX-FileCopyrightText: 2026 Bora Yarkın -->
<!-- SPDX-License-Identifier: GPL-3.0-only -->

# Getting Started

This guide matches the `0.6.16` release line.

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

1. Open `Advanced Remote Settings` if you want to review the route, set a relay URL, or disable local mode for route-specific testing.
2. Keep the route on `Auto (Local -> IPv6 -> Relay)` unless you are forcing a specific path, and disable `Enable local` only when you want a relay-only or direct-IPv6-only test.
3. Save any settings changes, then use `Start Remote` from the same `Presentation Remote` submenu to bring up the embedded local server and QR pairing dialog.
4. Scan the QR code shown by LibreOffice with your phone.
5. Use the Manual Link shown in `Advanced Remote Settings` if you also want to open the current route in a desktop browser.

## Testing Localization

The extension ships English and Turkish catalogs in `localizations/`.

- Set `IMPRESS_REMOTE_LANG=tr` before launching LibreOffice to force Turkish extension strings during development.
- Add `?lang=tr` to the phone UI URL, or `lang=tr` in the pairing fragment, to force Turkish browser strings.
- Omit the override to let the extension and browser fall back to their detected language, then English.

## Relay Mode

```bash
make server-dev
```

Then:

1. Open `Advanced Remote Settings` from the extension menu.
2. Enable relay mode, enter the relay base URL, and save.
3. Use `Start Remote` from the same `Presentation Remote` submenu.
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
- `make oxt` builds only the versioned extension package, for example `dist/libreoffice-impress-remote-0.6.16.oxt`.
- `make release-full` builds the versioned OXT plus both standalone relay bundle variants in one command.
- The `.oxt` itself embeds the matching stripped Python relay bundle, Cloudflare relay bundle, and documentation bundle so users can export them from Advanced Remote Settings without visiting GitHub.

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
