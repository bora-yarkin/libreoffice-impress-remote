<!-- SPDX-FileCopyrightText: 2026 Bora Yarkın -->
<!-- SPDX-License-Identifier: GPL-3.0-only -->

# Feature Matrix

This matrix reflects the `0.7.7` snapshot.

## User Workflow

| Feature | Status | Notes |
| --- | --- | --- |
| Installable OXT | Implemented | `make oxt` builds `dist/libreoffice-impress-remote-<version>.oxt`. |
| Impress-only start/stop | Implemented | `Slide Show -> Start Remote` toggles to Stop Remote while running. |
| Remote Settings | Implemented | Contains only mode selection, relay URL when Relay mode is selected, relay/documentation export buttons, Help, Save, and Close. |
| QR-first pairing | Implemented | Start Remote opens the QR popup. Copy URL is in that popup as the manual fallback. |
| Local network mode | Tested locally | Default and recommended route for same Wi-Fi and hotspot setups; this is the main `1.0.0` gate. |
| LocalTunnel mode | Experimental | Optional public tunnel fallback using the vendored pure-Python LocalTunnel-compatible client. |
| Direct IPv6 mode | Experimental | Advertises only globally reachable IPv6 addresses after listener self-test, but needs more real-network proof. |
| Relay Server mode | Experimental | Optional self-hosted Python or Cloudflare relay. Relay export buttons appear only in Relay Server mode. |
| In-product help | Implemented | Help explains modes, pairing, and error reporting from LibreOffice. |
| GitHub release publication | Planned | CI builds the OXT, but release creation is not automated yet. |

## Phone Remote

| Feature | Status | Notes |
| --- | --- | --- |
| Current slide image | Implemented | Served as a rendered PNG asset. |
| Presenter notes | Implemented | Notes are the only scrollable phone region. |
| Previous/next controls | Implemented | Buttons are pinned to the bottom; tapping the slide advances. |
| Timers | Implemented | The phone shows total presentation time and current-slide time while a slideshow is running. |
| Overflow controls | Implemented | First slide, last slide, timer pause/resume, and go-to-slide. |
| Fullscreen slide mode | Implemented | Requests fullscreen and landscape orientation when the browser supports it. |
| Settings-free UI | Implemented | No route selection, relay configuration, IP lists, or troubleshooting settings on the phone. |
| Plain browser page | Implemented | The QR opens a normal browser page with no app-install step. |
| Low-latency local previews | Implemented | Local mode prewarms a bounded server-side PNG cache and the phone preloads the next slide. |
| Browser E2E automation | Planned | Real browser automation is still needed. |

## Transport And Security

| Feature | Status | Notes |
| --- | --- | --- |
| ECDH P-256 bootstrap | Implemented | Local/direct/tunnel/relay encrypted modes derive keys from ECDH plus the QR pairing verifier. |
| Encrypted state/commands/assets | Implemented | Web-Crypto-capable local, LocalTunnel, direct IPv6, and relay modes use AES-256-GCM frames. |
| Safari local fallback | Implemented | Local mode can fall back to authenticated plaintext `/api/local/*` on trusted LANs when Web Crypto is unavailable. |
| Relay admission token | Implemented | Relay phone links include an admission token for `/api/session` and `/ws`. |
| Replay checks and key rotation | Implemented | Encrypted frames are session-bound, nonce replay is rejected, and plugin send keys rotate. |
| Asset manifests and SRI | Implemented | Shared web assets expose SHA-256/SRI metadata in OXT, Python relay, Cloudflare relay, and local server builds. |
| Local HTTPS or trusted phone shell | Planned | Needed to resist active local script replacement. |

## Packaging, Relay, And QA

| Feature | Status | Notes |
| --- | --- | --- |
| Single complete OXT | Implemented | One versioned package embeds local mode, experimental modes, docs, and relay export bundles. |
| Python relay bundle | Experimental | Includes the shared phone UI and Linux/Windows service helpers. |
| Cloudflare relay bundle | Experimental | Includes the Worker, Durable Object binding config, and shared phone UI assets. |
| Relay compatibility validator | Implemented | `make relay-compat RELAY_URL=...` checks the public HTTP contract. |
| Localization import | Implemented | `make localization-import` validates keyed JSON catalogs; English and Turkish ship today. |
| Grouped test suite | Implemented | Tests are grouped under `tests/extension`, `tests/shared`, `tests/relay`, and `tests/tools`. |
| Manual release checklist | Implemented | [Test Before Release](test-before-release.md) covers the routes and UI flows that still need real-device verification. |
| LibreOffice runtime matrix | Planned | More macOS, Windows, Linux, LibreOffice-version, and phone-browser results are needed. |
