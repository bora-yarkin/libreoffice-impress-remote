<!-- SPDX-FileCopyrightText: 2026 Bora Yarkın -->
<!-- SPDX-License-Identifier: GPL-3.0-only -->

# Architecture

The project uses one LibreOffice extension, one shared phone UI, and optional relay deployments.

```text
Local mode:
Phone browser -> laptop local IP -> LibreOffice extension

Relay mode:
Phone browser -> Python relay UI/WS <- LibreOffice extension relay client

Direct IPv6 mode:
Phone browser -> laptop global IPv6 -> LibreOffice extension
```

The extension owns slideshow control, notes extraction, state generation, local HTTP service, transport configuration, pairing, and relay-client behavior.

The relay server owns session matching, hosted relay phone UI delivery, plaintext relay-key negotiation messages, admission-controlled session status, and opaque encrypted frame forwarding.

As of `0.6.12`, relay and direct-IPv6 state, command, and asset flows are encrypted and session-bound. Local mode uses the same encrypted flow when the browser exposes Web Crypto, with an authenticated plaintext `/api/local/*` compatibility fallback for Safari-style LAN HTTP contexts that cannot run Web Crypto. The relay caches only the active `hello` plus a small bounded window of opaque plugin frames, and exposes a session-status probe so LibreOffice can detect joined relay phones.

## Runtime Components

- LibreOffice protocol handler: registers `vnd.org.borayarkin.impressremote:*` commands, owns start/stop/settings dispatch, and reports dynamic menu state.
- Impress controller adapter: reads slideshow state, presenter notes, slide indexes, titles, timer state, and blank/end state through UNO.
- Slide preview exporter: renders the current and next slide images for the phone UI.
- Local listener: serves the phone UI shell plus encrypted state, command, event, and slide-asset endpoints, with an authenticated plaintext `/api/local/*` compatibility fallback when local-mode Web Crypto is unavailable in the browser.
- Relay client: connects LibreOffice to an optional self-hosted relay and sends only encrypted session frames after pairing.
- Shared phone UI: static HTML, CSS, and JavaScript reused by the OXT, Python relay bundle, and Cloudflare relay bundle.
- Relay server: performs session admission and opaque websocket forwarding without parsing slide notes, slide images, or commands.

## Core Versus Companion Boundary

The long-term LibreOffice candidate is the local-first Impress remote experience:

- local LAN pairing and control
- QR pairing and route guidance
- presenter notes and slide preview state
- LibreOffice-native settings, menus, toolbar/notebookbar integration, help, localization, accessibility, and QA
- a versioned state and command contract

The companion boundary is everything required only for difficult networks:

- reference Python relay
- Cloudflare Worker relay
- VPS/service installers
- reverse-proxy, TLS, firewall, and deployment recipes
- future non-LibreOffice suite adapters

Direct IPv6 sits between those boundaries. It is implemented now as an optional fallback, but it should only become a LibreOffice-core candidate if the local feature proves stable and the added network complexity remains justified.

## Upstream Architecture Path

The current Python extension should not be proposed as a direct core import. It should be used to validate behavior, protocol shape, and UX before a smaller C++/LibreOffice-native patch series is written.

Likely LibreOffice surfaces:

- `sd/`: Impress slideshow state, control, slide preview, and feature ownership
- `framework/`: command dispatch, menu/toolbar behavior, and UI state
- `officecfg/`: configuration schema and defaults
- `svx/` or shared UI helpers: reusable QR/dialog/resource support if needed
- `uiconfig/simpress/`: menu, toolbar, and notebookbar integration
- help content: user-facing local pairing and troubleshooting docs
- tests/QA: controller state, local resource delivery, UI command registration, and package/resource checks

For the concrete upstream design note, see [LibreOffice Upstream Architecture](libreoffice-upstream-architecture.md).

## Non-goals

- No Node.js dependency.
- No database requirement.
- No server-side LibreOffice requirement.
- No server-side parsing of slide notes or previews.
- No mandatory hosted relay or public tunnel service.
