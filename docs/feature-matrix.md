<!-- SPDX-FileCopyrightText: 2026 Bora Yarkın -->
<!-- SPDX-License-Identifier: GPL-3.0-only -->

# Feature Matrix

This matrix reflects the `0.7.6` snapshot. It is deliberately user-facing: it separates what can be tested today from what is planned, so the README can stay short without hiding project status.

## User Workflow

| Feature | Status | Notes |
| --- | --- | --- |
| Install as a LibreOffice `.oxt` extension | Implemented | Built with `make oxt`; output is versioned as `dist/libreoffice-impress-remote-<version>.oxt`. |
| Start/stop remote from Impress | Implemented | Available from `Slide Show -> Start Remote`; the menu item toggles to Stop Remote while running. |
| QR-first pairing | Implemented | Start Remote opens a QR-only pairing popup; manual link is available from Remote Settings as a backup. |
| Explicit mode selection | Implemented | Remote Settings selects Local network, LocalTunnel, Direct IPv6, or Relay Server, and Start Remote obeys the saved mode. |
| Same-Wi-Fi and hotspot local mode | Implemented | This is the recommended path and works for many normal Wi-Fi and phone-hotspot setups. |
| LocalTunnel fallback | Implemented | The OXT includes a vendored pure-Python LocalTunnel-compatible client for non-local testing without a project-specific relay server. |
| In-product step-by-step help | Implemented | Start Remote, Remote Settings, and Help explain same-Wi-Fi, phone-hotspot, manual-link, LocalTunnel, IPv6, and relay usage. |
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
| Plain browser remote | Implemented | The QR opens a normal browser page; installable PWA manifest, icon, and service worker shell are intentionally omitted. |
| Presentation timer on phone | Implemented | The timer is shown over the slide while a slideshow is running. |
| Richer mobile controls | Implemented | A compact icon-only drawer exposes first-slide, last-slide, timer pause/resume, fullscreen, and jump-to-slide actions without adding settings to the phone UI. |
| Low-latency full-deck preload | Implemented | Local mode prewarms a bounded server-side PNG cache for the full deck when the remote starts, and the phone still preloads the next slide image. |

## LibreOffice UX

| Feature | Status | Notes |
| --- | --- | --- |
| Impress-only menu integration | Implemented | Start/Stop Remote and Remote Settings are merged into Impress Slide Show UI rather than Writer or Calc. |
| Toolbar/notebookbar buttons | Implemented | Supported toolbar modes get Start/Stop Remote and Remote Settings near slideshow controls. |
| Remote Settings | Implemented | Owns mode selection, relay URL, runtime status, manual link, relay-only resource export, issues, and help. |
| Bundled resource export | Implemented | Users can export documentation and matching Python relay/Cloudflare bundles from Relay Server mode. |
| Broad platform UX verification | Planned | More compatibility evidence is needed across supported LibreOffice versions and desktop platforms. |
| LibreOffice-core proof of concept | Planned | The extension is a prototype path; a core patch would need a smaller native implementation. |

## Transport And Security

| Feature | Status | Notes |
| --- | --- | --- |
| Encrypted relay transport | Implemented | Relay forwards opaque encrypted frames and does not decrypt notes, commands, or slide assets. |
| Encrypted direct IPv6 transport | Implemented | Direct IPv6 uses the same `hello`/`frame` contract as relay mode. |
| Encrypted LocalTunnel transport | Implemented | LocalTunnel mode exposes the extension-hosted web UI and encrypted direct HTTP endpoints through the public tunnel URL. |
| Encrypted local transport when Web Crypto is available | Implemented | Modern browsers use session-bound `/api/direct/*` encrypted state, command, event, and slide-asset endpoints. |
| Safari local compatibility fallback | Implemented | Local mode can use LAN-only authenticated plaintext `/api/local/*` polling when Safari does not expose Web Crypto on LAN HTTP origins. |
| Relay admission token | Implemented | Relay phone links include an admission token required for `/api/session` and `/ws`. |
| Replay checks and key rotation | Implemented | Encrypted frames are session-bound and nonce replay is rejected. |
| ECDH P-256 bootstrap | Implemented | Encrypted local/direct and relay modes derive transport keys from ephemeral P-256 ECDH plus the QR pairing verifier. |
| Shared frontend asset manifest and SRI | Implemented | OXT, Python relay, Cloudflare relay, and local server builds expose SHA-256/SRI metadata, and packaged pages pin shared CSS/JS with subresource integrity. |
| Local HTTPS | Planned | Current local web shell is still served over HTTP, so encrypted frames reduce passive-observer exposure but do not stop active script replacement. |

## Relay And Deployment

| Feature | Status | Notes |
| --- | --- | --- |
| Python relay server | Implemented | Self-hostable on a VPS or local machine. |
| Python relay service helpers | Implemented | Linux and Windows service install/uninstall helpers exist in the release bundle. |
| Cloudflare Worker relay bundle | Implemented | The matching Worker plus Durable Object relay bundle is embedded in the OXT for export from Relay Server mode. |
| Shared phone UI source | Implemented | OXT, Python relay, and Cloudflare relay use the same `shared/webui/` source. |
| Relay health endpoint | Implemented | `/health` reports relay runtime and limit status. |
| Relay session status endpoint | Implemented | `/api/session` lets LibreOffice detect joined phones. |
| Alternative relay implementations | Implemented | The protocol is documented and `make relay-compat RELAY_URL=...` validates the public HTTP contract for compatible relay implementations. |

## Development And QA

| Feature | Status | Notes |
| --- | --- | --- |
| `uv`-managed development environment | Implemented | `make venv` installs requirements without manual activation commands. |
| LibreOffice SDK downloader | Implemented | `make sdk-download` resolves a compatible SDK automatically. |
| Localization import workflow | Implemented | `make localization-import ARGS="path/to/locale.json"` validates and imports keyed catalogs for new languages. |
| OXT packaging tests | Implemented | Tests cover manifest presence, shared web assets, versioned OXT naming, and bundled resources. |
| Protocol and relay tests | Implemented | Unit and integration tests cover encrypted relay behavior and replay/reconnect paths. |
| Local HTTP endpoint integration tests | Implemented | Embedded HTTP tests cover static headers, direct session auth, encrypted state/assets/commands, fallback auth, local commands, slide bytes, stale revisions, and body-size limits. |
| Manual release checklist | Implemented | [Test Before Release](test-before-release.md) covers real OXT, LibreOffice, phone browser, local, hotspot, IPv6, relay, localization, and security checks. |
| Browser-level E2E tests | Planned | Manual browser testing is still required until automation can exercise Safari/local and encrypted direct/relay paths. |
| LibreOffice runtime matrix | Planned | More recorded LibreOffice-version and OS compatibility checks are still needed. |
| Product CI release gate | Implemented | CI installs dependencies, runs lint/tests, builds the single versioned OXT, and verifies the generated artifact. |
