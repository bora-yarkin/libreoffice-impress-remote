<!-- SPDX-FileCopyrightText: 2026 Bora Yarkın -->
<!-- SPDX-License-Identifier: GPL-3.0-only -->

# Roadmap

This roadmap turns the project goals into a concrete delivery plan.

It reflects the repository state as of `2026-07-16` and the current `0.2.0` snapshot.

## Product Direction

The long-term goal is:

- a FOSS presenter remote for LibreOffice Impress
- no mandatory third-party relay or tunnel service
- no mandatory local install beyond LibreOffice itself for local and direct modes
- optional self-hosted relay support for hard networks such as CGNAT and hostile Wi-Fi
- an architecture that can eventually move from extension prototype to LibreOffice core

## Hard Rules

- Do not make a public tunnel service such as LocalTunnel, ngrok, or similar a required product dependency.
- Do not require a vendor-hosted cloud service for core functionality.
- Keep local mode and direct mode first-class, not fallback features.
- Keep the relay optional, self-hostable, and protocol-compatible with alternative implementations.
- Keep the phone UI lightweight and settings-free.
- Keep transport and pairing policy inside LibreOffice UI.
- Keep cross-platform support in mind for macOS, Windows, and Linux.

## Scope Split

The project should distinguish between what is a realistic LibreOffice core candidate and what is better kept as a companion component.

### Strong LibreOffice Core Candidates

- local LAN remote control
- direct IPv6 remote control
- QR pairing and pairing route selection
- presenter notes and slide preview generation
- LibreOffice-native settings UI
- localization, accessibility, help, and QA coverage
- transport-neutral command and state protocol definitions

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

Target outcome:

- local mode is the default recommended user path
- users on the same network can reliably pair and control presentations
- local mode is usable without touching relay settings

Main work:

- document the local HTTP trust model and whether HTTPS will be supported
- add better mobile error states, retry states, and accessibility polish
- add local embedded server endpoint coverage
- harden slide-state refresh and reconnect behavior across start, stop, and slideshow transitions
- confirm behavior on current LibreOffice versions across macOS, Windows, and Linux

Repository focus:

- `extension/python/impress_remote/local_server.py`
- `extension/python/impress_remote/controller.py`
- `extension/web/`
- `tests/`
- `docs/`

Exit criteria:

- a user can install the extension, start the remote, scan a QR code, and control a presentation locally without manual troubleshooting
- local mode has clear documentation and regression coverage

### M2 - Protocol and Security Foundation

Target outcome:

- the transport protocol is versioned and no longer implicit
- local, direct, and relay paths can share one protocol contract
- plaintext relay forwarding is removed from the production path

Main work:

- define a versioned protocol for commands, state, previews, errors, and negotiation
- implement ECDH P-256 key exchange
- implement HKDF-SHA256 session derivation
- implement AES-GCM encrypted frames
- add replay protection, session binding, and key rotation rules
- update the threat model and operational guidance

Repository focus:

- `extension/python/impress_remote/protocol.py`
- `extension/python/impress_remote/crypto.py`
- `extension/python/impress_remote/relay_client.py`
- `server/src/impress_remote_relay/`
- `docs/security/e2ee.md`

Exit criteria:

- relay mode no longer requires trusting the relay with slide notes or commands
- the protocol is documented tightly enough that another implementation could interoperate

### M3 - Direct IPv6 Production Ready

Target outcome:

- direct IPv6 becomes a real second path, not just a prototype route toggle

Main work:

- detect globally reachable IPv6 addresses instead of only non-link-local candidates
- add reachability checks and route health hints
- teach auto mode to prefer usable routes, not merely configured routes
- document IPv6 caveats for routers, hotspots, captive portals, and firewalls
- secure direct IPv6 with the same protocol profile used elsewhere

Repository focus:

- `extension/python/impress_remote/network.py`
- `extension/python/impress_remote/local_server.py`
- `extension/python/impress_remote/config.py`
- `docs/architecture.md`

Exit criteria:

- users with usable IPv6 can pair directly without relay setup
- users without usable IPv6 get clear route guidance instead of silent failure

### M4 - Optional Self-hosted Relay Viable

Target outcome:

- the project can cross CGNAT and bad Wi-Fi without depending on a third-party service
- the relay is optional and self-hostable by advanced users or organizations

Main work:

- add session creation, join, reconnect, and resume behavior
- harden cleanup, backpressure, rate limits, and observability
- publish deployment documentation for Docker, reverse proxy, TLS, DNS, and firewall rules
- document the policy that public tunnel services are debug-only, not product dependencies
- keep the relay protocol open so the reference server is replaceable

Repository focus:

- `server/`
- `extension/python/impress_remote/relay_client.py`
- `docs/relay-server.md`
- `docs/architecture.md`

Exit criteria:

- a user can run the reference relay on their own VPS and use it without patching the product
- relay deployment is documented well enough for non-authors

### M5 - LibreOffice-quality UX, Localization, and Accessibility

Target outcome:

- the feature feels like LibreOffice software, not a sidecar prototype

Main work:

- move strings into a localization-friendly workflow
- align menu labels, dialog copy, status text, and errors for translation
- improve keyboard behavior, focus order, and readable status feedback
- add LibreOffice help and troubleshooting content
- confirm package behavior and UI quality across supported desktop platforms

Repository focus:

- `extension/python/impress_remote/office_ui.py`
- LibreOffice configuration and metadata files under `extension/`
- `extension/web/`
- `docs/`

Exit criteria:

- the extension is ready for broader community testing
- localization is no longer blocked on hard-coded strings

### M6 - Upstream Preparation

Target outcome:

- the project has a clear, realistic path into LibreOffice itself

Main work:

- define the upstream candidate scope explicitly:
  - local mode
  - direct IPv6 mode
  - pairing and QR flow
  - presenter state and controls
  - LibreOffice-native configuration
- identify what stays outside core:
  - reference relay server
  - deployment assets
- reduce extension-specific assumptions that would be awkward in core
- write an upstream design note mapping this feature to LibreOffice modules such as `sd/`, `svx/`, `framework/`, `officecfg/`, and help content
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
- integrate settings, menu actions, localization, and help in the normal LibreOffice way
- preserve protocol compatibility where possible so the optional self-hosted relay can remain usable
- gather reviewer feedback early and narrow scope if necessary

Expected upstream surface:

- an initial patch series should focus on local mode and direct IPv6
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

1. Finish local mode polish and local endpoint coverage.
2. Freeze a versioned protocol document.
3. Implement encrypted transport for relay and direct paths.
4. Make direct IPv6 route detection trustworthy.
5. Harden self-hosted relay lifecycle and deployment docs.
6. Add localization plumbing and accessibility polish.
7. Write the upstream design note before attempting a large core port.

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
- direct IPv6 works where it should
- difficult networks are solved by an optional self-hosted relay, not by a mandatory third-party service
- the security model is honest and documented
- localization and accessibility are first-class
- the core candidate subset is realistic enough to upstream into LibreOffice

The most realistic end state is:

- LibreOffice core owns the user-facing local and direct remote experience
- a separate FOSS companion relay server remains available for users who need internet traversal

That preserves the no-third-party-service goal without pretending that CGNAT can be solved with no relay at all.
