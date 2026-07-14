<!-- SPDX-FileCopyrightText: 2026 Bora Yarkın -->
<!-- SPDX-License-Identifier: GPL-3.0-only -->

# Relay Server

The relay server is a lightweight Python process using `aiohttp`.

It should:

- serve `/health`
- accept WebSocket clients on `/ws`
- match clients by session ID
- relay encrypted frames
- expire dead sessions

It must not:

- decrypt payloads
- store slide previews
- store presenter notes
- require a database
- require Node.js
