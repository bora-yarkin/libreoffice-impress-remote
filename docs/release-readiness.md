<!-- SPDX-FileCopyrightText: 2026 Bora Yarkın -->
<!-- SPDX-License-Identifier: GPL-3.0-only -->

# Release Readiness

This document defines what "ready to release" means while the project is still pre-1.0. It does not claim every planned feature is finished. Instead, it separates technical-preview releases from future beta/stable releases and gives each route its own acceptance gates.

## Current Release Posture

`0.6.16` is a pre-1.0 technical preview suitable for hands-on testing by the maintainer and early contributors.

It is not yet a stable end-user release because these important areas are still unfinished:

- Local HTTPS or signed/pinned frontend delivery is not implemented.
- Browser-level E2E coverage is still manual.
- LibreOffice runtime compatibility is not verified across a release matrix.
- Localization exists only for English and Turkish.
- Phone-side timer and richer mobile controls are not shipped.
- GitHub release creation is not automated yet.

## Support Policy

Until `1.0.0`, only the latest development snapshot is supported.

| Area | Current Policy |
| --- | --- |
| Supported extension version | Latest tagged or main-branch preview only. |
| Security fixes | Applied to the newest preview; no long-term maintenance branches yet. |
| Compatibility promise | Best-effort within the documented target matrix. |
| Breaking changes | Allowed before `1.0.0`, but protocol-breaking changes must bump the protocol version. |
| Relay compatibility | Best-effort for the current Python and Cloudflare relay bundles generated from the same version. |

## Target Compatibility Matrix

These are release targets, not proof that every cell is already verified.

| Component | Minimum Target | Release-Readiness Notes |
| --- | --- | --- |
| LibreOffice | 24.8 or newer | First realistic target for broad testing because it is recent and still representative of current UNO behavior. |
| macOS | macOS 13 or newer | Primary maintainer platform; local/hotspot flow should be verified here before each preview. |
| Windows | Windows 10 or newer | Extension install, menu registration, local listener, and relay export need manual verification. |
| Linux desktop | Current Ubuntu LTS or equivalent | Extension install, local listener, and Python relay service scripts need verification. |
| Phone browsers | Safari on current iOS, Chrome/Android, Firefox/Android | Safari local fallback, encrypted local mode, and relay mode should be checked separately. |
| Python relay | Python 3.11 or newer | Matches project packaging and CI test target. |
| Cloudflare relay | Current Cloudflare Workers runtime | Must deploy from the generated Cloudflare bundle without editing shared web UI assets. |

Older LibreOffice versions may work, but they are not release targets until someone verifies them and adds them to this matrix.

## Route Release Milestones

### Local Mode

Current maturity: closest to preview-ready.

Minimum gate for broader preview:

- install OXT on the maintainer machine
- open Impress, start remote, scan QR, and control a real slideshow
- verify current slide image and presenter notes update
- verify previous/next buttons and tap-to-advance
- verify phone hotspot flow
- verify Safari local compatibility fallback on LAN HTTP
- verify encrypted local mode in a Web-Crypto-capable browser
- verify stop/start remote behavior and QR popup lifecycle
- verify manual link backup

Minimum gate for beta:

- embedded local HTTP endpoint tests for encrypted direct state, encrypted commands, slide assets, fallback authentication, stale revisions, and browser security headers remain passing
- macOS, Windows, and Linux manual verification is recorded
- reconnect behavior is verified across slideshow start, stop, and document changes
- user-facing local and hotspot guidance exists in LibreOffice UI

### Direct IPv6 Mode

Current maturity: implemented fallback, needs broader network proof.

Minimum gate for broader preview:

- advertise only globally reachable IPv6 addresses
- self-test listener before offering the route
- fail gracefully when no public IPv6 is available
- verify encrypted state, command, and slide assets in at least one working IPv6 environment
- verify router/firewall guidance in Advanced Remote Settings

Minimum gate for beta:

- browser-level handshake and reconnect tests cover direct IPv6 behavior
- route fallback from Auto is verified on networks with and without usable IPv6
- documentation explains when direct IPv6 is worth trying and when relay/local is better

### Relay Mode

Current maturity: implemented optional fallback, self-hosting path is viable.

Minimum gate for broader preview:

- generated Python relay bundle runs without repository checkout
- generated Cloudflare relay bundle deploys without editing shared phone UI files
- LibreOffice connects as plugin and publishes encrypted state/assets
- phone connects as relay client and receives state/assets
- commands round-trip through the relay
- `/api/session` lets LibreOffice detect a joined phone
- relay never decrypts presenter notes, commands, or slide previews

Minimum gate for beta:

- VPS reverse-proxy/TLS guide is verified end to end
- Linux and Windows service helpers are manually tested
- relay replay, reconnect, admission-token, rate-limit, and cleanup tests remain passing in CI
- frontend-delivery trust limitation is explicitly accepted or mitigated by signed/pinned assets

## Current Automated Release Gates

Product CI should pass before publishing any preview artifact:

- install Python test dependencies
- compile extension, relay, test, and tool Python sources
- run Ruff lint
- run the full Python unit/integration test suite
- validate the extension manifest
- build the versioned `.oxt`
- verify the versioned `.oxt` exists
- build the Python relay bundle
- build the Cloudflare relay bundle
- verify both relay bundle archives exist
- upload the versioned `.oxt` artifact

GitHub Native Security should pass or have an explicitly documented exception:

- Dependency Review on pull requests
- CodeQL
- OpenSSF Scorecard on non-PR runs

## Manual Release Checklist

Use the full [Test Before Release](test-before-release.md) checklist before tagging a preview release. The shorter list below is the minimum summary gate.

Packaging:

- `make clean`
- `make venv`
- `make test`
- `make lint`
- `make oxt`
- `make release-full`
- confirm `dist/libreoffice-impress-remote-<version>.oxt` exists
- confirm the OXT contains matching Python relay, Cloudflare relay, and docs bundles
- install the generated OXT into LibreOffice

Local:

- open Impress, start remote, scan QR
- verify QR popup closes after phone connects
- verify slide image, notes, previous/next, tap-to-advance
- verify manual link backup
- verify Safari local fallback if testing on iOS
- verify stop remote tears down the route

Relay:

- export bundled Python relay from Advanced Remote Settings
- run relay locally or on a VPS
- configure relay URL in LibreOffice
- force Relay only
- scan relay QR and verify commands plus slide assets
- export and deploy the bundled Cloudflare relay when validating Cloudflare support
- verify direct IPv6 in a real public-IPv6 network, or record it as skipped with the network reason

Docs:

- README current status matches the feature matrix
- test-before-release results are recorded for every supported route that was tested
- TODO implemented/planned sections match reality
- changelog has an entry for the release
- troubleshooting covers any newly discovered install/runtime failure
- security docs mention any new trust-model limitations

## Release Blockers

Block a broader preview release if any of these are true:

- OXT cannot install cleanly in the maintainer's current LibreOffice.
- Local mode cannot pair and control a real Impress slideshow.
- Phone UI cannot show current slide and notes.
- Product CI fails.
- The packaged OXT omits the shared phone UI, localization catalogs, or bundled resources.
- Relay mode decrypts or stores presentation content server-side.
- Known security behavior differs from `docs/security/e2ee.md`.

Block a beta/stable release if any of these are true:

- no Windows or Linux manual verification exists
- no browser-level E2E coverage exists for core phone UI behavior
- no recorded test-before-release results exist for local, direct IPv6, and relay target routes
- localization expansion has no import workflow
- local frontend trust decisions are still unresolved

## Release Naming

Before `1.0.0`, use preview language:

- `0.x.y technical preview`
- `0.x.y maintainer preview`
- `0.x.y relay preview`

Do not call the project "stable" until the beta/stable blockers above are resolved.
