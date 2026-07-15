<!-- SPDX-FileCopyrightText: 2026 Bora Yarkın -->
<!-- SPDX-License-Identifier: GPL-3.0-only -->

# LibreOffice Extension

The extension is packaged as an `.oxt` archive. It should remain as self-contained as possible.

As of `0.2.0`, the extension owns pairing, route selection, QR generation, and transport settings. The phone UI is intentionally lightweight and settings-free.

## Rules

- Prefer Python stdlib inside the extension.
- Avoid compiled native dependencies.
- Avoid installing pip packages into LibreOffice's bundled Python.
- Use UNO APIs for Impress control.
- Keep the phone UI as static HTML, CSS, and JavaScript.
- Keep transport configuration and pairing decisions inside LibreOffice UI rather than the phone UI.

## Build

```bash
python tools/build_oxt.py
```

## Install

```text
LibreOffice -> Tools -> Extensions -> Add
```
