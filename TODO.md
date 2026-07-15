<!-- SPDX-FileCopyrightText: 2026 Bora Yarkın -->
<!-- SPDX-License-Identifier: GPL-3.0-only -->

# TODO

This file tracks the `0.2.0` project snapshot: what already ships today and what is still planned next.

For milestone order and upstream strategy, see `docs/roadmap.md`.

Current product direction: local mode is the primary path, including same-Wi-Fi and many hotspot setups. Direct IPv6 and relay remain optional fallback routes.

## Implemented

- Packaging: LibreOffice `.oxt` packaging, manifest files, menu registration, versioned extension builds, and source-only OXT output are in place.
- Setup tooling: `make venv` creates a `uv`-managed environment with project dependencies installed, and `make sdk-download` resolves, downloads, and installs a compatible LibreOffice SDK.
- Local mode server: The extension can start and stop embedded HTTP listeners, expose local IPv4 URLs, expose direct IPv6 URLs when available, and fall back to the next available local port when the preferred one is busy.
- Local mode runtime UX: The phone UI now receives live server-push updates, shows reconnect and offline states, falls back to polling when `EventSource` is unavailable, and preloads the next rendered slide image without adding extra phone UI controls.
- Presenter state: The extension reports slide count, current slide index, current slide title, presenter notes, next slide index, next slide title, richer controller-state fallbacks, current and next slide render tokens, next-slide thumbnails for preload/export, presenter timer state, blank-screen state, end-of-deck state, and clearer state when no presentation is open or when the active document is not Impress.
- Presentation control: The phone UI can start a slideshow, end a slideshow, move by slide, move by effect, and jump to a specific slide.
- Phone UI: The local browser remote now acts as a lightweight dummy remote with a full current-slide image, presenter notes, live status, and side-by-side previous and next buttons.
- Slide rendering: The extension can export the current Impress slide to PNG and serve it to the local phone UI.
- LibreOffice UX: The extension menu now exposes start, stop, open-console, and settings actions, and the LibreOffice dialog now owns route selection, relay configuration, runtime status, QR-based phone pairing, and recoverable runtime issue reporting.
- Pairing flow: The extension now supports `auto`, `local`, `ipv6`, and `relay` pairing modes, with `auto` preferring local first, then direct IPv6, then relay, and local mode is the primary recommended route.
- Relay mode prototype: The extension can persist relay settings, open an outbound relay connection as the plugin, publish a shareable relay link, receive commands from relay-connected phones, and push live presentation state over the relay.
- Relay server: The relay exposes `/`, `/app.js`, `/app.css`, `/health`, and `/ws`, serves a relay-hosted phone controller UI, forwards plugin and phone WebSocket messages, replaces an existing plugin when a new one joins, and expires empty or stale sessions.
- Relay safety: Session-id length limits, phone-count limits, and WebSocket message-size limits are implemented.
- Crypto foundation: Random session token generation and HKDF-SHA256 helpers exist.
- Config persistence: Transport settings are stored in LibreOffice configuration data with migration/fallback support for the earlier extension-owned config file.
- Runtime flexibility: Users can disable the local listener for relay-only or direct-IPv6-only testing, and LibreOffice shutdown now tears down listeners and relay sessions cleanly.
- Editor support: Workspace analysis config, import roots, and UNO stubs are in place to keep Pylance usable in this repo.
- Tests: Unit and integration coverage exists for bootstrap/import behavior, SDK resolution logic, config and protocol helpers, controller state extraction, network URL helpers, crypto helpers, manifest presence, and relay message forwarding.

## Planned

- Local mode: Decide whether to support HTTPS locally or explicitly document the chosen trust model.
- Local mode: Expand in-product and user-facing guidance for same-Wi-Fi and hotspot usage.
- Phone UI: Add stronger error presentation, retry flows, and accessibility polish for mobile use.
- Phone UI: Add installable PWA behavior if offline launch or homescreen install is desired.
- Localization: Move LibreOffice dialog strings, menu labels, status text, errors, and phone UI copy into a translation-friendly workflow that can scale to LibreOffice's language coverage.
- Direct IPv6 mode: Detect whether the host has a globally reachable IPv6 address, not just any non-link-local IPv6, when local mode is unavailable.
- Direct IPv6 mode: Add reachability checks and user-facing guidance for router, firewall, and hotspot caveats.
- Direct IPv6 mode: Secure direct IPv6 transport with the same protocol used in other modes.
- Bluetooth support: Design and implement a Bluetooth-based pairing and control path for environments where local network, IPv6, and relay are poor fits.
- Relay mode: Add session creation, pairing, resume, and reconnect behavior for relay transport as a fallback path.
- Relay mode: Add relay deployment docs for VPS, reverse proxy, TLS, and firewall setup.
- Relay mode: Add authentication or admission control if public relay deployment is expected.
- Security and protocol: Implement the planned ECDH P-256 key exchange.
- Security and protocol: Implement AES-GCM encrypted frames instead of plaintext relayed messages.
- Security and protocol: Define a shared protocol for commands, state updates, previews, errors, and version negotiation.
- Security and protocol: Add replay protection, session binding, and key rotation rules.
- Security and protocol: Decide how to trust or pin the phone UI when it is served through a relay-controlled origin.
- Relay hardening: Add structured logs and operational metrics.
- Relay hardening: Add abuse protections if the relay will be internet-facing.
- Relay hardening: Add more cleanup and backpressure behavior for noisy or abandoned clients.
- Testing: Add local HTTP endpoint tests for the embedded extension server.
- Testing: Add end-to-end manual or automated scenarios for local, IPv6, and relay workflows.
- Testing: Add coverage for the future relay client and encrypted protocol once implemented.
- Testing: Add broader LibreOffice runtime compatibility checks across supported versions.
- Documentation: Keep a user-facing feature matrix that clearly marks implemented versus planned behavior.
- Documentation: Expand the run/install troubleshooting guide for LibreOffice extension loading failures.
- Documentation: Add a clearer architecture and protocol document for the three transport paths.
- Documentation: Keep security docs aligned with the gap between prototype behavior and production goals.
- LibreOffice integration: Align architecture, UX, packaging, and contribution requirements with the long-term goal of making this part of LibreOffice itself.
- Release readiness: Define milestones for local mode, direct IPv6 mode, and relay mode reaching true end-to-end usability.
- Release readiness: Decide the minimum supported LibreOffice versions and supported desktop platforms.
- Release readiness: Expand CI coverage for packaged extension verification and broader test execution.
