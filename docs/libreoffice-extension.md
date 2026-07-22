<!-- SPDX-FileCopyrightText: 2026 Bora Yarkın -->
<!-- SPDX-License-Identifier: GPL-3.0-only -->

# LibreOffice Extension

The extension is packaged as an `.oxt` archive. It should remain as self-contained as possible.

As of `0.7.6`, the extension owns Impress-only Slide Show menu and supported-toolbar integration, pairing, explicit mode selection, QR generation, encrypted ECDH local/direct/tunnel transport with a Safari-compatible authenticated local fallback, vendored LocalTunnel-compatible fallback, relay pairing verifiers, encrypted relay asset publishing, relay session-status probing, copyable diagnostic error reporting, local full-deck preview prewarming, bundled documentation/relay export, dynamic localization catalogs, polished install metadata, and shared frontend asset manifests. The phone UI is intentionally lightweight and settings-free, but now includes presentation and slide timers, compact icon-only slideshow controls, and a fullscreen slide mode from the shared `shared/webui/` source that is vendored into the `.oxt` at build time.

## Rules

- Prefer Python stdlib inside the extension.
- Avoid compiled native dependencies.
- Avoid installing pip packages into LibreOffice's bundled Python.
- Use UNO APIs for Impress control.
- Keep the phone UI as static HTML, CSS, and JavaScript.
- Keep transport configuration and pairing decisions inside LibreOffice UI rather than the phone UI.
- Persist user-facing transport settings in LibreOffice configuration storage whenever the UNO runtime is available.

## Build

```bash
make oxt
```

## Install

```text
LibreOffice -> Tools -> Extensions -> Add
```

## Bundled Resources

The `.oxt` includes version-matched resource bundles under `resources/`:

- `impress-remote-docs-<version>.zip`
- `impress-remote-relay-python-<version>.zip`
- `impress-remote-relay-cloudflare-<version>.zip`

Users do not need GitHub to get the matching documentation or relay server for the installed extension. Open:

```text
Slide Show -> Remote Settings
```

Then select Relay Server mode and use `Get Documentation`, `Get Relay Server`, or `Get Cloudflare Relay`. LibreOffice asks for an export folder when the platform folder picker is available and otherwise falls back to the user's Downloads folder.
