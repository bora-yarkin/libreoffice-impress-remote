<!-- SPDX-FileCopyrightText: 2026 Bora Yarkın -->
<!-- SPDX-License-Identifier: GPL-3.0-only -->

# LibreOffice Extension

The extension is packaged as an `.oxt` archive. It should remain as self-contained as possible.

As of `0.6.19`, the extension owns Impress-only Slide Show menu and supported-toolbar integration, pairing, route selection, QR generation, transport settings, encrypted ECDH local/direct transport with a Safari-compatible authenticated local fallback, relay pairing verifiers, encrypted relay asset publishing, relay session-status probing, runtime issue reporting, local full-deck preview prewarming, bundled Python relay/Cloudflare relay/documentation export, source-only packaging, and English/Turkish localization plumbing. The phone UI is intentionally lightweight and settings-free, but now includes a phone timer and compact icon-only slideshow controls from the shared `shared/webui/` source that is vendored into the `.oxt` at build time.

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

The `.oxt` includes version-matched support bundles under `resources/`:

- `impress-remote-relay-python-<version>.zip`
- `impress-remote-relay-cloudflare-<version>.zip`
- `impress-remote-docs-<version>.zip`

Users do not need GitHub to get the matching relay server or documentation for the installed extension. Open:

```text
Slide Show -> Presentation Remote -> Advanced Remote Settings
```

Then use `Get Relay Server`, `Get Cloudflare Relay`, or `Get Documentation`. LibreOffice asks for an export folder when the platform folder picker is available and otherwise falls back to the user's Downloads folder.
