# SPDX-FileCopyrightText: 2026 Bora Yarkın
# SPDX-License-Identifier: GPL-3.0-only

# TODO

Recovered roadmap based on the current repository state.

## Current foundation already present

- LibreOffice `.oxt` packaging, manifest files, and menu registration exist.
- A UNO protocol handler can start and stop an embedded local HTTP server.
- A minimal phone web UI exists with polling and two control buttons.
- A relay server skeleton exists with `/health` and `/ws`.
- Basic token generation and HKDF utility code exist.

## Local mode

- Make the extension expose a usable pairing flow instead of only printing a localhost URL.
- Show the actual LAN URL in LibreOffice so a phone can connect over Wi-Fi.
- Add QR-code pairing for the local server URL.
- Detect the best local IPv4 and IPv6 addresses instead of always advertising `127.0.0.1`.
- Add a real status surface in LibreOffice that shows whether the local server is running.
- Add port conflict handling and a way to change the local port.
- Support HTTPS or clearly document why local HTTP is acceptable for the product model.
- Replace polling with WebSocket or server-sent push for lower-latency state updates.
- Add reconnect handling when the phone drops off the network and returns.

## Presentation state and slideshow control

- Read the real current slide index instead of always returning `0`.
- Detect whether a slideshow is actually running instead of always returning `True`.
- Return the real slide count for the active presentation in slideshow mode and edit mode.
- Wire presenter notes extraction into the state response.
- Add next-slide preview generation instead of the current placeholder-only module.
- Add direct commands for next slide versus next effect and previous slide versus previous effect in the UI.
- Add go-to-slide support in the phone UI.
- Handle cases where no presentation is open or no slideshow controller is available.
- Start slideshow mode from the extension when needed.
- Keep state synchronized when slides change outside the phone UI.

## Phone web UI

- Add a connection and pairing screen instead of assuming a working local server.
- Add a transport selector for local, direct IPv6, and relay modes.
- Add a settings screen for relay host, port, and session details.
- Add a presenter layout that shows current slide, next slide, notes, timer, and connection state.
- Add clearer control affordances for blank screen, jump to slide, and end presentation.
- Make the UI resilient to failed fetches, timeouts, and stale sessions.
- Add accessibility improvements for large tap targets, orientation changes, and low-light use.
- Add installable PWA behavior if offline or homescreen install is part of the intended UX.

## Direct IPv6 mode

- Detect whether the host actually has reachable public IPv6.
- Advertise the correct global IPv6 address to the phone.
- Handle bracketed IPv6 URL generation correctly in the UI and pairing flow.
- Add reachability checks so the user can tell whether direct IPv6 should work before trying it.
- Document router, firewall, and hotspot caveats for direct IPv6 use.
- Secure direct IPv6 transport with the same message protocol as other modes.

## Relay mode

- Implement the extension-side relay client instead of the current `NotImplementedError`.
- Add a LibreOffice configuration page for relay domain, IP, port, and transport settings.
- Create a pairing/session creation flow for relay mode.
- Define which side generates session IDs and how they are shared safely with the phone.
- Connect the phone UI to the relay server over WebSocket.
- Serve or otherwise distribute the phone UI for relay sessions.
- Add reconnect and session resume behavior for relay disconnections.
- Add relay authentication or admission control if public deployment is expected.
- Add relay deployment docs for VPS, reverse proxy, TLS, and firewall setup.

## End-to-end encryption and protocol

- Implement the planned ECDH P-256 key exchange.
- Implement AES-GCM encrypted frames instead of plain relayed messages.
- Define a shared message schema for commands, state updates, previews, and errors.
- Use the same protocol across local, direct IPv6, and relay modes.
- Add replay protection, session binding, and key rotation rules.
- Decide how the phone UI can be trusted when served by a relay-controlled origin.
- Add protocol versioning so phone and extension updates can fail gracefully.

## LibreOffice integration and configuration UX

- Add a real options or setup dialog inside LibreOffice.
- Persist configuration in LibreOffice user settings.
- Let users enable or disable local, IPv6, and relay transports independently.
- Show the active session, mode, and remote endpoints inside LibreOffice.
- Surface recoverable errors in LibreOffice UI instead of only printing to stdout or traceback.
- Add startup/shutdown cleanup so stopping the extension always tears down listeners and sessions.

## Relay server hardening

- Add limits for session count, message size, and idle clients.
- Add cleanup tasks for abandoned WebSocket connections.
- Add structured logging and operational metrics.
- Add graceful shutdown for running relay processes.
- Add optional TLS guidance or built-in termination assumptions.
- Add tests for real plugin-phone message relay, duplicate connections, and cleanup behavior.
- Add abuse protections if the relay will be internet-facing.

## Testing

- Add unit tests for slideshow state extraction, notes extraction, and command dispatch.
- Add integration tests for the local HTTP server endpoints.
- Add tests for the phone UI behavior and protocol messages.
- Add tests for the extension-side relay client once implemented.
- Add compatibility checks against LibreOffice’s bundled Python runtime.
- Add end-to-end manual test scripts for local, IPv6, and relay scenarios.

## Documentation

- Restore a feature matrix that clearly marks implemented versus planned behavior.
- Add a user-facing "how to run" guide for the current local-only prototype.
- Add an architecture/protocol document for the three transport paths.
- Add troubleshooting guidance for LibreOffice extension loading and reinstall behavior.
- Add security notes that distinguish prototype security from production goals.

## Release readiness

- Define a milestone for "local presenter remote works end-to-end".
- Define a milestone for "direct IPv6 works end-to-end".
- Define a milestone for "relay mode works end-to-end with encryption".
- Decide the minimum supported LibreOffice versions and platforms.
- Add CI coverage for building the `.oxt` and running both extension and relay tests.
