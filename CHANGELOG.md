<!-- SPDX-FileCopyrightText: 2026 Bora Yarkın -->
<!-- SPDX-License-Identifier: GPL-3.0-only -->

# Changelog

All notable changes to LibreOffice Impress Remote are documented here.

Early `0.x` entries are recorded as development milestones instead of pretending they were stable release lines.

## [Unreleased]

## [1.0.1] - 2026-07-23

### Changed

- Applied Dependabot's GitHub Actions updates to the current workflows, including the release workflow: `actions/checkout` 7.0.1, `actions/setup-python` 7.0.0, and `github/codeql-action` 4.37.2 pinned SHAs.
- Applied Dependabot's server dependency updates: `aiohttp>=3.14.2` and `ruff>=0.15.22`.
- Bumped the extension, relay package, and project version to `1.0.1`.

## [1.0.0] - 2026-07-22

### Added

- Added GitHub release automation that runs compile, lint, tests, builds the versioned OXT, generates SHA-256 checksums, creates a matching `v<VERSION>` tag when run manually, and creates or updates the GitHub Release.

### Changed

- Promoted the extension to `1.0.0` as the first local-mode release while keeping LocalTunnel, Direct IPv6, and relay modes documented as experimental.
- Updated release-readiness, README, roadmap, feature matrix, protocol, security, and development docs for the `1.0.0` release line.
- Bumped the extension, relay package, and project version to `1.0.0`.

## [0.7.8] - 2026-07-22

### Documentation

- Refreshed the documentation set around the current 0.7.8 UI: Start/Stop Remote, Remote Settings, QR popup Copy URL fallback, Local network, LocalTunnel, Direct IPv6, and Relay Server modes.
- Removed redundant standalone LibreOffice extension, compliance, and old planning documents by folding useful content into extension-focused architecture and roadmap docs.
- Reframed the project docs around the extension-first volunteer direction: local mode is the tested main `1.0.0` gate, while LocalTunnel, Direct IPv6, and relay modes are experimental.
- Removed README screenshot placeholders.
- Added store-ready extension listing wording for TDF submission.

### Changed

- Replaced the packaged extension icon with the new presentation-screen and phone-remote SVG.
- Replaced install-facing English and Turkish extension descriptions with store-ready wording based on the TDF listing details.
- Bumped the extension, relay package, and project version to `0.7.8`.

## [0.7.7] - 2026-07-22

### Changed

- Removed stale phone-only localization keys for commands no longer exposed by the mobile remote.
- Removed the redundant standalone manifest-check helper and let Product CI rely on the richer test suite plus OXT build verification.
- Consolidated GitHub security and branch-protection notes into release readiness documentation.
- Trimmed no-longer-exposed controller command handlers and removed dead blank-presentation state from controller, component, and local-server payloads.
- Bumped the extension, relay package, and project version to `0.7.7`.

## [0.7.6] - 2026-07-22

### Changed

- Fixed the phone total timer so slide updates no longer reset it back to zero while the presentation is running.
- Removed the phone drawer blank-screen control.
- Bumped the extension, relay package, and project version to `0.7.6`.

## [0.7.5] - 2026-07-22

### Changed

- Replaced the confusing phone drawer timer and blank-screen glyphs with clearer pause/play and screen-off/screen-on icons.
- Bumped the extension, relay package, and project version to `0.7.5`.

## [0.7.4] - 2026-07-22

### Added

- Added a phone fullscreen slide mode button next to the controls drawer button.
- Fullscreen slide mode hides presenter notes, expands the slide, requests fullscreen/landscape orientation when supported, and shows duplicated previous/next controls on both left and right edges.
- Bumped the extension, relay package, and project version to `0.7.4`.

## [0.7.3] - 2026-07-22

### Changed

- Simplified the phone UI command drawer by removing duplicate effect-step controls and slideshow start/end controls.
- Added explicit first-slide and last-slide drawer controls.
- Replaced the ambiguous monitor-style blank/resume icon with a clearer blackout-style control.
- Added separate presentation and current-slide timers, plus a drawer toggle to pause/resume the displayed timers.
- Changed the jump-to-slide button from `#` text to an icon button.
- Bumped the extension, relay package, and project version to `0.7.3`.

## [0.7.2] - 2026-07-22

### Fixed

- Added explicit separators before Start/Stop Remote and after Remote Settings in the Impress Slide Show menu merge.
- Fixed Pylance diagnostics for the dynamic UNO clipboard `DataFlavor` struct used by the QR popup Copy URL action.
- Bumped the extension, relay package, and project version to `0.7.2`.

## [0.7.1] - 2026-07-22

### Changed

- Added install-facing OXT metadata with packaged icon and localized extension descriptions.
- Simplified Remote Settings into a settings-only dialog with mode selection and relay-only relay URL/resource controls.
- Replaced the settings Help text box with a static structured LibreOffice help dialog.
- Moved manual-link fallback to a Copy URL button in the QR pairing popup.
- Changed settings saves so changed settings stop a running remote and take effect on the next explicit Start Remote.
- Added `make refresh` and expanded `make clean` to remove the uv-managed venv and project cache.
- Bumped the extension, relay package, and project version to `0.7.1`.

## [0.7.0] - 2026-07-22

### Changed

- Removed the dual OXT product path: `make oxt` now builds one complete extension that includes the matching documentation, Python relay, and Cloudflare relay export bundles.
- Simplified LibreOffice remote settings to a single mode selector with Local network, Direct IPv6, Relay Server, and LocalTunnel modes.
- Changed the default route from Auto to Local network and made Start Remote obey the saved mode directly.
- Flattened the Impress Slide Show menu integration to direct Start/Stop Remote and Remote Settings actions.
- Relay URL and bundled relay/documentation export controls now appear only when Relay Server mode is selected.
- Added an in-product Help popup that explains the modes, pairing flow, and common failure paths.
- Product CI now builds and verifies the single versioned OXT artifact instead of separate relay-enabled/release bundle artifacts.
- Reorganized automated tests into grouped `tests/extension`, `tests/shared`, `tests/tools`, and `tests/relay` folders.
- Moved shared localization catalogs from the repository root into `shared/localizations`.
- Removed the source-only OXT packaging path so `make oxt` is the single extension build artifact.
- Removed installable PWA behavior from the phone UI, including web app manifest, service worker, icon assets, and matching local/relay routes.
- Consolidated relay, deployment, and compatibility documentation into `docs/relay.md` and removed duplicate/oversized legacy docs.
- Replaced scattered LibreOffice failure messages with a copyable diagnostic error popup for command and settings failures.
- Bumped the extension, relay package, and project version to `0.7.0`.

## [0.6.22] - 2026-07-22

### Added

- Added a vendored pure-Python LocalTunnel-compatible client for tunnel fallback without requiring Node.js or npm at LibreOffice runtime.
- Added `tunnel` as a first-class route that reuses the encrypted local/direct ECDH HTTP transport through a temporary public tunnel URL.
- Added LocalTunnel settings in LibreOffice Advanced Remote Settings, including tunnel enablement, tunnel host, requested subdomain, tunnel status, and tunnel-specific guidance.
- Added dual OXT build modes: the default OXT hides experimental relay UI/resources, while `make relay-oxt` builds an experimental relay-enabled OXT with Python relay and Cloudflare support preserved.

### Changed

- `make oxt` now builds the simpler local-plus-LocalTunnel default extension, and `make release-full` also builds the relay-enabled experimental OXT.
- Auto route selection now prefers local first, then LocalTunnel when local is unavailable, then direct IPv6, with relay kept for relay-enabled builds.
- Product CI now builds both default and relay-enabled OXT artifacts.
- Bumped the extension, relay package, and project version to `0.6.22`.

## [0.6.21] - 2026-07-22

### Fixed

- Fixed Pylance diagnostics in localization manifest tests and relay compatibility validation by narrowing dynamic JSON values before membership checks.

### Changed

- Bumped the extension, relay package, and project version to `0.6.21`.

## [0.6.20] - 2026-07-22

### Added

- Added dynamic localization discovery with generated `/localizations/manifest.json` for the extension local server, Python relay, Cloudflare/shared web bundles, and packaged OXT assets.
- Added `make localization-import` plus a translation import validator that checks locale tags, unknown keys, missing keys, and placeholder compatibility before writing catalogs.
- Added generated asset manifests with SHA-256 and SRI metadata for shared web UI assets, plus packaged SRI attributes for `app.css` and `app.js`.
- Added `make relay-compat` and a stdlib relay compatibility validator for checking third-party or self-hosted relay HTTP contracts.
- Added localization and relay compatibility documentation.

### Changed

- The phone UI now reads the localization manifest before choosing the browser locale, so adding supported languages no longer requires editing `shared/webui/app.js`.
- Bumped the extension, relay package, and project version to `0.6.20`.

### Documentation

- Added a user guide for local-first pairing, hotspot usage, route selection, and manual-link backup.
- Added a user-facing feature matrix that separates implemented behavior from planned work.
- Added an install/runtime troubleshooting guide for LibreOffice extension loading, stale caches, missing modules, menu visibility, QR/link, local pairing, Safari Web Crypto, and relay issues.
- Aligned architecture and security summaries around local encrypted mode, Safari local fallback, direct IPv6, and relay behavior.
- Added release-readiness policy covering route gates, target compatibility, latest-preview support, CI gates, manual release checks, and preview/beta blockers.

### Changed

- Expanded Product CI from smoke packaging to a release gate that installs test dependencies, runs lint and tests, builds the OXT, builds relay bundles, and verifies release artifacts.

## [0.6.19] - 2026-07-21

### Fixed

- Fixed Pylance diagnostics in local slide-preload status handling by validating the dynamic prewarm result before reading status fields.

### Changed

- Bumped the extension, relay package, and project version to `0.6.19`.

## [0.6.18] - 2026-07-21

### Added

- Added a versioned source-only OXT build that omits embedded relay and documentation resource bundles while keeping the installable extension code and shared phone web UI.
- Added `make source-oxt` and included the source-only OXT in `make release-full`.
- Added packaging tests for source-only OXT contents and side-by-side full/source OXT outputs.

### Changed

- Bumped the extension, relay package, and project version to `0.6.18`.

## [0.6.17] - 2026-07-21

### Added

- Added a phone-side presentation timer over the slide while the slideshow is running.
- Added a compact icon-only phone controls drawer for start from first slide, previous/next effect, last slide, blank/resume, end presentation, and jump-to-slide actions.
- Added local-mode full-deck preview prewarming through a bounded server-side PNG cache so slide changes can reuse already-exported previews.
- Added local preload status to the runtime connection payload for troubleshooting.

### Changed

- Expanded LibreOffice in-product guidance for same-Wi-Fi and phone-hotspot local pairing.
- Updated README, TODO, feature matrix, and release-readiness docs now that phone timer, richer phone controls, local guidance, and low-latency local prewarming are implemented.
- Bumped the extension, relay package, and project version to `0.6.17`.

## [0.6.16] - 2026-07-21

### Fixed

- Fixed Pylance diagnostics in the embedded local HTTP endpoint tests by making the fake controller injection and fake-only command assertions explicit.

### Changed

- Bumped the extension, relay package, and project version to `0.6.16`.

## [0.6.15] - 2026-07-21

### Added

- Added pure-Python P-256 ECDH support inside the LibreOffice extension runtime so encrypted transport does not depend on external Python cryptography packages.
- Added two-way ECDH `hello` negotiation: LibreOffice publishes an ephemeral plugin public key, the phone answers with an ephemeral phone public key, and both sides derive AES transport keys from the ECDH shared secret plus the QR pairing verifier.
- Added direct HTTP handshake completion over `POST /api/direct/handshake` before encrypted state, assets, or commands are exchanged.
- Added relay support for forwarding validated phone `hello` responses while keeping relay servers opaque and keyless.

### Changed

- Replaced the previous pre-shared-secret-only encrypted transport bootstrap with `ECDH-P256+HKDF-SHA256+AES-256-GCM`.
- Updated the shared phone UI to use browser Web Crypto ECDH and to keep multiple key generations so in-flight frames survive key rotation.
- Updated protocol, relay, local HTTP, and crypto tests for the two-leg ECDH handshake.
- Bumped the extension, relay package, and project version to `0.6.15`.

## [0.6.14] - 2026-07-21

### Added

- Added an encrypted embedded HTTP round-trip test that pairs as a phone client, decrypts direct state, decrypts a slide asset frame, and sends an encrypted command back to the extension server.
- Added `docs/test-before-release.md` with manual release-candidate steps for OXT installation, Impress UI integration, local and hotspot pairing, Safari fallback, direct IPv6, Python relay, Cloudflare relay, phone UI, localization, security, and release notes.

### Changed

- Updated release-readiness and TODO tracking so automated coverage, manual real-device release checks, and remaining browser/LibreOffice compatibility work are separated more clearly.
- Bumped the extension, relay package, and project version to `0.6.14`.

## [0.6.13] - 2026-07-21

### Added

- Added embedded local HTTP endpoint tests for the LibreOffice-served phone UI, direct encrypted state, local compatibility state, commands, slide assets, stale revisions, and response security headers.

### Changed

- Direct local/IPv6 `/api/direct/*` requests now require the unguessable pairing session id in the query string or `X-Impress-Remote-Session` header before they are treated as paired client activity.
- The shared phone UI now binds direct encrypted state, event, handshake, command, and slide-asset requests to the pairing session id from the QR/manual-link fragment.
- Direct and local compatibility slide endpoints now reject stale slide render revisions instead of returning a mismatched current slide image.
- Embedded local API and static responses now include no-sniff, no-referrer, frame-denial, and Content Security Policy headers.

### Security

- Restricted authenticated plaintext `/api/local/*` compatibility transport to local-network, link-local, or loopback clients.
- Added constant-time comparison for local compatibility session and pairing-secret headers.
- Added a JSON body size limit for local/direct command endpoints.

## [0.6.12] - 2026-07-21

### Added

- Added a Safari-compatible local-only phone transport fallback for browsers that do not expose Web Crypto on LAN HTTP origins.
- Added authenticated `/api/local/*` state, command, and slide-image endpoints gated by the pairing session id and pairing secret.

### Security

- Kept relay and direct IPv6 transport Web-Crypto-only, and kept the old unauthenticated `/api/state`, `/api/command`, `/api/events`, and `/api/slide/*` endpoints removed.
- Documented that the Safari local fallback is authenticated but plaintext, intended only for same-LAN compatibility when encrypted local transport is unavailable in the browser.

## [0.6.11] - 2026-07-21

### Changed

- Renamed the compiled extension artifact to include the centralized version number, for example `libreoffice-impress-remote-0.6.11.oxt`.
- Changed OXT packaging to build embedded relay and documentation archives in a temporary directory instead of leaving intermediate zip files and folders in `dist/`.
- Updated `make install-oxt` to install the versioned OXT filename.

## [0.6.10] - 2026-07-21

### Added

- Embedded the matching Cloudflare Worker relay archive inside the compiled `.oxt` alongside the Python relay and documentation archives.
- Added an Advanced Remote Settings action to export the bundled Cloudflare relay package from the installed extension.

## [0.6.9] - 2026-07-21

### Changed

- Centralized release versioning around the root `VERSION` file so OXT packaging, relay bundles, Cloudflare bundles, documentation bundles, and runtime package versions derive from one source.
- Made tool entrypoints import-safe when run directly as `python tools/build_oxt.py`, matching the Product CI command path.
- Packaged `description.xml` now receives the release version during OXT build instead of relying on a hand-edited source XML value.

### Fixed

- Fixed GitHub Product CI failing with `ModuleNotFoundError: No module named 'tools'` when invoking `python tools/build_oxt.py` directly.

## [0.6.8] - 2026-07-21

### Added

- Embedded the matching stripped Python relay-server release archive and documentation archive inside the `.oxt` package.
- Added Advanced Remote Settings actions to export the bundled relay server or documentation to a selected folder, falling back to the user's Downloads folder when folder selection is unavailable.
- Added safe packaged-resource extraction helpers with archive path validation.

### Changed

- Bumped the extension, relay package, and project version to `0.6.8`.

## [0.6.7] - 2026-07-21

### Changed

- Local and direct IPv6 phone routes now both use the encrypted `/api/direct/*` protocol path for state snapshots, server-sent events, commands, and slide assets.
- Updated phone-side encrypted transport messages so they refer to encrypted local/direct mode instead of direct IPv6 only.
- Updated protocol, security, architecture, roadmap, README, and TODO docs around local encrypted transport and the explicit local HTTP shell trust model.
- Bumped the extension, relay package, and project version to `0.6.7`.

### Security

- Removed the plaintext local `/api/state`, `/api/events`, `/api/command`, and `/api/slide/*` production endpoints from the embedded LibreOffice web server.
- Local mode now protects presenter notes, slide images, and remote commands with the same HKDF-SHA256 plus AES-256-GCM session profile, replay checks, session binding, and key rotation used by direct IPv6.

## [0.6.6] - 2026-07-21

### Added

- Added a LibreOffice upstream architecture note that separates core-candidate functionality from companion relay/deployment scope and maps extension seams to likely LibreOffice modules.
- Added phone UI PWA metadata, a service worker shell cache, and an installable app icon shared by the OXT, Python relay, and Cloudflare bundles.

### Changed

- Expanded architecture, compliance, roadmap, README, and TODO docs around the path from extension prototype to LibreOffice-core contribution.
- Added a visible phone-side connection recovery panel with localized retry/reload actions, stronger offline/error feedback, and improved focus styling.
- Bumped the extension, relay package, and project version to `0.6.6`.

## [0.6.5] - 2026-07-21

### Changed

- Moved the extension UI from a standalone top-level menu to an Impress-only Slide Show submenu using LibreOffice addon menu merging.
- Added supported toolbar merge entries for Start/Stop Remote and Advanced Remote Settings near LibreOffice's built-in slideshow controls in `standardbar`, `singlemode`, and `notebookbarshortcuts`.
- Bumped the extension, relay package, and project version to `0.6.5`.

## [0.6.4] - 2026-07-20

### Fixed

- Fixed LibreOffice extension registration by making `component.py` load localization lazily after the bundled extension `python/` directory has been added to `sys.path`.
- Bumped the extension, relay package, and project version to `0.6.4`.

## [0.6.3] - 2026-07-20

### Fixed

- Fixed remaining Pylance diagnostics in the vendored QR-code image helpers by replacing missing external drawer imports with local protocols and clarifying the dynamic PNG writer export.
- Bumped the extension, relay package, and project version to `0.6.3`.

## [0.6.2] - 2026-07-20

### Fixed

- Converted remaining vendored QR-code exception strings to localization keys.
- Fixed QR-code `make_image` typing so `None` defaults, missing PIL imports, and contextual drawer calls no longer trigger Pylance diagnostics.
- Bumped the extension, relay package, and project version to `0.6.2`.

## [0.6.1] - 2026-07-20

### Changed

- Converted remaining user/client-visible extension, relay, protocol, and mobile HTML fallback text to localization keys.
- Updated relay protocol errors so Python and Cloudflare relay deployments emit message keys that the phone UI can localize.
- Bumped the extension, relay package, and project version to `0.6.1`.

## [0.6.0] - 2026-07-20

### Added

- Added shared English and Turkish localization catalogs under `localizations/`.
- Added a Python localization loader for LibreOffice-side menu labels, dialogs, status text, and surfaced errors.
- Added phone UI localization loading with browser-language detection plus `?lang=` and `#lang=` testing overrides.

### Changed

- Converted user-facing LibreOffice and phone-remote strings to stable localization keys.
- Updated OXT, Python relay, and Cloudflare bundle packaging so shared localization files ship with the shared phone UI.
- Bumped the extension, relay package, and project version to `0.6.0`.

## [0.5.0] - 2026-07-17

### Added

- Added relay admission tokens to relay pairing links plus an admission-controlled `/api/session` endpoint for both the Python relay and the Cloudflare relay bundle.
- Added relay-session probing in the LibreOffice extension so joined relay phones can trigger the same auto-start behavior as local mode before the first remote command is pressed.
- Added relay tests covering asset-manifest delivery, admission-token enforcement, reconnect with fresh relay `hello` replay, and websocket rate limiting.

### Changed

- Hardened the Python relay with structured JSON logging, per-session metrics, rate limiting, session-cap enforcement, and send-failure cleanup.
- Brought the Cloudflare relay bundle up to the same shared-web-ui and admission-control model as the Python relay, including session status, replay behavior, and runtime limits.
- Expanded the relay documentation with deployment, firewall, reverse-proxy, trust-model, and verification guidance for both relay bundle variants.

### Security

- Relay websocket and session-status access now require the LibreOffice-generated admission token in addition to the encrypted pairing secret.
- Documented the current supported relay trust model as self-hosting the published bundle and verifying `asset-manifest.json` until a stronger frontend-pinning story exists.

## [0.4.1] - 2026-07-17

### Added

- Added a standalone Python relay bundle layout that ships only relay runtime files, bundled web assets, and helper scripts instead of mixing in the `.oxt` package and shared-source tree.
- Added relay runtime config helpers that can persist a randomly chosen free port for standalone and service installations.
- Added foreground `run-relay` helpers plus Linux systemd and Windows service install/uninstall scripts to the Python relay bundle.
- Added bundle and runtime tests covering the stripped relay archive shape and first-run config generation.

### Changed

- Refactored `make release-bundle` to produce a minimal Python relay artifact, while `make release-full` now combines `oxt`, `release-bundle`, and `cloudflare-bundle`.

## [0.4.0] - 2026-07-17

### Added

- Added a shared `shared/webui/` source tree so the phone remote UI is authored once and reused across the LibreOffice extension, the Python relay, and future companion implementations.
- Added `make release-bundle` to build a releasable bundle containing the `.oxt`, the self-hosted Python relay sources, and the shared mobile UI.
- Added `make cloudflare-bundle` to produce a Cloudflare Worker plus Durable Object relay bundle that serves the same shared UI.
- Added an OXT build regression test that verifies shared web assets are vendored into the extension package.

### Changed

- Refactored the extension and Python relay runtimes to load the shared mobile UI from a packaged `web/` directory when bundled and from `shared/webui/` during source development.
- Removed the duplicated authored web UI copies from `extension/web/` and `server/src/impress_remote_relay/web/`.
- Updated build tooling and repo metadata for the new shared-web and release-bundle layout.

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
