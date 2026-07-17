<!-- SPDX-FileCopyrightText: 2026 Bora Yarkın -->
<!-- SPDX-License-Identifier: GPL-3.0-only -->

# Architecture

The project uses one LibreOffice extension and one optional Python relay server.

```text
Local mode:
Phone browser -> laptop local IP -> LibreOffice extension

Relay mode:
Phone browser -> Python relay UI/WS <- LibreOffice extension relay client

Direct IPv6 mode:
Phone browser -> laptop global IPv6 -> LibreOffice extension
```

The extension owns slideshow control, notes extraction, state generation, local HTTP service, transport configuration, pairing, and relay-client behavior.

The relay server owns session matching, hosted relay phone UI, plaintext relay-key negotiation messages, and opaque encrypted frame forwarding.

As of `0.3.3`, relay and direct-IPv6 state, command, and asset flows are encrypted and session-bound. The local-only route still needs to adopt the same protocol profile.

## Non-goals

- No Node.js dependency.
- No database requirement.
- No server-side LibreOffice requirement.
- No server-side parsing of slide notes or previews.
