<!-- SPDX-FileCopyrightText: 2026 Bora Yarkın -->
<!-- SPDX-License-Identifier: GPL-3.0-only -->

# TODO

This file tracks the `1.0.1` project snapshot: what already ships today and what is still planned next.

For milestone order and project direction, see `docs/roadmap.md`.

Current product direction: local mode is the default, tested path, including same-Wi-Fi and many hotspot setups. One complete OXT ships local mode plus experimental LocalTunnel, direct IPv6, and relay mode support, with matching relay/documentation bundles embedded for export from LibreOffice.

## Planned

### 1. Broaden Local Mode Evidence

- Local compatibility evidence: Record local-mode results across supported LibreOffice versions, macOS, Windows, Linux, iOS Safari, Android Chrome, and Android Firefox.
- Browser-level E2E automation: Add automated coverage for essential phone UI behavior, Safari local fallback, encrypted local handshakes, reconnect flows, and command round trips.
- Accessibility verification: Verify keyboard navigation, focus order, screen-reader labels, status announcements, QR/Copy URL fallback, and phone remote controls across supported desktop and phone platforms.
- Release readiness evidence: Keep recording real manual compatibility results for local same-Wi-Fi and hotspot workflows after `1.0.0`.

### 2. Release And Volunteer Maintenance Readiness

- Documentation baseline: Keep the feature matrix, troubleshooting guide, architecture, protocol, and security model updated as behavior changes.
- Volunteer maintenance notes: Keep the docs clear that this is a best-effort FOSS project with no guaranteed maintenance cadence or long-term support branches.
- Release readiness maintenance: Keep the release-readiness gates and support policy updated as planned features land.

### 3. Experimental Route Hardening

- LocalTunnel testing: Verify tunnel creation, teardown, provider failure behavior, browser loading, and encrypted command/state paths in real networks.
- Direct IPv6 testing: Verify public IPv6 discovery, firewall guidance, and encrypted browser behavior on networks with and without usable IPv6.
- Relay testing: Verify Python relay, Cloudflare relay, service scripts, reverse proxies, and encrypted reconnect behavior on real deployments.
- Experimental labeling: Keep LocalTunnel, Direct IPv6, and Relay Server docs and UI honest about their experimental status.

### 4. Extension Polish

- LibreOffice Help content: Add polished help pages and keep in-product troubleshooting aligned with the local-first, hotspot-friendly workflow.
- Localization expansion: Add more translated catalogs only after the English source strings settle.
- UI polish: Keep the extension feeling small, understandable, and native enough for normal Impress users.
- Possible future adapters: Revisit MS Office, browser-extension, or other suite adapters only if someone volunteers to build and maintain them.

## Implemented

### LibreOffice UX And Integration

- Impress-only UI integration: The extension appears under Impress `Slide Show`, not Writer or Calc, and exposes direct Start/Stop Remote plus Remote Settings actions where LibreOffice toolbar merging supports it.
- LibreOffice-owned settings: Remote Settings owns the mode selector, relay URL in Relay Server mode, relay/documentation resource export, and help.
- QR-first pairing: Start Remote opens a QR pairing popup, closes after a phone connects, and keeps Copy URL in the QR popup as the manual fallback.
- Explicit mode policy: Start Remote obeys the saved mode directly: Local network, LocalTunnel, Direct IPv6, or Relay Server.
- Simplified settings UI: Relay URL and bundled relay/documentation export controls are visible only when Relay Server mode is selected.
- In-product guidance: LibreOffice explains same-Wi-Fi, phone-hotspot, LocalTunnel fallback, direct IPv6, relay, and Copy URL usage inside Start Remote, Remote Settings, and Help flows.
- Config persistence: Transport settings are stored in LibreOffice configuration data, with migration/fallback support for the earlier extension-owned config file.
- Extension-focused docs: The architecture documents the extension and its optional experimental routes without treating a LibreOffice-core merge as the project destination.

### Presenter State, Control, And Rendering

- Presenter state: The extension reports document kind, slideshow running/active/paused state, slide count, current and next slide indexes, titles, notes, previews, remaining slides, end-of-deck state, timer state, and render tokens.
- Presentation control: Remote transports accept start, start-from-first-slide, previous/next slide, first/last slide, and goto-slide commands.
- Slide rendering: The extension exports Impress slides to PNG and serves current and next slide previews to the phone UI.
- Low-latency local previews: Local mode prewarms a bounded server-side PNG cache for the full deck when the remote starts, and the phone preloads the next rendered slide.
- Robust state fallbacks: The controller handles editing view, empty decks, non-Impress documents, controller-state fallbacks, stale render revisions, and clearer user-facing state messages.

### Phone UI

- Lightweight remote: The phone UI shows the current slide image pinned at the top, presenter notes as the only scrollable area, and bottom-pinned previous/next controls.
- Minimal controls: Tapping the slide advances, and a compact icon-only drawer exposes first-slide, last-slide, timer pause/resume, fullscreen, and jump-to-slide actions without adding phone-side settings.
- Runtime feedback: The phone UI includes presentation timers, a reconnect/offline panel, retry/reload actions, and focus/accessibility polish on a normal browser page.
- Shared web source: The authored phone UI lives in `shared/webui/` and is reused by the OXT, Python relay bundle, and Cloudflare relay bundle.

### Local And Direct IPv6 Routes

- Embedded local server: The extension starts/stops embedded HTTP listeners, exposes local IPv4 URLs, exposes direct IPv6 URLs when available, and falls back to the next available local port when the preferred port is busy.
- LocalTunnel route: A vendored pure-Python LocalTunnel-compatible client can expose the extension-hosted phone UI and encrypted local/direct HTTP API through a temporary public URL without requiring Node.js, npm, or the project-specific relay server at runtime.
- Local security posture: Web-Crypto-capable local mode uses encrypted state, command, event, and slide-asset endpoints; Safari-style LAN browsers can use an authenticated plaintext `/api/local/*` fallback.
- Local hardening: Embedded responses send browser security headers, direct endpoints require the pairing session id, command payloads are size-limited, stale slide revisions return conflicts, and plaintext fallback endpoints are limited to local-network clients.
- Direct IPv6 readiness: The extension advertises only globally reachable IPv6 addresses, self-tests the IPv6 listener before offering the route, and surfaces router/firewall/hotspot guidance when IPv6 is unavailable.
- Runtime flexibility: Users can switch modes for local, LocalTunnel, direct-IPv6, or relay testing, and LibreOffice shutdown tears down listeners and relay sessions cleanly.

### Relay Mode And Relay Server

- Relay client mode: LibreOffice can persist relay settings, connect outbound as the plugin, publish relay pairing links with admission tokens, detect joined phones, auto-start the slideshow, receive encrypted commands, and publish encrypted state/assets.
- Reference relay server: The Python relay exposes `/`, `/app.js`, `/app.css`, `/asset-manifest.json`, `/health`, `/api/session`, and `/ws`, serves the shared phone UI, validates protocol envelopes, forwards opaque frames, replaces stale plugins, and expires empty or stale sessions.
- Relay deployment bundles: The repository builds a stripped Python relay bundle and a Cloudflare Worker plus Durable Object bundle, both using the shared phone UI.
- Relay operations: The Python relay bundle includes a one-command foreground runner plus Linux and Windows service install/uninstall scripts that persist a randomly chosen port.
- Relay safety: Reference relays enforce session-id limits, phone-count limits, websocket message-size limits, admission tokens, structured logs, metrics, rate limits, send-failure cleanup, and stale-session expiry.
- Relay reconnect: Active sessions replay the latest key advertisement plus a bounded window of encrypted plugin frames to newly joined phones, without server-side decryption, and clear cached secure state when the plugin disconnects.
- Relay docs: VPS, reverse proxy, TLS, firewall, session-status, and bundle-verification guidance exists for the Python and Cloudflare relay deployments.
- Relay ecosystem validation: `make relay-compat` validates the implementation-independent public relay contract for compatible Python, Cloudflare, or third-party relays.

### Security And Protocol

- Shared encrypted protocol: Local/direct and relay transports use versioned `hello`, `frame`, and `error` messages with a two-way ECDH P-256 handshake before deriving AES transport keys.
- Relay encryption: LibreOffice generates a per-pairing verifier, derives relay keys with ECDH P-256 plus HKDF-SHA256, encrypts state, command, and asset frames with AES-256-GCM, binds frames to the session, detects replayed nonces, and rotates plugin send keys.
- Crypto foundation: Random session tokens, base64url helpers, HKDF-SHA256 helpers, and pure-Python AES-GCM helpers are implemented.
- Security model docs: The current local HTTP shell, Safari fallback, direct IPv6, relay frontend-delivery trust model, and self-hosted relay verification guidance are documented honestly.
- Trusted frontend delivery baseline: The OXT, Python relay, Cloudflare relay, and local server generate asset manifests with SHA-256 and SRI metadata, and packaged index pages pin the shared CSS/JS with subresource integrity.

### Packaging, Release, And Tooling

- OXT packaging: LibreOffice `.oxt` packaging, manifest files, extension metadata, direct Slide Show menu registration, version injection, build-feature metadata, and versioned OXT builds are in place.
- Single complete extension build: `make oxt` builds one OXT containing local, LocalTunnel, direct IPv6, relay mode, matching documentation, and relay export bundles.
- Bundled resources: The OXT embeds matching documentation, Python relay, and Cloudflare relay bundles for export from Remote Settings when Relay Server mode is selected.
- GitHub release automation: The release workflow runs build gates, creates a version tag when needed, generates checksums, and publishes the versioned OXT to a GitHub Release.
- Development setup: `make venv` creates a `uv`-managed environment with dependencies installed, and `make sdk-download` resolves/downloads/installs a compatible LibreOffice SDK automatically.
- Editor support: Workspace analysis config, import roots, and UNO stubs are in place to keep Pylance usable.
- Localization catalogs: User-facing LibreOffice and phone UI strings use stable keys backed by English and Turkish JSON catalogs under `shared/localizations/`.
- Localization import workflow: `make localization-import` validates and imports new translation catalogs, checks unknown/missing keys, validates placeholders, and lets the phone UI discover shipped locales from `/localizations/manifest.json`.

### Documentation And QA

- Product docs: README, user guide, feature matrix, install/runtime troubleshooting, architecture, protocol, relay, release-readiness, roadmap, and security docs are aligned with the current behavior.
- Release readiness: Local, direct IPv6, and relay gates, target compatibility policy, latest-release support policy, manual release checklist, and release blockers are documented.
- Product CI: CI installs test dependencies, runs lint and tests, builds the single versioned OXT, and verifies the generated extension artifact.
- Automated tests: Unit and integration coverage exists for bootstrap/import behavior, SDK resolution, config, protocol helpers, crypto helpers, controller state extraction, embedded local HTTP endpoints, encrypted local/direct round trips, network URL helpers, relay admission/reconnect/security behavior, manifest presence, packaging, localization, and bundled resources.
- Manual testing docs: `docs/test-before-release.md` covers OXT install, Impress UI integration, local and hotspot pairing, Safari fallback, direct IPv6, Python relay, Cloudflare relay, phone UI, localization, security, and release notes.
