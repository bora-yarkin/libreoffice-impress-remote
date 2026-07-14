<!-- SPDX-FileCopyrightText: 2026 Bora Yarkın -->
<!-- SPDX-License-Identifier: GPL-3.0-only -->

# FOSS and LibreOffice Compliance

## Licensing

- Use GPL-3.0-only unless the maintainer explicitly changes the license.
- Keep SPDX identifiers in source files.
- Keep REUSE metadata valid.
- Do not add incompatible dependencies.

## LibreOffice Extension Standards

- Package as `.oxt`.
- Keep extension metadata in `description.xml` and `META-INF/manifest.xml`.
- Use UNO APIs rather than platform-specific automation.
- Avoid OS-specific paths.
- Keep macOS, Windows, and Linux support in design decisions.

## Security Requirements

- Never log slide notes or slide images.
- Never persist relay payloads.
- Treat relay servers as untrusted.
- Expire pairing sessions.
