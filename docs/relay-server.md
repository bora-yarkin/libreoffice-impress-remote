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

Current prototype note:

- relay messages are plaintext JSON today
- encrypted relay frames are still planned before security-sensitive use

It must not:

- decrypt payloads
- store slide previews
- store presenter notes
- require a database
- require Node.js
