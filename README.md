<!-- SPDX-FileCopyrightText: 2026 Bora Yarkın -->
<!-- SPDX-License-Identifier: GPL-3.0-only -->

# LibreOffice Impress Remote

LibreOffice Impress Remote turns your phone into a lightweight presenter remote for LibreOffice Impress. Start it from Impress, scan a QR code, and control the presentation from a clean phone UI that shows the current slide, presenter notes, and simple next/previous controls.

The extension is local-first. Same-Wi-Fi and many hotspot setups work without extra infrastructure. LocalTunnel, direct IPv6, and self-hosted relay modes are included for experimentation on harder networks, but they are not the primary experience.

## What You Get

- A LibreOffice Impress extension, not a separate desktop app
- QR-first pairing from inside Impress
- A lightweight phone remote with current slide, notes, timers, bottom next/previous controls, and compact icon-only presentation controls
- Local networking by default, with LocalTunnel, direct IPv6, and self-hosted relay modes
- LibreOffice-owned mode selection, relay configuration, and help

## Current Status

Version `1.0.0` is the current first stable local-mode release. Local mode has been tested by the maintainer and works for real Impress control in the current development environment.

- Impress-only `Slide Show -> Start Remote` and `Slide Show -> Remote Settings`
- QR-first pairing with Copy URL fallback in the QR popup
- phone UI with slide image, notes, effect-aware previous/next, tap-to-advance, timers, fullscreen, first/last slide, and go-to-slide
- Local network mode by default, plus optional LocalTunnel, Direct IPv6, and Relay Server modes
- encrypted local/direct/tunnel/relay transport when Web Crypto is available
- Safari-compatible authenticated HTTP fallback for local mode and experimental direct IPv6 testing
- one versioned OXT that embeds matching documentation and the Python relay bundle
- English and Turkish localization catalogs plus an import workflow for more languages
- GitHub release automation for publishing the versioned OXT after build, lint, and tests pass

Experimental or still in progress:

- broader LibreOffice, OS, browser, accessibility, LocalTunnel, IPv6, and relay compatibility evidence
- long-term maintenance cadence, which depends on volunteer time

## How To Use It

1. Install the extension in LibreOffice.
2. Open `Slide Show -> Start Remote`.
3. Scan the QR code with your phone.
4. Use `Copy URL` in the QR popup only if scanning fails.
5. Use `Slide Show -> Remote Settings` when you want to change the mode or relay configuration.

The default mode is `Local network`. Remote Settings lets you choose:

1. local network
2. direct IPv6
3. relay server
4. LocalTunnel

## Why This Exists

This is a volunteer FOSS extension for LibreOffice Impress. The goal is to make the common local presenter-remote flow useful, understandable, and dependency-light without requiring a mandatory cloud service. Experimental routes may grow over time, and other office-suite adapters may happen someday, but none of that is promised.

## Technical Documentation

This README is intentionally product-focused. Technical details live in the linked docs:

- [Technical documentation index](docs/README.md)
- [User guide](docs/user-guide.md)
- [Feature matrix](docs/feature-matrix.md)
- [Troubleshooting](docs/troubleshooting.md)
- [Build and test setup](docs/development/getting-started.md)
- [Test before release](docs/test-before-release.md)
- [Architecture](docs/architecture.md)
- [Localization](docs/localization.md)
- [Protocol](docs/protocol.md)
- [Relay and deployment](docs/relay.md)
- [Release readiness](docs/release-readiness.md)
- [Security model](docs/security/e2ee.md)
- [Roadmap](docs/roadmap.md)

## Contributing And Project Policy

- [Contributing](.github/CONTRIBUTING.md)
- [Security policy](.github/SECURITY.md)
- [Code of conduct](.github/CODE_OF_CONDUCT.md)
- [Governance](.github/GOVERNANCE.md)

## License

GPL-3.0-only. See `LICENSE` and `REUSE.toml`.
