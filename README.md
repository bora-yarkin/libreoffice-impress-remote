<!-- SPDX-FileCopyrightText: 2026 Bora Yarkın -->
<!-- SPDX-License-Identifier: GPL-3.0-only -->

# LibreOffice Impress Remote

LibreOffice Impress Remote is a FOSS, self-hostable remote-control system for LibreOffice Impress presentations. It is designed to work locally like a Keynote-style presenter remote while also supporting relay and direct IPv6 transports for difficult networks such as CGNAT, locked-down conference Wi-Fi, and public IPv6. In practice, the project is local-first: same-Wi-Fi and many phone hotspot setups should work without needing IPv6 or a relay.

The project is pre-1.0. Version `0.2.0` delivers a usable QR-first local/direct browser remote with full current-slide rendering, live local presenter updates, a LibreOffice-native settings dialog, LibreOffice-persisted network settings, and a prototype relay mode with a hosted phone UI and extension-side relay client. Production E2E encryption is still a blocking milestone before security-sensitive use.

See [docs/roadmap.md](docs/roadmap.md) for the staged plan toward a no-mandatory-third-party, upstream-friendly LibreOffice feature.

## Product Areas

- LibreOffice Impress `.oxt` extension
- Local browser-based phone remote
- Lightweight Python relay server
- End-to-end encrypted message protocol
- Direct IPv4, direct IPv6, and relay transports
- Presenter notes, current slide state, QR pairing, and future slide preview support

## Repository Layout

- `extension/`: LibreOffice extension metadata, Python UNO component, and phone web UI
- `server/`: lightweight Python relay server
- `docs/`: architecture, security, development, and compliance documentation
- `tests/`: repository-level tests
- `tools/`: build and validation scripts
- `.github/workflows/ci.yml`: product CI, packaging, and security checks
- `.github/workflows/github-native.yml`: Dependency Review, CodeQL, and OpenSSF Scorecard

## Quick Start

### Prerequisites

- Python 3.11+
- `uv`
- LibreOffice
- LibreOffice SDK matching the installed LibreOffice version

### Build the extension

```bash
make venv
make sdk-download
make oxt
make install-oxt
```

The package is created at:

```text
dist/libreoffice-impress-remote.oxt
```

Install it with LibreOffice Extension Manager:

```text
Tools -> Extensions -> Add
```

Or install the freshly built package directly with LibreOffice's `unopkg` wrapper:

```bash
make install-oxt
```

To resolve, download, and install the latest SDK compatible with your installed LibreOffice branch:

```bash
make sdk-download
```

### Run the relay server

```bash
make venv
make server-dev
```

Default relay endpoint:

```text
GET /            -> hosted relay phone UI
GET /health      -> relay health and session metadata
GET /ws?...      -> relay WebSocket transport
```

Prototype relay flow:

1. Run `make server-dev` on the relay host.
2. Start the LibreOffice remote locally.
3. Open the LibreOffice settings dialog, enable relay mode, and enter the relay base URL.
4. Start the remote and scan the QR code for the relay route on the phone.

## Testing the local path

After installation, use LibreOffice's menu:

```text
Slide Show -> Presentation Remote
```

- `Start Remote` starts the embedded HTTP listener.
- `Open Console` starts the listener if needed and opens the currently selected remote route in your browser.
- `Settings` opens the LibreOffice dialog for local listener enablement, local port, IPv6 direct mode, relay enablement, relay URL, route selection, and QR pairing.
- `Stop Remote` tears the local runtime down cleanly.

The default pairing route is `auto`, which prefers:

1. local network
2. direct IPv6
3. relay server

Use the route dropdown in the LibreOffice dialog when you want to force a specific path for testing.

## Modes

| Mode | Path | Use case |
| --- | --- | --- |
| Local | Phone -> laptop local IP | Same Wi-Fi, local router, Android hotspot, many personal hotspots including tested iPhone hotspot setups |
| Relay | Phone -> relay-hosted UI/WS <- LibreOffice extension | Fallback for restricted networks or when local/direct pairing fails |
| Direct IPv6 | Phone -> laptop global IPv6 | Optional fallback when local pairing fails but public IPv6 is available |

## Security Model

The relay server is intentionally dumb. It should only join clients into session rooms and forward encrypted frames. It must not parse slide notes, store previews, or know encryption keys.

Current prototype caveat:

```text
Relay mode currently forwards plaintext JSON state and command frames.
```

Treat the relay as trusted for now. Do not use it for confidential presenter notes on untrusted networks or third-party relays until E2E encryption lands.

Planned production E2E profile:

```text
ECDH P-256 + HKDF-SHA256 + AES-GCM
```

Browser-hosted E2E has a limitation: if the web UI is served by a malicious relay, that relay can serve hostile JavaScript. The documentation therefore distinguishes passive relay privacy from malicious frontend delivery.

## Development Commands

| Command | Purpose |
| --- | --- |
| `make oxt` | Build the `.oxt` extension |
| `make install-oxt` | Build and install the `.oxt` with `unopkg` |
| `make test` | Run tests |
| `make lint` | Run Ruff linting |
| `make security` | Run REUSE, Bandit, and pip-audit checks |
| `make clean` | Remove generated files |

If LibreOffice reports `premature end of file:///.../component.py`, it is usually still loading a stale cached extension version. Close LibreOffice and run `make install-oxt`, or remove the extension in Extension Manager and reinstall `dist/libreoffice-impress-remote.oxt`.

## License

GPL-3.0-only. See `LICENSE` and `REUSE.toml`.
