<!-- SPDX-FileCopyrightText: 2026 Bora Yarkın -->
<!-- SPDX-License-Identifier: GPL-3.0-only -->

# TODO

This file tracks the `0.6.12` project snapshot: what already ships today and what is still planned next.

For milestone order and upstream strategy, see `docs/roadmap.md`.

Current product direction: local mode is the primary path, including same-Wi-Fi and many hotspot setups. Direct IPv6 and relay remain optional fallback routes.

## Implemented

- Packaging: LibreOffice `.oxt` packaging, manifest files, menu registration, and versioned extension builds are in place.
- Packaging resources: The `.oxt` now embeds the matching stripped Python relay bundle, Cloudflare relay bundle, and documentation bundle for the extension version, and Advanced Remote Settings can export them to Downloads or a selected folder.
- Setup tooling: `make venv` creates a `uv`-managed environment with project dependencies installed, `make sdk-download` resolves, downloads, and installs a compatible LibreOffice SDK, and the build flow now ships `make release-bundle`, `make cloudflare-bundle`, and `make release-full` outputs.
- Local mode server: The extension can start and stop embedded HTTP listeners, expose local IPv4 URLs, expose direct IPv6 URLs when available, and fall back to the next available local port when the preferred one is busy.
- Local mode security: Local presenter state, commands, and slide assets now use the same encrypted `hello`/`frame` protocol as direct IPv6 when browser Web Crypto is available, Safari-style LAN browsers can use an authenticated plaintext `/api/local/*` compatibility fallback, and the local HTTP shell trust model is explicitly documented instead of pretending local HTTPS exists.
- Local mode runtime UX: The phone UI now receives live server-push updates, shows reconnect and offline states, falls back to polling when `EventSource` is unavailable, and preloads the next rendered slide image without adding extra phone UI controls.
- Presenter state: The extension reports slide count, current slide index, current slide title, presenter notes, next slide index, next slide title, richer controller-state fallbacks, current and next slide render tokens, next-slide thumbnails for preload/export, presenter timer state, blank-screen state, end-of-deck state, and clearer state when no presentation is open or when the active document is not Impress.
- Presentation control: The extension runtime accepts slideshow start/end, slide/effect navigation, and goto-slide commands over the remote transport, and the current phone UI exposes previous/next slide controls plus tap-to-advance.
- Phone UI: The local browser remote now acts as a lightweight dummy remote with a full current-slide image, presenter notes, live status, side-by-side previous and next buttons, visible connection recovery, retry/reload actions, focus/accessibility polish, and installable PWA shell metadata, and the authored web UI now lives in a shared source tree reused across the extension, Python relay, and Cloudflare relay bundle.
- Slide rendering: The extension can export the current Impress slide to PNG and serve it to the local phone UI.
- LibreOffice UX: The extension integrates as an Impress-only Slide Show submenu, exposes supported toolbar buttons for Start/Stop Remote and Advanced Remote Settings next to LibreOffice's built-in slideshow controls where addon toolbar merging is supported, and the LibreOffice dialog now owns route selection, relay configuration, runtime status, QR-based phone pairing, and recoverable runtime issue reporting.
- LibreOffice integration: The architecture now separates the LibreOffice-core candidate from companion relay/deployment scope, maps extension seams to likely LibreOffice modules, and documents a reviewable upstream patch strategy in `docs/libreoffice-upstream-architecture.md`.
- Pairing flow: The extension now supports `auto`, `local`, `ipv6`, and `relay` pairing modes, with `auto` preferring local first, then direct IPv6, then relay, and local mode is the primary recommended route.
- Direct IPv6 mode: The extension now advertises only globally reachable IPv6 addresses, self-tests the IPv6 listener before offering the route, surfaces router/firewall/hotspot guidance in LibreOffice, and uses encrypted state, command, and slide-asset transport for the direct IPv6 phone route.
- Relay mode: The extension can persist relay settings, open an outbound relay connection as the plugin, publish a shareable relay link with a relay admission token, detect joined phones from the relay session-status API so LibreOffice can auto-start the slideshow, receive encrypted commands from relay-connected phones, push live presentation state over the relay, and publish encrypted current/next slide asset frames for the relay-hosted phone UI.
- Relay server: The relay exposes `/`, `/app.js`, `/app.css`, `/asset-manifest.json`, `/health`, `/api/session`, and `/ws`, serves a lightweight relay-hosted phone remote, validates current protocol envelopes, forwards opaque encrypted plugin and phone frames, replaces an existing plugin when a new one joins, and expires empty or stale sessions.
- Relay deployment bundles: The repository now produces a self-hosted Python relay release bundle and a separate Cloudflare Worker plus Durable Object bundle that both serve the same shared mobile remote UI.
- Relay operations: The standalone Python relay bundle now includes a one-command foreground runner plus Linux and Windows install/uninstall service scripts that persist a randomly chosen port.
- Relay deployment docs: VPS, reverse proxy, TLS, firewall, session-status, and bundle-verification guidance now exist for the Python and Cloudflare relay deployments.
- Relay safety: Session-id length limits, phone-count limits, websocket message-size limits, per-session admission tokens, structured runtime logs, per-session metrics, rate limits, and send-failure cleanup are implemented across the reference relay deployments.
- Relay protocol: The relay now uses versioned `hello`, `frame`, and `error` messages for negotiation, commands, state updates, and runtime errors.
- Relay security: LibreOffice now generates a per-pairing secret, carries it in QR and manual-link fragments together with the relay admission token, derives relay keys with HKDF-SHA256, encrypts relay state, command, and error frames with AES-256-GCM, binds frames to the session with authenticated metadata, detects replayed nonces, rotates plugin send keys, and documents the current self-hosted UI trust model through release-bundle asset verification.
- Relay reconnect: Active relay sessions replay the latest key advertisement plus a bounded window of recent encrypted plugin frames to newly joined phones without server-side decryption, and cached secure state is cleared when the plugin disconnects.
- Crypto foundation: Random session token generation, base64url helpers, HKDF-SHA256 helpers, and pure-Python AES-GCM helpers exist.
- Config persistence: Transport settings are stored in LibreOffice configuration data with migration/fallback support for the earlier extension-owned config file.
- Localization: User-facing LibreOffice menu labels, dialogs, status text, surfaced errors, and phone UI copy now use stable keys backed by shared English and Turkish JSON catalogs under `localizations/`.
- Runtime flexibility: Users can disable the local listener for relay-only or direct-IPv6-only testing, and LibreOffice shutdown now tears down listeners and relay sessions cleanly.
- Editor support: Workspace analysis config, import roots, and UNO stubs are in place to keep Pylance usable in this repo.
- Tests: Unit and integration coverage exists for bootstrap/import behavior, SDK resolution logic, config and protocol helpers, controller state extraction, network URL helpers, crypto helpers, encrypted relay protocol flows, relay admission control and reconnect handling, manifest presence, and relay message forwarding.

## Planned

- Local mode: Expand in-product and user-facing guidance for same-Wi-Fi and hotspot usage.
- Packaging: Add a source-only OXT output alongside the current packaged extension build.
- Phone UI: Expose richer slideshow controls such as start/end, effect-step navigation, and jump-to-slide actions when the mobile UX is ready.
- Local mode: Add a low-latency mode that pre-renders and preloads the full deck before the remote opens so slide changes avoid export-time stalls.
- Localization: Expand the initial English and Turkish catalogs into importable translation packs that can scale to LibreOffice's language coverage.
- Security and protocol: Replace the current pairing-secret bootstrap with the planned ECDH P-256 key exchange.
- Testing: Add local HTTP endpoint tests for the embedded extension server.
- Testing: Add end-to-end manual or automated scenarios for local and direct-IPv6 workflows.
- Testing: Add broader browser-level coverage for encrypted direct-IPv6 handshakes, key rotation, and future secure local resume flows.
- Testing: Add broader LibreOffice runtime compatibility checks across supported versions.
- Documentation: Keep a user-facing feature matrix that clearly marks implemented versus planned behavior.
- Documentation: Expand the run/install troubleshooting guide for LibreOffice extension loading failures.
- Documentation: Keep the architecture and protocol documents aligned as local, IPv6, and relay transports converge.
- Documentation: Keep security docs aligned with the gap between prototype behavior and production goals.
- LibreOffice integration: Reduce extension-specific assumptions that would be awkward in core and expand compatibility evidence before attempting a LibreOffice-core proof of concept.
- Release automation: Add GitHub release support so standard CI workflows gate publication, then publish a GitHub release containing the extension package and a minimal relay-server release artifact stripped of documentation.
- Release readiness: Define milestones for local mode, direct IPv6 mode, and relay mode reaching true end-to-end usability.
- Release readiness: Decide the minimum supported LibreOffice versions and supported desktop platforms.
- Release readiness: Expand CI coverage for packaged extension verification and broader test execution.
