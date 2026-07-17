<!-- SPDX-FileCopyrightText: 2026 Bora Yarkın -->
<!-- SPDX-License-Identifier: GPL-3.0-only -->

# Relay Server

The relay server is a lightweight Python process using `aiohttp`.

It should:

- serve `/`, `/app.js`, and `/app.css` for the phone relay UI
- serve `/health`
- accept WebSocket clients on `/ws`
- match clients by session ID
- relay presentation state and command frames
- expire dead sessions

Current relay transport note:

- `hello` messages are plaintext metadata used to derive or rotate relay keys
- `frame` messages for relay state, commands, and errors are AES-GCM encrypted and opaque to the relay
- newly joined phones can receive the latest `hello` and latest encrypted state while the plugin remains connected

It must not:

- decrypt payloads
- store slide previews
- store presenter notes
- require a database
- require Node.js
