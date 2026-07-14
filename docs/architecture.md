<!-- SPDX-FileCopyrightText: 2026 Bora Yarkın -->
<!-- SPDX-License-Identifier: GPL-3.0-only -->

# Architecture

The project uses one LibreOffice extension and one optional Python relay server.

```text
Local mode:
Phone browser -> laptop local IP -> LibreOffice extension

Relay mode:
Phone browser -> Python relay <- LibreOffice extension

Direct IPv6 mode:
Phone browser -> laptop global IPv6 -> LibreOffice extension
```

The extension owns slideshow control, notes extraction, state generation, local HTTP/WebSocket service, pairing, and relay-client behavior.

The relay server owns only WebSocket session matching and encrypted frame forwarding.

## Non-goals

- No Node.js dependency.
- No database requirement.
- No server-side LibreOffice requirement.
- No server-side parsing of slide notes or previews.
