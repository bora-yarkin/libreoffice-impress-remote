<!-- SPDX-FileCopyrightText: 2026 Bora Yarkın -->
<!-- SPDX-License-Identifier: GPL-3.0-only -->

# LibreOffice Extension

The extension is packaged as an `.oxt` archive. It should remain as self-contained as possible.

As of `0.5.0`, the extension owns pairing, route selection, QR generation, transport settings, relay pairing secrets, encrypted relay asset publishing, relay session-status probing, and runtime issue reporting. The phone UI is intentionally lightweight and settings-free, but now comes from the shared `shared/webui/` source during development and is vendored into the `.oxt` at build time.

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
