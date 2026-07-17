<!-- SPDX-FileCopyrightText: 2026 Bora Yarkın -->
<!-- SPDX-License-Identifier: GPL-3.0-only -->

# Contributing

Contributions must preserve the project's FOSS and LibreOffice compatibility goals.

## Requirements

- Keep the LibreOffice extension dependency-light and cross-platform.
- Avoid native Python wheels inside the `.oxt` package.
- Prefer Python stdlib inside the extension.
- Keep the relay server optional and lightweight.
- Add SPDX headers to source files.
- Keep generated artifacts out of Git unless explicitly needed.
- Do not store slide contents, presenter notes, pairing secrets, or relay payloads in logs.

## Commit Style

Use conventional commit prefixes where possible:

```text
feat:
fix:
docs:
test:
chore:
security:
```

## Local Checks

```bash
make lint
make test
make security
make oxt
```
