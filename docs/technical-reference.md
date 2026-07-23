<!-- SPDX-FileCopyrightText: 2026 Bora Yarkın -->
<!-- SPDX-License-Identifier: GPL-3.0-only -->

# Technical Reference

This is the single technical reference for LibreOffice Impress Remote. It keeps the project easier to maintain than a pile of small docs that all need updating after every UI, protocol, or packaging change.

## Contents

- [Project Shape](#project-shape)
- [Routes And Responsibilities](#routes-and-responsibilities)
- [Architecture](#architecture)
- [Protocol And Pairing](#protocol-and-pairing)
- [Security Model](#security-model)
- [Relay Server](#relay-server)
- [Localization](#localization)
- [Development Setup](#development-setup)
- [Troubleshooting](#troubleshooting)
- [Release And Maintenance Policy](#release-and-maintenance-policy)
- [Roadmap](#roadmap)

## Project Shape

LibreOffice Impress Remote is one LibreOffice extension, one shared phone UI, and optional experimental network routes.

The project is extension-first. It is not trying to become LibreOffice core right now. The goal is a small, understandable, dependency-light Impress remote that works locally without a required cloud service.

Current direction:

- Local network mode is the default, tested, and recommended path.
- Phone hotspot support matters because it solves many real same-room cases.
- Direct IPv6, Relay Server, and LocalTunnel are experimental fallbacks.
- The phone UI stays lightweight and settings-free.
- LibreOffice owns mode selection, pairing, help, settings, and the optional relay export.
- Relay and tunnel behavior must never become mandatory for local use.

This is a volunteer FOSS project. Compatibility and maintenance are best-effort, not a paid-product guarantee.

## Routes And Responsibilities

```text
Local network:
Phone browser -> laptop local IP -> LibreOffice extension

LocalTunnel:
Phone browser -> tunnel URL -> laptop local listener -> LibreOffice extension

Direct IPv6:
Phone browser -> laptop global IPv6 -> LibreOffice extension

Relay Server:
Phone browser -> relay UI/WS <- LibreOffice extension relay client
```

| Route | Status | Phone UI Source | Transport | Use When |
| --- | --- | --- | --- | --- |
| Local network | Main path | LibreOffice extension | Encrypted direct transport when Web Crypto is available; authenticated LAN fallback when needed | Phone and computer share Wi-Fi or hotspot. |
| LocalTunnel | Experimental | LibreOffice extension through tunnel | Encrypted direct transport through the tunnel | Local network access is blocked and a temporary public URL is acceptable. |
| Direct IPv6 | Experimental | LibreOffice extension | Encrypted direct transport when Web Crypto is available; authenticated plaintext fallback only when explicitly selected | Both devices have real public IPv6 and firewall rules allow it. |
| Relay Server | Experimental | Self-hosted relay | Opaque encrypted websocket frames | Local/tunnel/direct routes do not fit and the user can self-host infrastructure. |

## Architecture

Runtime components:

- LibreOffice protocol handler: registers `vnd.org.borayarkin.impressremote:*` commands and owns Start/Stop Remote plus Remote Settings dispatch.
- Impress controller adapter: reads slideshow state, presenter notes, slide indexes, titles, timer state, and end-of-deck state through UNO.
- Slide preview exporter: renders slide previews as PNG assets for the phone UI.
- Local listener: serves the phone UI shell and session-bound local/direct endpoints.
- Relay client: connects LibreOffice to an optional self-hosted relay and sends encrypted session frames.
- Shared phone UI: static HTML/CSS/JS under `shared/webui/`, reused by the OXT and Python relay bundle.
- Python relay: serves the phone UI, exposes health/session status, and forwards opaque encrypted websocket frames.

The extension owns slideshow control, notes extraction, state generation, local HTTP service, transport configuration, pairing, and relay-client behavior.

The relay owns only session matching, hosted phone UI delivery, admission-controlled session status, and opaque frame forwarding. It must not decrypt slides, notes, or commands.

## Protocol And Pairing

The encrypted protocol is intentionally small and versioned. Local network, Direct IPv6, LocalTunnel, and Relay Server use the same `hello`, `frame`, and `error` message shape when Web Crypto is available.

Pairing links normally come from QR scan or Copy URL. Local, LocalTunnel, and Direct IPv6 links carry metadata in the URL fragment:

```text
#mode=<route>&s=<session-id>&k=<pairing-verifier>
```

Relay links also include an admission token:

```text
#mode=relay&s=<session-id>&k=<pairing-verifier>&a=<admission-token>
```

Fragment fields:

- `mode`: `local`, `tunnel`, `ipv6`, or `relay`
- `s`: session identifier
- `k`: pairing verifier, mixed into key derivation and used by authenticated local fallback
- `a`: relay admission token for `/api/session` and `/ws`

The browser does not send URL fragments in HTTP requests, but JavaScript running on the loaded page can read them.

Encrypted transport setup:

1. LibreOffice generates the session id and pairing verifier.
2. LibreOffice publishes or serves a plugin `hello` with an ephemeral P-256 public key.
3. The phone sends a phone `hello` for the same session and key id.
4. Both sides derive AES-256-GCM keys using ECDH P-256 plus HKDF-SHA256.
5. State, commands, errors, and slide assets move as encrypted `frame` messages.
6. Nonces are session-bound and replay-checked.
7. Plugin send keys rotate during longer sessions.

Plaintext compatibility fallback exists only for Local network mode and explicitly selected Direct IPv6 mode when Web Crypto is not available. It uses `/api/local/*` endpoints with session and secret headers. It is authenticated, not encrypted.

## Security Model

Current cryptographic profile:

```text
ECDH P-256
HKDF-SHA256
AES-256-GCM
Versioned hello/frame/error messages
Session binding
Replay protection
Key rotation
```

Route security summary:

| Route | Confidentiality | Authentication | Main Caveat |
| --- | --- | --- | --- |
| Local network with Web Crypto | Encrypted frames for state, commands, and slide assets | ECDH plus pairing verifier and session id | Initial web shell is still served over HTTP. |
| Local Safari compatibility | Plaintext authenticated local API | Session id plus pairing verifier headers; local clients only | Same-LAN observers can see traffic. Use trusted local networks. |
| LocalTunnel | Encrypted frames through tunnel | ECDH plus pairing verifier and session id | Tunnel provider is frontend-delivery infrastructure. |
| Direct IPv6 with Web Crypto | Encrypted frames over public IPv6 | ECDH plus pairing verifier and session id | Firewall/public exposure must be handled carefully. |
| Direct IPv6 compatibility | Plaintext authenticated API | Session id plus pairing verifier headers | Public-path observers can see traffic. Experimental only. |
| Relay Server | End-to-end encrypted frames through relay | ECDH plus pairing verifier and admission token | Relay-served JavaScript still has to be trusted or verified. |

Important limitation: browser-hosted E2E cannot protect against a server or network attacker that replaces the first HTML/JavaScript page. The current baseline protects against passive observers and honest-but-curious relays, not malicious frontend delivery.

Current frontend trust baseline:

- OXT, local server, and Python relay generate asset manifests.
- Packaged pages pin shared CSS/JS with SRI where applicable.
- Self-hosted relay users should export the matching relay bundle from the installed OXT.
- LocalTunnel and Relay Server URLs should be treated as secret presentation links.

Never log slide notes, slide images, pairing secrets, admission tokens, or encrypted payload contents.

## Relay Server

Relay Server mode is experimental. It exists for networks where local mode does not fit and the user is comfortable self-hosting.

A compatible relay serves:

- `/`
- `/app.js`
- `/app.css`
- `/asset-manifest.json`
- `/localizations/manifest.json`
- `/localizations/<locale>.json`
- `/health`
- `/api/session?session=<id>&a=<admission-token>`
- `/ws?role=plugin|phone&session=<id>&a=<admission-token>`

The relay forwards `hello`, `frame`, and `error` envelopes. `frame` payloads stay encrypted end to end.

From source:

```bash
make relay-dev
```

From an exported relay bundle:

```bash
./configure.sh
```

On Windows:

```powershell
.\configure.ps1
```

The exported relay bundle root contains only `configure.sh` and `configure.ps1`. Runtime files live under `relay-runtime/`. The configure script asks whether to run once, install as a service, or uninstall the service. Leave the port empty to use the random/default port behavior.

Reverse proxy checklist:

- Terminate TLS at the proxy, or use plain HTTP only on trusted internal networks.
- Forward websocket upgrades on `/ws`.
- Preserve query parameters on `/ws` and `/api/session`.
- Keep `/asset-manifest.json` reachable.
- Keep the saved LibreOffice relay URL aligned with the public base URL.

Compatibility check:

```bash
make relay-compat RELAY_URL=https://relay.example.com
```

## Localization

Runtime strings live in keyed JSON catalogs under `shared/localizations/`. English is the source catalog and Turkish is the first shipped translation.

Import a translation:

```bash
make localization-import ARGS="path/to/de-DE.json"
```

The importer rejects unknown keys and placeholder mismatches. Use incomplete catalogs only when intentionally relying on English fallback:

```bash
make localization-import ARGS="--allow-incomplete path/to/de-DE.json"
```

The phone UI discovers shipped locales through `/localizations/manifest.json`.

## Development Setup

Common setup:

```bash
git clone https://github.com/bora-yarkin/libreoffice-impress-remote.git
cd libreoffice-impress-remote
make venv
make test
make oxt
make install-oxt
```

Useful commands:

- `make refresh`: remove generated files, `.venv`, and project uv cache, then recreate the environment.
- `make clean`: clean build artifacts and local development cache.
- `make lint`: run lint checks.
- `make test`: run the test suite.
- `make oxt`: build `dist/libreoffice-impress-remote-<version>.oxt`.
- `make relay-dev`: run the Python relay from the source tree.
- `make relay-compat RELAY_URL=...`: validate a relay HTTP contract.

Close LibreOffice before `make install-oxt`; LibreOffice can keep old extension code loaded while any process is still running.

During normal development, do not bump `VERSION` for every code change. Record work under `CHANGELOG.md` `Unreleased` and update `VERSION` only when preparing or publishing a release.

## Troubleshooting

Rebuild and reinstall cleanly:

```bash
make oxt
make install-oxt
```

Quit LibreOffice completely before reinstalling.

Common install/runtime failures:

- `premature end of file ... component.py`: LibreOffice cached or unpacked a broken OXT. Quit LibreOffice, remove the extension if visible, rebuild, and reinstall.
- `No module named 'impress_remote'`: OXT package layout is wrong or stale. Rebuild the versioned OXT and inspect the archive.
- `No module named 'com'`: a UNO module was imported outside LibreOffice runtime or too early during registration.
- `NameError` during registration: a runtime-only class leaked into a top-level annotation/import path.
- Menu missing: open an actual Impress presentation; commands are Impress-only under `Slide Show`.
- QR or Copy URL missing: use `Slide Show -> Start Remote`; Remote Settings is settings-only.
- Safari Web Crypto unavailable: Local network mode can use authenticated LAN fallback. LocalTunnel and Relay Server still require Web Crypto.
- Relay says connected on phone but LibreOffice cannot connect: check `/health`, websocket proxying on `/ws`, query preservation, TLS, and the exact relay URL saved in Remote Settings.

Diagnostic popup errors in LibreOffice should be copied in full when reporting issues.

## Release And Maintenance Policy

`1.0.0` is the first local-mode release. Local mode has been tested by the maintainer and works in the current development environment. That does not mean every LibreOffice version, OS, router, phone browser, or corporate network is covered.

Release posture:

- Local network mode is the release gate.
- Direct IPv6, Relay Server, and LocalTunnel are experimental and should not block the main local release.
- Security fixes are best-effort for the latest tagged release or main-branch snapshot only.
- There are no long-term support branches.
- Compatibility evidence means “tested there,” not “supported forever.”

Before a release, at minimum:

- run `make clean`, `make venv`, `make lint`, `make test`, and `make oxt`
- install the generated OXT in LibreOffice Impress
- verify Start/Stop Remote and Remote Settings
- test local same-Wi-Fi or hotspot pairing with a real phone
- verify slide image, presenter notes, effect-aware navigation, timers, and Copy URL
- update `CHANGELOG.md`

## Roadmap

Open work lives in [TODO](../TODO.md). The short version:

- broaden local-mode evidence across OSes, LibreOffice versions, and phone browsers
- add browser-level E2E tests for the phone UI
- verify accessibility across desktop and phone flows
- harden experimental LocalTunnel, Direct IPv6, and Relay Server behavior with real deployments
- expand localization after source strings settle
- improve frontend trust beyond plain HTTP web-shell delivery
- keep the project simple enough for volunteer maintenance
