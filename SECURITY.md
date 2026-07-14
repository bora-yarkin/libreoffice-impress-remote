<!-- SPDX-FileCopyrightText: 2026 Bora Yarkın -->
<!-- SPDX-License-Identifier: GPL-3.0-only -->

# Security Policy

This project is pre-1.0 and must not be used for sensitive presentations until production E2E encryption is completed, reviewed, and tested.

## Supported Versions

No stable supported version exists yet.

## Reporting Vulnerabilities

Report vulnerabilities privately to the project maintainer. Do not disclose slide-content leaks, authentication bypasses, pairing-token bugs, or relay-message handling bugs publicly before a fix is available.

## Security Principles

- The relay server must not decrypt presentation data.
- The relay server must not store slide previews or presenter notes.
- Pairing tokens must be random and session-scoped.
- Local mode must bind only to configured interfaces.
- Relay mode must assume the server is honest-but-curious at minimum.
- Browser-hosted E2E must document the malicious-JavaScript limitation.
