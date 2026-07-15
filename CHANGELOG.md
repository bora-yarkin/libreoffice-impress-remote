<!-- SPDX-FileCopyrightText: 2026 Bora Yarkın -->
<!-- SPDX-License-Identifier: GPL-3.0-only -->

# Changelog

All notable changes to LibreOffice Impress Remote are documented here.

The project is pre-1.0. Early entries are recorded as development milestones instead of pretending a stable release ledger already exists.

## [Unreleased]

### Added

- Added a LibreOffice-native configuration schema so transport settings persist in LibreOffice user settings instead of only in the extension fallback file.
- Added a LibreOffice dialog toggle for disabling the local listener during relay-only or direct-IPv6-only testing.
- Added richer presenter-state API fields for pause, blank-screen, timer, remaining-slides, and end-of-deck status.
- Added rendered next-slide thumbnail export and preload URLs for the embedded phone remote.
- Added a concrete project roadmap that separates local/direct upstream goals from the optional self-hosted relay companion path.

### Changed

- Improved the LibreOffice settings dialog with draft-aware pairing previews, clearer issue reporting, and live QR/manual-link updates while route settings change.
- Improved runtime lifecycle handling so LibreOffice shutdown tears down local listeners and relay sessions cleanly.
- Improved slide-state tracking so controller fallbacks and render revisions stay synchronized when the presenter changes slides outside the phone UI.
- Improved the LibreOffice runtime status line to surface slide position and presenter timer details while the remote is running.

### Fixed

- Fixed stopped runtimes from accidentally starting the relay client while only saving settings.
- Fixed LibreOffice-side route previews to handle incomplete relay URLs without breaking the settings dialog.

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
- Documented that the current relay prototype still forwards plaintext JSON frames until E2E encryption lands.
