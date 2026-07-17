<!-- SPDX-FileCopyrightText: 2026 Bora Yarkın -->
<!-- SPDX-License-Identifier: GPL-3.0-only -->

# Changelog

All notable changes to LibreOffice Impress Remote are documented here.

The project is pre-1.0. Early entries are recorded as development milestones instead of pretending a stable release ledger already exists.

## [Unreleased]

## [0.3.5] - 2026-07-17

### Added

- Added encrypted relay asset publishing for current and next slide PNG frames plus relay state image revisions so relay mode can render the same image-first mobile remote as the local path.

### Changed

- Rebuilt the relay-hosted phone UI to match the current lightweight mobile remote layout with the slide pinned to the top, scrollable presenter notes, bottom-pinned previous/next controls, and tap-to-advance on the slide.
- Hardened the relay server into a thinner opaque transport that validates only the outer protocol envelope, replays the latest `hello` plus a bounded window of recent encrypted plugin frames, and raises the websocket message limit for encrypted slide assets.

### Security

- Relay connections now reject legacy plaintext or malformed websocket messages instead of forwarding them across the third-party relay path.

## [0.3.4] - 2026-07-17

### Fixed

- Fixed addon command parsing so LibreOffice menu-status updates can resolve the Start Remote toggle command even when status listeners provide the full command URL instead of a populated `Path`, which keeps the menu label in sync with the running remote state.

### Changed

- Added a planned LibreOffice UX item for placing Presentation Remote under Slide Show across toolbar modes and adding Start Remote plus Advanced Remote Settings near Start from First Slide where the current UI supports it.

## [0.3.3] - 2026-07-17

### Changed

- Expanded the README and TODO roadmap notes to include planned GitHub release automation that publishes the extension package and a stripped relay-server release artifact after the standard workflows pass.

## [0.3.2] - 2026-07-17

### Changed

- Expanded the README roadmap to spell out the planned localization workflow: converting all user-facing strings to stable keys and adding importable i18n support for LibreOffice-language translation packs.

## [0.3.1] - 2026-07-17

### Added

- Added encrypted direct-IPv6 transport for presenter state, commands, and slide assets on the LibreOffice-served phone route.
- Added direct-IPv6 listener self-tests and LibreOffice-facing diagnostics for public-address detection and firewall or hotspot caveats.

### Changed

- Direct IPv6 route selection now advertises only globally reachable IPv6 addresses and only when the listener can reach its own advertised endpoint.
- The direct phone route now uses route-specific pairing fragments so the web app can distinguish local and direct IPv6 behavior.

### Fixed

- Fixed the IPv6 listener self-test helper typing so `network.py` no longer triggers the Pylance tuple-size error on `socket.create_connection`.

## [0.3.0] - 2026-07-17

### Added

- Added a LibreOffice-generated relay pairing secret that is embedded in QR and manual-link fragments for secure relay pairing.
- Added a versioned relay protocol with `hello`, `frame`, and `error` message types plus a protocol reference document.
- Added HKDF-SHA256 plus AES-256-GCM encrypted relay transport for state, command, and error frames.
- Added replay protection, session-bound authenticated metadata, plugin-driven key rotation, and secure relay state replay for newly joined phones during an active session.
- Added tests for AES-GCM helpers, encrypted relay codec flows, and secure relay state caching behavior.
- Added a LibreOffice-native configuration schema so transport settings persist in LibreOffice user settings instead of only in the extension fallback file.
- Added a LibreOffice dialog toggle for disabling the local listener during relay-only or direct-IPv6-only testing.
- Added richer presenter-state API fields for pause, blank-screen, timer, remaining-slides, and end-of-deck status.
- Added rendered next-slide thumbnail export and preload URLs for the embedded phone remote.
- Added a concrete project roadmap that separates local/direct upstream goals from the optional self-hosted relay companion path.
- Added LibreOffice-side usage guidance that explains the recommended local-first workflow directly in the settings dialog.

### Changed

- Relay pairing now expects the full pairing link when using the hosted relay UI, because the fragment carries the relay session key material.
- Relay servers now cache only the latest key advertisement and latest encrypted state for active plugin sessions and never need decrypted presenter data.
- Improved the LibreOffice settings dialog with draft-aware pairing previews, clearer issue reporting, and live QR/manual-link updates while route settings change.
- Improved runtime lifecycle handling so LibreOffice shutdown tears down local listeners and relay sessions cleanly.
- Improved slide-state tracking so controller fallbacks and render revisions stay synchronized when the presenter changes slides outside the phone UI.
- Improved the LibreOffice runtime status line to surface slide position and presenter timer details while the remote is running.
- Reframed the project documentation around a local-first strategy, with Direct IPv6 and relay treated as optional fallback paths instead of the main user story.

### Fixed

- Fixed stopped runtimes from accidentally starting the relay client while only saving settings.
- Fixed LibreOffice-side route previews to handle incomplete relay URLs without breaking the settings dialog.
- Fixed relay-session teardown to clear cached secure state when the plugin disconnects.
- Fixed relay-state pushes to reuse a single presenter snapshot per send cycle and surface protocol failures in runtime status output.

### Security

- Relay mode no longer forwards plaintext slide state or presenter commands through the relay server.
- Documented the remaining relay limitations: relay-served UI trust still needs a pinning or trusted-distribution story, and the current bootstrap still uses a pairing secret rather than ECDH P-256.

## [0.2.0] - 2026-07-15

### Added

- Initialized the repository with a LibreOffice `.oxt` extension skeleton.
- Added a local browser remote foundation.
- Added a lightweight Python relay server skeleton.
- Added architecture, security, LibreOffice extension, relay server, and compliance documentation.
- Added SPDX and REUSE metadata.
- Added GitHub Actions CI, package build, Dependency Review, CodeQL, and OpenSSF Scorecard workflows.
- Added a `uv`-based project setup flow through `make venv`.
- Added automatic LibreOffice SDK resolution, download, and installation through `make sdk-download`.
- Added editor workspace configuration and UNO stubs for saner Python analysis in the repo.
- Added controller, network, bootstrap, SDK, and relay tests.
- Added local/direct network discovery helpers for presenter sessions.
- Added persisted transport settings and a browser settings form for local port, IPv6, relay enablement, and relay URL.
- Added a hosted relay phone UI and an extension-side relay client that connects to the relay as the presentation plugin.
- Added LibreOffice menu actions for opening the browser console and editing transport settings inside a native dialog.
- Added current-slide PNG export for the local phone UI.
- Added LibreOffice-side pairing route selection with `auto`, `local`, `ipv6`, and `relay` modes.
- Added LibreOffice-side QR generation for phone pairing.

### Changed

- Upgraded the browser remote from a minimal polling view to a presenter-console layout with richer controls and connection details.
- Upgraded the local browser remote from timer-based polling to server-push updates with reconnect and offline handling plus a polling fallback for older browsers.
- Simplified the local phone UI into a lightweight remote with only the current slide, presenter notes, live status, and previous/next controls.
- Upgraded the LibreOffice extension UX with a QR-first control panel that owns relay setup, route selection, and phone pairing.
- Upgraded the extension-side presenter state from placeholder values to current slide, next slide, title, notes, and navigation metadata.
- Upgraded the local server to expose local IPv4 and direct IPv6 URLs and accept jump-to-slide requests.
- Upgraded relay health output and session tracking with richer metadata and guardrails.
- Upgraded the local server with preferred-port fallback, relay link publishing, relay connection status, and persistent transport config loading.
- Upgraded controller state handling to distinguish running presentations, editing-view readiness, empty decks, and non-Impress documents.
- Upgraded the relay server from a bare websocket switchboard to a hosted relay controller plus websocket transport.

### Fixed

- Fixed LibreOffice extension packaging to avoid bundling generated Python cache files.
- Fixed the SDK downloader to use macOS SDK DMGs on macOS and install their contents instead of downloading the Linux archive.
- Fixed repo analysis noise by excluding downloaded SDK artifacts from workspace diagnostics.
- Fixed LibreOffice extension path bootstrapping for file-URL based module loading and bumped the extension package to `0.1.2`.
- Fixed the LibreOffice Python component manifest entry to use the SDK-compatible Python UNO media type and bumped the extension package to `0.1.3`.

### Security

- Documented the planned E2E protocol and the browser-hosted frontend trust limitation.
