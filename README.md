<!-- SPDX-FileCopyrightText: 2026 Bora Yarkın -->
<!-- SPDX-License-Identifier: GPL-3.0-only -->

# LibreOffice Impress Remote

LibreOffice Impress Remote turns your phone into a lightweight presenter remote for LibreOffice Impress. Start it from Impress, scan a QR code, and control the presentation from a clean phone UI that shows the current slide, presenter notes, and simple next/previous controls.

The extension is local-first. Same-Wi-Fi and many hotspot setups should work without extra infrastructure. Direct IPv6 and a self-hosted relay exist as fallback routes for harder networks.

![Placeholder for the LibreOffice pairing popup](.github/assets/readme/libreoffice-pairing.png)

> QR-first pairing popup from LibreOffice Impress.

![Placeholder for the mobile remote view](.github/assets/readme/mobile-remote.jpeg)

> Phone remote with slide preview, presenter notes, and bottom-pinned controls.

![Placeholder for the advanced options dialog](.github/assets/readme/advanced-options.png)

> Advanced options dialog for route selection, relay configuration, and troubleshooting.

## What You Get

- A LibreOffice Impress extension, not a separate desktop app
- QR-first pairing from inside Impress
- A lightweight phone remote with current slide, notes, and next/previous controls
- Local networking by default, with direct IPv6 and self-hosted relay fallbacks
- LibreOffice-owned settings, troubleshooting, and route selection

## Current Status

Version `0.3.3` is a usable pre-1.0 build with:

- QR-first local pairing
- live current-slide rendering
- presenter notes on the phone
- LibreOffice-native remote controls and settings
- encrypted relay and direct IPv6 transport for fallback networking

Still in progress:

- ECDH-based key exchange
- encrypted transport parity for local mode
- phone-side presentation timer
- converting all user-facing strings to stable keys, then adding importable i18n support so translations can be generated for LibreOffice-supported languages and loaded back into the extension
- GitHub release support that runs the standard workflows and, after they pass, publishes a GitHub release with the extension package and a stripped relay-server release artifact without bundled documentation
- broader LibreOffice UX polish and accessibility work

## How To Use It

1. Install the extension in LibreOffice.
2. Open `Slide Show -> Presentation Remote`.
3. Start the remote and scan the QR code with your phone.
4. Control the presentation from the phone while keeping setup inside LibreOffice.

The default route is `Auto`, which tries:

1. local network
2. direct IPv6
3. relay server

## Why This Exists

This project is aiming for a fully FOSS, LibreOffice-friendly presenter remote that does not depend on a mandatory third-party cloud service. The long-term direction is to make the local-first experience strong enough to inform a real LibreOffice contribution.

## Technical Documentation

This README is intentionally product-focused. Technical details live in the linked docs:

- [Technical documentation index](docs/README.md)
- [Build and test setup](docs/development/getting-started.md)
- [Architecture](docs/architecture.md)
- [Protocol](docs/protocol.md)
- [Relay server](docs/relay-server.md)
- [Security model](docs/security/e2ee.md)
- [Roadmap](docs/roadmap.md)

## Contributing And Project Policy

- [Contributing](.github/CONTRIBUTING.md)
- [Security policy](.github/SECURITY.md)
- [Code of conduct](.github/CODE_OF_CONDUCT.md)
- [Governance](.github/GOVERNANCE.md)

## License

GPL-3.0-only. See `LICENSE` and `REUSE.toml`.
