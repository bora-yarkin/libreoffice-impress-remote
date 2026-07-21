<!-- SPDX-FileCopyrightText: 2026 Bora Yarkın -->
<!-- SPDX-License-Identifier: GPL-3.0-only -->

# LibreOffice Upstream Architecture

This note defines what should become a LibreOffice feature and what should stay outside LibreOffice core.

The goal is not to upstream the current Python extension as-is. The extension is the proving ground. A LibreOffice contribution should be smaller, local-first, easier to review, and aligned with the existing Impress, framework, configuration, localization, help, and QA systems.

## Upstream Candidate Scope

The first LibreOffice-core candidate should include:

- local LAN presenter remote for Impress
- QR pairing from LibreOffice UI
- current slide preview, presenter notes, slide count, current index, and timer state
- next, previous, start, end, and basic slideshow commands
- local-first route guidance for same-Wi-Fi and hotspot workflows
- LibreOffice-native settings storage
- LibreOffice-native menu, toolbar, notebookbar, help, localization, accessibility, and QA integration
- a documented transport-neutral state and command contract

Direct IPv6 is a secondary candidate. It should only move upstream after local mode is accepted as maintainable and after the UI can explain when IPv6 is useful.

## Companion Scope

These pieces should remain outside LibreOffice core:

- reference Python relay server
- Cloudflare Worker relay bundle
- VPS, reverse-proxy, TLS, firewall, and service-install scripts
- public tunnel integrations
- optional non-LibreOffice adapters for future browser, PowerPoint, or cross-suite work

LibreOffice core may keep protocol compatibility with a self-hosted relay, but it should not require or operate a hosted relay service.

## Current Extension Seams

The current extension maps to future core work like this:

| Extension Area | Current Files | Future LibreOffice Surface |
| --- | --- | --- |
| Menu and toolbar integration | `extension/Addons.xcu`, `component.py` | `sd/uiconfig/simpress/menubar/`, Impress toolbars, notebookbar UI definitions |
| UNO dispatch entry point | `component.py` | Sfx/UNO command implementations in Impress or framework dispatch |
| Presentation state | `controller.py`, `preview.py` | Impress slideshow/controller APIs and preview export helpers |
| Local web server | `local_server.py` | Core-owned local listener or an approved internal service boundary |
| Pairing and QR | `office_ui.py`, `qr.py` | Impress dialog/sidebar UI plus bundled QR rendering approach |
| Settings | `Settings.xcs`, `Settings.xcu`, `config.py` | `officecfg` schema and LibreOffice options/config migration |
| Phone UI | `shared/webui/` | Bundled static resource owned by LibreOffice, translated through LibreOffice localization workflow |
| Protocol | `protocol.py`, `crypto.py` | Versioned core protocol contract with tests and compatibility docs |
| Relay client | `relay_client.py` | Optional follow-up or companion bridge boundary, not a first upstream blocker |

## Proposed Patch Strategy

1. Introduce a minimal local-mode state and command service for Impress.
2. Add current slide preview and presenter notes retrieval through existing Impress APIs.
3. Add the local web resource delivery path with a small static phone UI.
4. Add QR pairing and a LibreOffice-native start/stop UI under Slide Show.
5. Add settings through `officecfg` and keep defaults local-first.
6. Add tests for state extraction, command dispatch, packaging/resource delivery, and basic browser contract.
7. Add help and localization entries only after labels and flows stabilize.
8. Consider direct IPv6 as a follow-up patch series.
9. Keep relay compatibility out of the first core patch unless reviewers explicitly want the protocol hook.

Each patch should be reviewable alone. A giant "remote control feature" patch is too hard to review and too easy to reject.

## Review Risks To Reduce First

- Avoid depending on Python implementation details in the upstream design.
- Avoid bundled third-party services or cloud assumptions.
- Avoid adding mandatory network listeners without clear user action and settings.
- Avoid storing or logging notes, slide images, relay payloads, or pairing secrets.
- Avoid making relay support necessary for the main user story.
- Avoid UI that bypasses LibreOffice localization, help, accessibility, or command patterns.
- Avoid private OS automation for slideshow control.

## Acceptance Bar

Before attempting a core proof of concept, the extension should demonstrate:

- reliable local pairing on macOS, Windows, and Linux
- clear same-Wi-Fi and hotspot instructions in the LibreOffice UI
- stable state and command protocol tests
- packaged-resource tests for the phone UI
- no hard-coded user-facing strings outside localization catalogs
- documented security behavior for local mode
- a clean split between local/direct core behavior and relay companion behavior

## Long-Term End State

The desired end state is:

- LibreOffice core owns local presenter remote UX for Impress.
- Direct IPv6 may be owned by LibreOffice if it remains useful and maintainable.
- The self-hosted relay remains a FOSS companion for hard networks.
- The extension either becomes a staging channel for experimental features or is sunset once equivalent core functionality ships.
