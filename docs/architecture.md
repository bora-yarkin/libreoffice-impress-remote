<!-- SPDX-FileCopyrightText: 2026 Bora Yarkın -->
<!-- SPDX-License-Identifier: GPL-3.0-only -->

# Architecture

The project uses one LibreOffice extension, one shared phone UI, and optional relay deployments.

```text
Local mode:
Phone browser -> laptop local IP -> LibreOffice extension

LocalTunnel mode:
Phone browser -> tunnel URL -> laptop local listener -> LibreOffice extension

Relay mode:
Phone browser -> relay UI/WS <- LibreOffice extension relay client

Direct IPv6 mode:
Phone browser -> laptop global IPv6 -> LibreOffice extension
```

The extension owns slideshow control, notes extraction, state generation, local HTTP service, transport configuration, pairing, and relay-client behavior.

The relay server owns session matching, hosted relay phone UI delivery, plaintext relay-key negotiation messages, admission-controlled session status, and opaque encrypted frame forwarding.

As of `1.0.5`, local, LocalTunnel, relay, and direct-IPv6 state, command, and asset flows are encrypted, session-bound, and bootstrapped with ephemeral ECDH P-256 hello negotiation when Web Crypto is available. Local mode uses the same encrypted flow with a LAN-only authenticated plaintext `/api/local/*` compatibility fallback for Safari-style HTTP contexts that cannot run Web Crypto. Direct IPv6 mode can use the same authenticated plaintext fallback only when the user explicitly chooses that experimental route. The relay caches only the active `hello` plus a small bounded window of opaque plugin frames, exposes a session-status probe so LibreOffice can detect joined relay phones, and serves the shared web UI with generated asset/localization manifests.

## Route Responsibilities

| Route | Listener/Server | Phone UI Source | State And Commands | Primary Use |
| --- | --- | --- | --- | --- |
| Local, Web-Crypto-capable browser | LibreOffice embedded HTTP listener | LibreOffice extension | Session-bound encrypted `/api/direct/*` frames | Same Wi-Fi and hotspot use. |
| Local, Safari-style Web Crypto unavailable | LibreOffice embedded HTTP listener | LibreOffice extension | LAN-only authenticated plaintext `/api/local/*` polling | Same-LAN compatibility on trusted local networks. |
| LocalTunnel | LibreOffice embedded listener exposed through tunnel | LibreOffice extension | Session-bound encrypted `/api/direct/*` frames | Temporary public URL when local network access is blocked. |
| Direct IPv6 | LibreOffice embedded IPv6 listener | LibreOffice extension | Session-bound encrypted `/api/direct/*` frames | Optional fallback when public IPv6 works end to end. |
| Relay | Self-hosted Python or Cloudflare relay | Relay-hosted shared phone UI | Opaque encrypted websocket frames | Optional fallback for CGNAT or blocked local networks. |

## Runtime Components

- LibreOffice protocol handler: registers `vnd.org.borayarkin.impressremote:*` commands, owns start/stop/settings dispatch, and reports dynamic menu state.
- Impress controller adapter: reads slideshow state, presenter notes, slide indexes, titles, timer state, and end-of-deck state through UNO.
- Slide preview exporter: renders the current and next slide images for the phone UI.
- Local listener: serves the phone UI shell plus session-bound encrypted state, command, event, and slide-asset endpoints, with a LAN-only authenticated plaintext `/api/local/*` compatibility fallback when local-mode Web Crypto is unavailable in the browser.
- Relay client: connects LibreOffice to an optional self-hosted relay and sends only encrypted session frames after pairing.
- Shared phone UI: static HTML, CSS, and JavaScript reused by the OXT, Python relay bundle, and Cloudflare deploy build.
- Relay server: performs session admission and opaque websocket forwarding without parsing slide notes, slide images, or commands.

## Main And Experimental Boundaries

The main product is the local-first Impress remote experience:

- local LAN pairing and control
- QR pairing and route guidance
- presenter notes and slide preview state
- LibreOffice extension settings, menus, toolbar/notebookbar integration, help, localization, accessibility, and QA
- a versioned state and command contract

The experimental boundary is everything required only for difficult networks:

- reference Python relay
- Cloudflare Worker relay
- VPS/service installers
- reverse-proxy, TLS, firewall, and deployment recipes
- possible future non-LibreOffice suite adapters, if someone volunteers to maintain them

Direct IPv6 sits between those boundaries. It is implemented now as an optional fallback, but it remains experimental until enough real networks prove it is worth recommending.

## Extension Maintenance Notes

This repository is the product. The current direction is not to merge the feature into LibreOffice core. Keep the extension dependency-light, understandable, and self-contained.

Practical constraints:

- Keep local mode independent from relay, tunnel, and cloud-specific behavior.
- Avoid native Python wheels inside the OXT.
- Avoid mandatory Node.js, npm, databases, hosted services, or server-side LibreOffice.
- Keep SPDX and REUSE metadata valid.
- Never log slide notes, slide images, pairing secrets, or relay payloads.
- Treat LocalTunnel, Direct IPv6, and Relay Server mode as experimental unless they have recorded field-test evidence.

## Non-goals

- No Node.js dependency.
- No database requirement.
- No server-side LibreOffice requirement.
- No server-side parsing of slide notes or previews.
- No mandatory hosted relay or public tunnel service.
