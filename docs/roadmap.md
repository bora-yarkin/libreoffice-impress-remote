<!-- SPDX-FileCopyrightText: 2026 Bora Yarkın -->
<!-- SPDX-License-Identifier: GPL-3.0-only -->

# Roadmap

This roadmap turns the project goals into a concrete delivery plan.

It reflects the repository state as of `2026-07-22` and the current `0.7.6` snapshot.

## Product Direction

The long-term goal is:

- a FOSS presenter remote for LibreOffice Impress
- no mandatory third-party relay or tunnel service
- no mandatory local install beyond LibreOffice itself for the main local workflow
- optional self-hosted relay support for hard networks such as CGNAT and hostile Wi-Fi
- an architecture that can eventually move from extension prototype to LibreOffice core

In practice, local mode should solve most same-room use cases, including normal Wi-Fi and many phone hotspot setups. Direct IPv6 and relay support are important fallback paths, but they should not define the main product experience.

## Hard Rules

- Do not make a public tunnel service such as LocalTunnel, ngrok, or similar a required product dependency.
- Do not require a vendor-hosted cloud service for core functionality.
- Keep local mode as the primary path users are expected to try first.
- Keep direct IPv6 and relay available as fallback paths, not as the default story.
- Keep the relay optional, self-hostable, and protocol-compatible with alternative implementations.
- Keep the phone UI lightweight and settings-free.
- Keep transport and pairing policy inside LibreOffice UI.
- Keep cross-platform support in mind for macOS, Windows, and Linux.

## Scope Split

The project should distinguish between what is a realistic LibreOffice core candidate and what is better kept as a companion component.

### Strong LibreOffice Core Candidates

- local LAN remote control
- QR pairing and pairing route selection
- presenter notes and slide preview generation
- LibreOffice-native settings UI
- localization, accessibility, help, and QA coverage
- transport-neutral command and state protocol definitions

### Secondary Core Candidates

- direct IPv6 remote control, once local mode is considered complete and trustworthy

### Likely Companion Project Scope

- optional self-hosted relay server
- deployment recipes for VPS, reverse proxy, TLS, and firewalling
- optional protocol bridge implementations in other languages

### Explicit Non-goal

- a LibreOffice-operated hosted relay service

## Milestones

### M0 - Prototype Baseline Completed

Status: completed in `0.2.0`

What exists now:

- local embedded HTTP server
- QR-first LibreOffice dialog
- lightweight phone remote
- direct IPv6 prototype path
- optional relay prototype
- current slide rendering and presenter state
- route selection in LibreOffice

This is the base for the remaining work, not the finish line.

### M1 - Local Mode Complete

Status: in progress after `0.7.6`

Target outcome:

- local mode is the default recommended user path
- users on the same network can reliably pair and control presentations
- local mode is usable without touching relay settings

Main work:

- add local embedded server endpoint coverage
- expand same-Wi-Fi and hotspot guidance in LibreOffice and user-facing docs
- harden slide-state refresh and reconnect behavior across start, stop, and slideshow transitions
- confirm behavior on current LibreOffice versions across macOS, Windows, and Linux

Repository focus:

- `extension/python/impress_remote/local_server.py`
- `extension/python/impress_remote/controller.py`
- `shared/webui/`
- `tests/`
- `docs/`

Exit criteria:

- a user can install the extension, start the remote, scan a QR code, and control a presentation locally without manual troubleshooting
- local mode has clear documentation and regression coverage

### M2 - LibreOffice-quality UX, Guidance, Localization, and Accessibility

Status: in progress after `0.7.6`

Target outcome:

- the feature feels like LibreOffice software, not a sidecar prototype
- local mode is understandable without reading external docs
- users get explicit in-product guidance for same-Wi-Fi and hotspot use before they reach for fallback routes

Main work:

- continue expanding the initial English and Turkish catalogs with the localization import workflow
- keep menu labels, dialog copy, status text, errors, and help text aligned with translation keys
- extend keyboard, focus, and status-feedback verification across supported desktop platforms
- add LibreOffice help and troubleshooting content
- confirm package behavior and UI quality across supported desktop platforms
- expand the LibreOffice UI guidance around the recommended local-first and hotspot-friendly usage flow

Repository focus:

- `extension/python/impress_remote/office_ui.py`
- LibreOffice configuration and metadata files under `extension/`
- `shared/webui/`
- `docs/`

Exit criteria:

- the extension is ready for broader community testing
- localization is no longer blocked on hard-coded strings
- users can understand the recommended workflow directly from LibreOffice

### M3 - Protocol and Security Foundation

Status: in progress after `0.7.6`

Target outcome:

- the transport protocol is versioned and no longer implicit
- local, direct, and relay paths can share one protocol contract
- plaintext relay forwarding is removed from the production path

Current baseline:

- relay transport now uses versioned `hello`, `frame`, and `error` messages
- relay state, command, and error frames now use ECDH P-256, HKDF-SHA256, and AES-GCM
- relay sessions now enforce replay protection, session binding, and plugin-driven key rotation
- direct IPv6 and Web-Crypto-capable local mode now use the same session-bound encrypted state, command, and slide-asset protocol profile, while local Safari-style LAN browsers can fall back to LAN-only authenticated plaintext `/api/local/*` polling
- the current relay protocol is documented tightly enough for compatible implementations to start from it

Remaining work:

- expand browser and LibreOffice compatibility evidence for the ECDH P-256 handshake
- document previews and richer future frame kinds without fragmenting interoperability
- update the threat model and operational guidance around trusted frontend delivery

Repository focus:

- `extension/python/impress_remote/protocol.py`
- `extension/python/impress_remote/crypto.py`
- `extension/python/impress_remote/relay_client.py`
- `server/src/impress_remote_relay/`
- `docs/security/e2ee.md`

Exit criteria:

- relay mode no longer requires trusting the relay with slide notes or commands
- the protocol is documented tightly enough that another implementation could interoperate

### M4 - Optional Direct IPv6 Hardening

Status: completed in the current repository snapshot after `0.7.6`

Target outcome:

- direct IPv6 becomes a reliable fallback when local mode does not work

Current baseline:

- only globally reachable IPv6 addresses are advertised for direct pairing
- the direct IPv6 listener self-tests its own advertised addresses before the route is offered
- Direct IPv6 mode only offers a pairing link when the route is actually usable
- the LibreOffice dialog now surfaces router, firewall, and hotspot guidance for direct IPv6 failures
- the direct IPv6 phone route now uses the same encrypted session profile as relay transport

Repository focus:

- `extension/python/impress_remote/network.py`
- `extension/python/impress_remote/local_server.py`
- `extension/python/impress_remote/config.py`
- `docs/architecture.md`

Exit criteria:

- users with usable IPv6 can pair directly without relay setup
- users without usable IPv6 get clear route guidance instead of silent failure

### M5 - Optional Self-hosted Relay Viable

Status: completed in `0.5.0`

Target outcome:

- the project can cross CGNAT and bad Wi-Fi without depending on a third-party service
- the relay is optional and self-hostable by advanced users or organizations

Current baseline:

- relay sessions now support admission-controlled join plus session-status probing
- LibreOffice can detect joined relay phones and auto-start the slideshow
- the reference Python relay and the Cloudflare bundle both serve the shared phone UI
- both reference deployments now expose deployment-health and session-status endpoints
- relay reconnect, replay, rate limits, and structured operational logging are implemented in the reference relay deployments

Main work:

- keep the relay protocol open so the reference server is replaceable as other implementations appear

Repository focus:

- `server/`
- `extension/python/impress_remote/relay_client.py`
- `docs/relay.md`
- `docs/architecture.md`

Exit criteria:

- a user can run the reference relay on their own VPS and use it without patching the product
- relay deployment is documented well enough for non-authors

### M6 - Upstream Preparation

Status: completed in the current repository snapshot after `0.7.6`

Target outcome:

- the project has a clear, realistic path into LibreOffice itself

Completed baseline:

- upstream candidate scope is now explicit
- relay and deployment assets are documented as companion scope
- extension seams are mapped to likely LibreOffice surfaces
- an upstream patch strategy exists in `docs/libreoffice-upstream-architecture.md`

Remaining follow-up work:

- reduce extension-specific assumptions that would be awkward in core
- expand compatibility testing and user-facing docs

Repository focus:

- architecture and compliance docs first
- then a parallel design/prototype effort against LibreOffice core

Exit criteria:

- there is a documented patch strategy, not just a feature wish
- the project can explain what belongs in LibreOffice core and what remains companion infrastructure

### M7 - LibreOffice Core Proof of Concept

Target outcome:

- the core candidate subset works inside LibreOffice without depending on this extension

Main work:

- port the local/direct client-facing functionality into LibreOffice core
- keep the first proof of concept local-first instead of making fallback transports a merge blocker
- integrate settings, menu actions, localization, and help in the normal LibreOffice way
- preserve protocol compatibility where possible so the optional self-hosted relay can remain usable
- gather reviewer feedback early and narrow scope if necessary

Expected upstream surface:

- an initial patch series should focus on local mode first
- direct IPv6 can follow as a smaller, optional follow-up if it still proves useful
- relay support may need to remain optional, minimized, or deferred depending on reviewer feedback

Exit criteria:

- a core implementation exists and is reviewable
- the user story works in LibreOffice without installing the extension

### M8 - Upstream Submission and Long-term Maintenance

Target outcome:

- the feature is maintained as a real LibreOffice contribution rather than a long-lived forked experiment

Main work:

- submit patch series to LibreOffice Gerrit
- address review, QA, translation, and help feedback
- split changes into mergeable increments rather than one giant patch
- keep the extension as a staging ground only while core work is incomplete
- plan migration or sunset paths once core functionality lands

Exit criteria:

- the feature has either merged upstream or has a clearly scoped, actively reviewed upstream branch of work

## Immediate Priorities For This Repository

The next practical order for this repo should be:

1. Expand browser and LibreOffice runtime compatibility checks across supported versions and desktop platforms.
2. Expand LibreOffice-side guidance, localization packaging, and cross-platform accessibility verification around the local-first workflow.
3. Harden frontend trust around local HTTP, relay-hosted UI delivery, and signed or pinned shared assets.
4. Add local embedded server endpoint coverage and broader end-to-end local/direct test coverage.
5. Harden self-hosted relay lifecycle and deployment docs as an optional fallback.
6. Reduce extension-specific assumptions before attempting a larger LibreOffice-core proof of concept.

## Decision Policy For Public Tunnel Services

Public tunnel services can still be useful for debugging, demos, or temporary developer workflows.

They should not be:

- the documented primary remote path
- a required dependency for users
- embedded into the product as a vendor-specific integration
- treated as the answer to CGNAT in the long-term roadmap

If a tunnel service is mentioned in documentation at all, it should be labeled as temporary developer tooling.

## Definition Of Success

This project is successful when:

- local mode is excellent
- local mode covers most real same-room cases, including many hotspot setups
- direct IPv6 works where it should, when fallback connectivity is needed
- difficult networks are solved by an optional self-hosted relay, not by a mandatory third-party service
- the security model is honest and documented
- localization and accessibility are first-class
- the core candidate subset is realistic enough to upstream into LibreOffice

The most realistic end state is:

- LibreOffice core owns the user-facing local and direct remote experience
- a separate FOSS companion relay server remains available for users who need internet traversal

That preserves the no-third-party-service goal without pretending that CGNAT can be solved with no relay at all.
