<!-- SPDX-FileCopyrightText: 2026 Bora Yarkın -->
<!-- SPDX-License-Identifier: GPL-3.0-only -->

# Security Policy

This project is a volunteer-maintained extension and should be treated as security-sensitive software under active development.

## Supported Versions

Security fixes are best-effort and target the latest tagged release or main-branch snapshot only. There are no long-term maintenance branches.

For the release target matrix and blockers, see `docs/release-readiness.md`.

## Reporting Vulnerabilities

Report vulnerabilities privately to the project maintainer. Do not disclose slide-content leaks, authentication bypasses, pairing-token bugs, or relay-message handling bugs publicly before a fix is available.

## Security Principles

- The relay server must not decrypt presentation data.
- The relay server must not store slide previews or presenter notes.
- Pairing tokens must be random and session-scoped.
- Local mode must bind only to configured interfaces.
- Relay mode must assume the server is honest-but-curious at minimum.
- Relay transport currently protects state and commands from passive or honest-but-curious relay operators, but the relay-served frontend is not yet pinned against malicious JavaScript delivery.
- Browser-hosted E2E must document the malicious-JavaScript limitation.
