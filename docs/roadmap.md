<!-- SPDX-FileCopyrightText: 2026 Bora Yarkın -->
<!-- SPDX-License-Identifier: GPL-3.0-only -->

# Roadmap

This roadmap reflects the `1.0.1` snapshot.

This is a volunteer FOSS extension. It may move quickly when someone has time and may sit quietly when nobody does. The docs should not promise a paid-product support cadence, guaranteed long-term maintenance, or future platform ports.

## Product Direction

The project stays extension-first:

- Local network mode is the default, tested, and recommended path.
- Phone hotspot support matters because it solves many same-room cases without external infrastructure.
- Local mode is the released main path.
- LocalTunnel, Direct IPv6, and Relay Server modes are experimental fallbacks.
- The phone UI stays lightweight and settings-free.
- LibreOffice owns mode selection, pairing, help, and troubleshooting.
- Relay and tunnel behavior must never become mandatory for the local workflow.

Future work may include other office suites, browser integrations, or deeper LibreOffice distribution paths if someone volunteers to build and maintain them. None of that is guaranteed.

## Milestones

### M1 - Broaden Local Mode Evidence

Status: local mode has been tested by the maintainer and is the `1.0.0` release path.

- Record same-Wi-Fi and hotspot pairing results on macOS, Windows, and Linux.
- Verify iOS Safari, Android Chrome, and Android Firefox behavior.
- Harden reconnect behavior across start, stop, slideshow transitions, and document switches.
- Keep local HTTP endpoint coverage passing.
- Keep user-facing local/hotspot guidance accurate in LibreOffice and docs.

Exit criteria: a normal user can install the OXT, start the remote, scan a QR code, and control a real slideshow locally without reading implementation docs.

### M2 - Make Releases Trustworthy

Status: in progress

- Keep GitHub release automation working after CI passes.
- Keep the OXT versioned and self-contained.
- Keep documentation bundled inside the OXT.
- Keep release notes honest about what was actually tested.
- Keep security fixes best-effort and latest-release-only until the project has enough maintainer capacity for more.

Exit criteria: a release can be built, installed, tested locally, and explained clearly.

### M3 - Product QA And Accessibility

Status: in progress

- Add browser-level E2E automation for phone UI behavior.
- Record a small but real LibreOffice/runtime compatibility matrix.
- Verify accessibility: keyboard navigation, focus order, screen-reader labels, QR/Copy URL fallback, and status feedback.
- Keep `docs/test-before-release.md` useful rather than ceremonial.

Exit criteria: release readiness is based on recorded evidence, not only unit tests.

### M4 - Localization And Help

Status: in progress

- Expand beyond English and Turkish only after source strings settle.
- Keep every user-facing string keyed.
- Add polished Help content for Local network mode, hotspot setup, and common errors.
- Keep docs and UI language plain enough for non-developers.

Exit criteria: the extension feels understandable to normal Impress users, not only project contributors.

### M5 - Security And Frontend Trust

Status: in progress

- Keep ECDH/AES-GCM local/direct/tunnel/relay protocol tests passing.
- Improve frontend trust for local HTTP and relay-hosted UI delivery.
- Decide between local HTTPS, signed assets, pinned assets, or a trusted phone shell.
- Keep Safari local fallback clearly documented as authenticated plaintext, not E2EE.

Exit criteria: the security model is honest, testable, and good enough for the documented local-first scope.

### M6 - Experimental Routes

Status: implemented, needs field testing

- Keep LocalTunnel, Direct IPv6, Python relay, and Cloudflare relay available for users who want to test them.
- Keep relay bundles version-matched with the OXT.
- Keep relay logs free of decrypted slide content, notes, commands, and image data.
- Keep experimental route docs clear about limits, risks, and setup complexity.

Exit criteria: advanced users can try experimental routes without confusing them with the main local workflow.

## Definition Of Success

The project succeeds when:

- local mode is excellent
- hotspot use is easy to understand
- the extension is small enough to install and explain
- optional fallback modes do not confuse the main flow
- localization and accessibility are treated seriously
- the docs are honest about volunteer maintenance and experimental features
