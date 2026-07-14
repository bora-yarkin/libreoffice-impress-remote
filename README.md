<!-- SPDX-FileCopyrightText: 2026 Bora Yarkın -->
<!-- SPDX-License-Identifier: GPL-3.0-only -->

# LibreOffice Impress Remote

LibreOffice Impress Remote is a FOSS, self-hostable remote-control system for LibreOffice Impress presentations. It is designed to work locally like a Keynote-style presenter remote while also supporting encrypted relay mode for difficult networks such as phone hotspots, CGNAT, locked-down conference Wi-Fi, and direct public IPv6.

The project is pre-1.0. The current implementation is an initial developer foundation: packageable LibreOffice extension, local browser remote, Python relay server skeleton, project documentation, compliance metadata, and CI/security automation. Production E2E encryption and final LibreOffice UNO integration are tracked as blocking milestones before security-sensitive use.

## Product Areas

- LibreOffice Impress `.oxt` extension
- Local browser-based phone remote
- Lightweight Python relay server
- End-to-end encrypted message protocol
- Direct IPv4, direct IPv6, and relay transports
- Presenter notes, current slide state, and future slide preview support

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
- LibreOffice
- LibreOffice SDK matching the installed LibreOffice version

### Build the extension

```bash
make oxt
```

The package is created at:

```text
dist/libreoffice-impress-remote.oxt
```

Install it with LibreOffice Extension Manager:

```text
Tools -> Extensions -> Add
```

### Run the relay server

```bash
cd server
python -m venv .venv
. .venv/bin/activate
pip install -e .
impress-remote-relay --host-v4 0.0.0.0 --host-v6 :: --port 8080
```

Default relay endpoint:

```text
/ws?role=phone|plugin&session=SESSION_ID
```

## Modes

| Mode | Path | Use case |
| --- | --- | --- |
| Local | Phone -> laptop local IP | Same Wi-Fi, local router, Android hotspot |
| Relay | Phone -> Python VPS <- plugin | iPhone hotspot, CGNAT, restricted networks |
| Direct IPv6 | Phone -> laptop global IPv6 | IPv4 behind CGNAT but public IPv6 available |

## Security Model

The relay server is intentionally dumb. It should only join clients into session rooms and forward encrypted frames. It must not parse slide notes, store previews, or know encryption keys.

Planned production E2E profile:

```text
ECDH P-256 + HKDF-SHA256 + AES-GCM
```

Browser-hosted E2E has a limitation: if the web UI is served by a malicious relay, that relay can serve hostile JavaScript. The documentation therefore distinguishes passive relay privacy from malicious frontend delivery.

## Development Commands

| Command | Purpose |
| --- | --- |
| `make oxt` | Build the `.oxt` extension |
| `make test` | Run tests |
| `make lint` | Run Ruff linting |
| `make security` | Run REUSE, Bandit, and pip-audit checks |
| `make clean` | Remove generated files |

## License

GPL-3.0-only. See `LICENSE` and `REUSE.toml`.
