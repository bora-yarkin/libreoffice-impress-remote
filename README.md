<!-- SPDX-FileCopyrightText: 2026 Bora Yarkın -->
<!-- SPDX-License-Identifier: GPL-3.0-only -->

# LibreOffice Impress Remote

LibreOffice Impress Remote turns a phone browser into a simple presenter remote for LibreOffice Impress.

Open a presentation, start the remote from the `Slide Show` menu, scan the QR code, and use your phone to see the current slide, read presenter notes, and move through the slideshow. There is no separate phone app to install and no required cloud account for the normal local workflow.

## What It Does

- Shows the current slide on your phone.
- Shows presenter notes below the slide.
- Provides large previous and next controls that handle slide effects before changing slides.
- Supports tap-to-advance on the slide preview.
- Includes presentation and per-slide timers.
- Offers fullscreen slide mode for a cleaner landscape phone view.
- Keeps settings in LibreOffice, not on the phone remote.
- Works locally by default over same Wi-Fi or many phone hotspot setups.

## Local First

The main experience is intentionally local:

1. Open an Impress presentation.
2. Choose `Slide Show -> Start Remote`.
3. Scan the QR code with your phone.
4. Present.

If QR scanning is awkward, the QR popup also has a Copy URL button.

Local mode is the recommended path because it is the simplest one: the computer running LibreOffice serves the phone page directly, and the phone controls the presentation over the local network.

## Connection Modes

Most people should use `Local network`.

| Mode | Purpose |
| --- | --- |
| Local network | Same Wi-Fi or phone hotspot. This is the normal path. |
| Direct IPv6 | Experimental fallback for networks with reachable public IPv6. |
| Relay Server | Experimental self-hosted relay path for difficult networks. |
| LocalTunnel | Experimental temporary public tunnel path. |

Use `Slide Show -> Remote Settings` only when you need to change the connection mode or configure the relay server.

## Built For Impress

The extension integrates into LibreOffice Impress instead of acting like a separate desktop app. The remote controls live under the `Slide Show` menu, and the phone page stays focused on presentation control rather than configuration.

The phone UI is deliberately small:

- slide at the top
- notes in the scrollable area
- previous and next pinned at the bottom
- optional drawer for first slide, last slide, timer pause/resume, and go-to-slide

## Privacy And Networking

Local mode does not require a third-party server. Experimental relay and tunnel modes exist for harder network setups, but they are optional.

When the browser supports Web Crypto, remote traffic uses an encrypted session protocol. Some local browser contexts, especially Safari on plain local HTTP, may use an authenticated local fallback for compatibility. The technical details and limitations are documented honestly in the technical reference.

## Documentation

- [User guide](docs/user-guide.md)
- [Technical reference](docs/technical-reference.md)

## Project Notes

This is a volunteer FOSS extension. The goal is to make a useful, understandable Impress remote without requiring a mandatory cloud service or a separate mobile app. Experimental modes and future platform adapters may improve over time if people want to help, but the local Impress workflow is the heart of the project.

## Contributing And Project Policy

- [Contributing](.github/CONTRIBUTING.md)
- [Security policy](.github/SECURITY.md)
- [Code of conduct](.github/CODE_OF_CONDUCT.md)
- [Governance](.github/GOVERNANCE.md)

## License

GPL-3.0-only. See `LICENSE` and `REUSE.toml`.
