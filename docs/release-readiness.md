<!-- SPDX-FileCopyrightText: 2026 Bora Yarkın -->
<!-- SPDX-License-Identifier: GPL-3.0-only -->

# Release Readiness

This document defines what "ready to release" means for a volunteer extension. It is deliberately practical: local mode is the released product path, while LocalTunnel, Direct IPv6, and relay modes are experimental fallbacks.

## Current Release Posture

`1.0.0` is the first local-mode release.

Local mode has been tested by the maintainer and works in the current development environment. That does not mean every LibreOffice version, operating system, router, phone browser, or corporate network is covered.

Still unfinished after `1.0.0`:

- broader local-mode compatibility evidence across macOS, Windows, Linux, iOS, and Android
- browser-level E2E coverage for the phone UI
- accessibility verification
- local HTTPS, signed assets, pinned assets, or an equivalent frontend-trust improvement
- broader post-release compatibility evidence

Experimental and not part of the main release promise:

- LocalTunnel mode
- Direct IPv6 mode
- Python relay mode
- Cloudflare relay mode

## Volunteer Support Policy

This is a FOSS project maintained as volunteer time allows.

| Area | Current Policy |
| --- | --- |
| Supported extension version | Latest tagged release or main-branch snapshot only. |
| Security fixes | Best-effort on the newest release; no long-term maintenance branches. |
| Compatibility promise | No guarantee. Recorded compatibility means "tested there", not "supported forever". |
| Breaking changes | Avoided in the main local path when practical; protocol-breaking changes must bump the protocol version. |
| Experimental routes | Best-effort only. They may change, break, or remain lightly tested. |

## Target Compatibility Matrix

These are testing targets, not promises.

| Component | Target | Notes |
| --- | --- | --- |
| LibreOffice | 24.8 or newer | Start with current LibreOffice behavior and expand only when someone tests older versions. |
| macOS | macOS 13 or newer | Primary maintainer platform. |
| Windows | Windows 10 or newer | Needs manual extension install and local-mode verification. |
| Linux desktop | Current Ubuntu LTS or equivalent | Needs manual extension install and local-mode verification. |
| Phone browsers | Current iOS Safari, Android Chrome, Android Firefox | Local mode and hotspot behavior matter most. |
| Experimental relay | Python 3.11+ or current Cloudflare Workers runtime | Useful for advanced testing, not part of the main local-mode promise. |

## Main Release Gate

The main release is local-first. Do not block it on LocalTunnel, Direct IPv6, or relay maturity.

Local mode must satisfy:

- OXT installs cleanly in the maintainer's current LibreOffice.
- Impress shows `Slide Show -> Start Remote` and `Slide Show -> Remote Settings`.
- Start Remote opens the QR popup.
- A phone can scan the QR and control a real slideshow.
- Current slide image and presenter notes update.
- Previous, next, tap-to-advance, first slide, last slide, goto-slide, fullscreen, and timers work.
- Phone hotspot pairing works.
- iOS Safari local compatibility fallback works on a trusted LAN or hotspot.
- Stop Remote tears down the listener.
- Copy URL works as QR fallback.
- Product CI passes.
- Documentation describes the tested local flow accurately.

## Experimental Route Gates

These routes can ship in releases, but keep them labeled experimental unless they have real field-test notes.

LocalTunnel:

- tunnel starts and returns a public URL
- QR opens through the tunnel
- encrypted state, slide assets, and commands work
- Stop Remote closes the tunnel
- provider failures are understandable

Direct IPv6:

- only global IPv6 addresses are advertised
- listener self-test passes before showing the route
- unavailable IPv6 reports useful router/firewall/network guidance
- encrypted state, slide assets, and commands work on at least one real public-IPv6 network

Relay:

- Python relay bundle runs without a repository checkout
- Cloudflare relay bundle deploys without editing shared phone UI files
- LibreOffice and phone connect through the relay
- commands round-trip
- relay never decrypts presenter notes, commands, or slide previews
- relay frontend-delivery trust limitations remain documented

## Automated Release Gates

Before publishing a release artifact:

- install Python test dependencies
- compile extension, relay, test, and tool Python sources
- run Ruff lint
- run the full Python unit/integration test suite
- build the versioned `.oxt`
- verify the versioned `.oxt` output exists
- upload the versioned `.oxt` artifact in CI

GitHub Native Security should pass or have an explicitly documented exception:

- Dependency Review on pull requests
- CodeQL
- OpenSSF Scorecard on non-PR runs

## Repository Security And Branch Protection

The repository includes Product CI, Dependency Review, CodeQL for Python and GitHub Actions, OpenSSF Scorecard, Dependabot, and CODEOWNERS.

Recommended `main` protection:

- require pull request before merge
- require CODEOWNERS review
- require status checks
- require branches to be up to date before merge
- require conversation resolution
- block force pushes
- block deletions
- require signed commits when practical

Recommended required checks:

```text
Product CI / Build And Smoke Test
GitHub Native Security / CodeQL
GitHub Native Security / OpenSSF Scorecard
```

If GitHub code scanning is disabled for the repository, CodeQL SARIF upload may fail until code scanning is enabled in repository settings.

## Manual Release Checklist

Use the full [Test Before Release](test-before-release.md) checklist before tagging a release. The shorter list below is the minimum summary gate.

Packaging:

- `make clean`
- `make venv`
- `make test`
- `make lint`
- `make oxt`
- confirm `dist/libreoffice-impress-remote-<version>.oxt` exists
- confirm the OXT contains matching Python relay, Cloudflare relay, and docs bundles
- install the generated OXT into LibreOffice

Local:

- open Impress, start remote, scan QR
- verify QR popup closes after phone connects
- verify slide image, notes, previous/next, tap-to-advance, timers, fullscreen, first/last slide, and goto-slide
- verify Copy URL backup from the QR popup
- verify Safari local fallback if testing on iOS
- verify phone hotspot workflow
- verify stop remote tears down the route

Experimental:

- test LocalTunnel, Direct IPv6, Python relay, and Cloudflare relay when possible
- record skipped experimental routes with the reason
- do not present untested experimental routes as proven

Docs:

- README current status matches the feature matrix
- test-before-release results are recorded
- TODO implemented/planned sections match reality
- changelog has an entry for the release
- troubleshooting covers any newly discovered install/runtime failure
- security docs mention any new trust-model limitations

## Release Blockers

Block a release if any of these are true:

- OXT cannot install cleanly in the maintainer's current LibreOffice.
- Local mode cannot pair and control a real Impress slideshow.
- Phone UI cannot show current slide and notes.
- Product CI fails.
- The packaged OXT omits the shared phone UI, localization catalogs, documentation, or bundled resources.
- Known security behavior differs from `docs/security/e2ee.md`.

## Release Naming

Use plain release language for the main local-mode extension:

- `1.0.0`
- `1.x.y`

Keep experimental route notes explicit in release notes when LocalTunnel, Direct IPv6, or relay behavior changes.
