<!-- SPDX-FileCopyrightText: 2026 Bora Yarkın -->
<!-- SPDX-License-Identifier: GPL-3.0-only -->

# LibreOffice Impress Remote

LibreOffice Impress Remote turns your phone into a lightweight presenter remote for LibreOffice Impress. Start it from Impress, scan a QR code, and control the presentation from a clean phone UI that shows the current slide, presenter notes, and simple next/previous controls.

The extension is local-first. Same-Wi-Fi and many hotspot setups should work without extra infrastructure. LocalTunnel is the default non-local fallback, while direct IPv6 and the self-hosted relay remain available for more advanced testing.

![Placeholder for the LibreOffice pairing popup](.github/assets/readme/libreoffice-pairing.png)

> QR-first pairing popup from LibreOffice Impress.

![Placeholder for the mobile remote view](.github/assets/readme/mobile-remote.jpeg)

> Phone remote with slide preview, presenter notes, and bottom-pinned controls.

![Placeholder for the remote settings dialog](.github/assets/readme/advanced-options.png)

> Remote Settings dialog for mode selection, relay configuration, help, and troubleshooting.

## What You Get

- A LibreOffice Impress extension, not a separate desktop app
- QR-first pairing from inside Impress
- A lightweight phone remote with current slide, notes, a timer, bottom next/previous controls, and compact icon-only presentation controls
- Local networking by default, with LocalTunnel, direct IPv6, and self-hosted relay modes
- LibreOffice-owned settings, troubleshooting, and route selection

## Current Status

Version `0.7.6` is a usable pre-1.0 build with:

- QR-first local pairing
- live current-slide rendering
- presenter notes on the phone
- phone-side presentation timer and compact icon-only controls for first slide, last slide, timer pause/resume, fullscreen, and jump-to-slide
- LibreOffice-native remote controls and settings
- Impress-only Slide Show menu integration plus supported toolbar buttons near the built-in slideshow controls
- encrypted direct IPv6 and relay transport, plus encrypted local transport when Web Crypto is available, for presenter state, commands, and slide assets, including relay-hosted slide previews and relay admission control
- Safari-compatible authenticated local fallback for LAN browsers that do not expose Web Crypto on plain HTTP
- one shared phone-remote web UI source reused by the LibreOffice extension, the Python relay, and the Cloudflare relay bundle
- visible phone-side connection recovery, retry/reload actions, and accessibility polish without installable PWA behavior
- local-mode full-deck preview prewarming to reduce slide export stalls during navigation
- LocalTunnel fallback for non-local testing without requiring the project-specific relay server
- one complete OXT build that embeds matching documentation, Python relay, and Cloudflare relay export bundles
- keyed user-facing strings with English and Turkish localization catalogs shared by LibreOffice and the phone UI
- dynamic localization discovery plus an import validator for adding new translation catalogs without editing phone UI code
- generated frontend asset manifests and subresource-integrity metadata for the shared web UI in OXT, relay, and Cloudflare builds
- build tooling for one complete versioned `.oxt`
- OXT-contained documentation export plus matching Python relay and Cloudflare relay exports from inside the installed extension
- relay session-status, reconnect replay, structured logs, published self-hosting docs, and a relay compatibility validator for testing implementation-independent relay deployments

Still in progress:

- GitHub release support that runs the standard workflows and, after they pass, publishes the versioned extension artifact
- broader LibreOffice UX polish and accessibility work

## How To Use It

1. Install the extension in LibreOffice.
2. Open `Slide Show -> Start Remote`.
3. Scan the QR code with your phone.
4. Use `Slide Show -> Remote Settings` when you want to change the mode or relay configuration.

The default mode is `Local network`. Remote Settings lets you choose:

1. local network
2. direct IPv6
3. relay server
4. LocalTunnel

## Why This Exists

This project is aiming for a fully FOSS, LibreOffice-friendly presenter remote that does not depend on a mandatory third-party cloud service. The long-term direction is to make the local-first experience strong enough to inform a real LibreOffice contribution.

## Technical Documentation

This README is intentionally product-focused. Technical details live in the linked docs:

- [Technical documentation index](docs/README.md)
- [User guide](docs/user-guide.md)
- [Feature matrix](docs/feature-matrix.md)
- [Troubleshooting](docs/troubleshooting.md)
- [Build and test setup](docs/development/getting-started.md)
- [Test before release](docs/test-before-release.md)
- [Architecture](docs/architecture.md)
- [LibreOffice upstream architecture](docs/libreoffice-upstream-architecture.md)
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
