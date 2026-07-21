<!-- SPDX-FileCopyrightText: 2026 Bora Yarkın -->
<!-- SPDX-License-Identifier: GPL-3.0-only -->

# Feature Matrix

This matrix reflects the `0.6.19` snapshot. It is deliberately user-facing: it separates what can be tested today from what is planned, so the README can stay short without hiding project status.

## User Workflow

| Feature | Status | Notes |
| --- | --- | --- |
| Install as a LibreOffice `.oxt` extension | Implemented | Built with `make oxt`; output is versioned as `dist/libreoffice-impress-remote-<version>.oxt`. |
| Source-only OXT package | Implemented | Built with `make source-oxt`; output is versioned as `dist/libreoffice-impress-remote-<version>-source.oxt` and omits embedded relay/docs resource bundles. |
| Start/stop remote from Impress | Implemented | Available from `Slide Show -> Presentation Remote -> Start Remote`; the menu item toggles to Stop Remote while running. |
| QR-first pairing | Implemented | Start Remote opens a QR-only pairing popup; manual link is available from Advanced Remote Settings as a backup. |
| Auto route selection | Implemented | Auto tries local first, then direct IPv6, then relay when configured. |
| Same-Wi-Fi and hotspot local mode | Implemented | This is the recommended path and works for many normal Wi-Fi and phone-hotspot setups. |
| In-product step-by-step help | Implemented | Start Remote and Advanced Remote Settings explain same-Wi-Fi, phone-hotspot, manual-link, IPv6, and relay fallback usage. |
| GitHub release publication | Planned | CI exists, but release creation and release artifact publishing are not automated yet. |
| Release-readiness policy | Implemented | Route gates, target compatibility, and preview blockers are documented in [Release Readiness](release-readiness.md). |

## Phone Remote

| Feature | Status | Notes |
| --- | --- | --- |
| Current slide image | Implemented | The extension exports the current Impress slide as PNG for the phone UI. |
| Presenter notes | Implemented | Notes are shown below the slide in the only scrollable area on the phone. |
| Previous and next controls | Implemented | Buttons are pinned to the bottom; tapping the slide also advances. |
| Settings-free phone UI | Implemented | Route, relay, and troubleshooting settings stay in LibreOffice. |
| Connection recovery panel | Implemented | The phone UI shows reconnect/offline feedback with retry and reload actions. |
| PWA shell metadata | Implemented | Manifest, icon, and service worker shell are included. |
| Presentation timer on phone | Implemented | The timer is shown over the slide while a slideshow is running. |
| Richer mobile controls | Implemented | A compact icon-only drawer exposes start/end, effect-step, blank/resume, last-slide, and jump-to-slide actions without adding settings to the phone UI. |
| Low-latency full-deck preload | Implemented | Local mode prewarms a bounded server-side PNG cache for the full deck when the remote starts, and the phone still preloads the next slide image. |

## LibreOffice UX

| Feature | Status | Notes |
| --- | --- | --- |
| Impress-only menu integration | Implemented | Presentation Remote is merged into Impress Slide Show UI rather than Writer or Calc. |
| Toolbar/notebookbar buttons | Implemented | Supported toolbar modes get Start/Stop Remote and Advanced Remote Settings near slideshow controls. |
| Advanced Remote Settings | Implemented | Owns route selection, relay URL, local port, runtime status, manual link, resource export, and issues. |
| Bundled resource export | Implemented | Users can export the matching Python relay, Cloudflare relay, or documentation bundle from the installed extension. |
| Broad platform UX verification | Planned | More compatibility evidence is needed across supported LibreOffice versions and desktop platforms. |
| LibreOffice-core proof of concept | Planned | The extension is a prototype path; a core patch would need a smaller native implementation. |

## Transport And Security

| Feature | Status | Notes |
| --- | --- | --- |
| Encrypted relay transport | Implemented | Relay forwards opaque encrypted frames and does not decrypt notes, commands, or slide assets. |
| Encrypted direct IPv6 transport | Implemented | Direct IPv6 uses the same `hello`/`frame` contract as relay mode. |
| Encrypted local transport when Web Crypto is available | Implemented | Modern browsers use session-bound `/api/direct/*` encrypted state, command, event, and slide-asset endpoints. |
| Safari local compatibility fallback | Implemented | Local mode can use LAN-only authenticated plaintext `/api/local/*` polling when Safari does not expose Web Crypto on LAN HTTP origins. |
| Relay admission token | Implemented | Relay phone links include an admission token required for `/api/session` and `/ws`. |
| Replay checks and key rotation | Implemented | Encrypted frames are session-bound and nonce replay is rejected. |
| ECDH P-256 bootstrap | Implemented | Encrypted local/direct and relay modes derive transport keys from ephemeral P-256 ECDH plus the QR pairing verifier. |
| Local HTTPS or frontend pinning | Planned | Current local web shell is served over HTTP; encrypted frames reduce passive-observer exposure but do not stop active script replacement. |

## Relay And Deployment

| Feature | Status | Notes |
| --- | --- | --- |
| Python relay server | Implemented | Self-hostable on a VPS or local machine. |
| Python relay service helpers | Implemented | Linux and Windows service install/uninstall helpers exist in the release bundle. |
| Cloudflare Worker relay bundle | Implemented | Separate Worker plus Durable Object bundle is produced by `make cloudflare-bundle`. |
| Shared phone UI source | Implemented | OXT, Python relay, and Cloudflare relay use the same `shared/webui/` source. |
| Relay health endpoint | Implemented | `/health` reports relay runtime and limit status. |
| Relay session status endpoint | Implemented | `/api/session` lets LibreOffice detect joined phones. |
| Alternative relay implementations | Planned | The protocol is documented so other implementations can be written, but only Python and Cloudflare bundles ship today. |

## Development And QA

| Feature | Status | Notes |
| --- | --- | --- |
| `uv`-managed development environment | Implemented | `make venv` installs requirements without manual activation commands. |
| LibreOffice SDK downloader | Implemented | `make sdk-download` resolves a compatible SDK automatically. |
| OXT packaging tests | Implemented | Tests cover manifest presence, shared web assets, versioned OXT naming, and bundled resources. |
| Protocol and relay tests | Implemented | Unit and integration tests cover encrypted relay behavior and replay/reconnect paths. |
| Local HTTP endpoint integration tests | Implemented | Embedded HTTP tests cover static headers, direct session auth, encrypted state/assets/commands, fallback auth, local commands, slide bytes, stale revisions, and body-size limits. |
| Manual release checklist | Implemented | [Test Before Release](test-before-release.md) covers real OXT, LibreOffice, phone browser, local, hotspot, IPv6, relay, localization, and security checks. |
| Browser-level E2E tests | Planned | Manual browser testing is still required until automation can exercise Safari/local and encrypted direct/relay paths. |
| LibreOffice runtime matrix | Planned | More recorded LibreOffice-version and OS compatibility checks are still needed. |
| Product CI release gate | Implemented | CI installs dependencies, runs lint/tests, builds the OXT, builds relay bundles, and verifies generated artifacts. |
