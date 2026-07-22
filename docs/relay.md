<!-- SPDX-FileCopyrightText: 2026 Bora Yarkın -->
<!-- SPDX-License-Identifier: GPL-3.0-only -->

# Relay And Deployment

Relay Server mode is an experimental path for networks where Local network mode does not fit. The relay stays thin: it serves the phone page, forwards encrypted websocket envelopes, exposes health/session status, and never decrypts presenter notes, commands, or slide images.

Local network mode is the main product path. Use relay mode only if you are comfortable self-hosting or deploying experimental infrastructure.

The installed OXT contains matching bundles for its own version:

- `impress-remote-relay-python-<version>.zip`
- `impress-remote-relay-cloudflare-<version>.zip`
- `impress-remote-docs-<version>.zip`

Open `Slide Show -> Remote Settings`, select `Relay Server`, then use `Get Relay Server`, `Get Cloudflare Relay`, or `Get Documentation`.

## HTTP Contract

A compatible relay serves:

- `/` plus `/app.js` and `/app.css`
- `/asset-manifest.json`
- `/localizations/manifest.json` and `/localizations/<locale>.json`
- `/health`
- `/api/session?session=<id>&a=<admission-token>`
- `/ws?role=plugin|phone&session=<id>&a=<admission-token>`

`hello`, `frame`, and `error` envelopes are forwarded as protocol messages. `frame` payloads stay AES-GCM encrypted end to end.

## Security Notes

Relay transport confidentiality is end-to-end encrypted between LibreOffice and the phone. A relay operator can see session metadata and opaque ciphertext, not slide contents or commands.

Frontend delivery is separate: the phone runs JavaScript served by the relay. Self-host the matching bundle from the OXT or verify `/asset-manifest.json` before trusting a hosted relay.

## Python Relay

For development from the source checkout:

```bash
make server-dev
```

From an exported bundle, run:

```bash
./run-relay.sh
```

Windows PowerShell:

```powershell
.\run-relay.ps1
```

The exported Python relay includes Linux and Windows service install/uninstall helpers. They persist a randomly chosen free port in `data/service.json`.

## Cloudflare Relay

Export `Get Cloudflare Relay`, then deploy the unpacked Worker bundle with Wrangler:

```bash
npx wrangler deploy
```

The Worker serves static phone UI assets from `public/` and keeps session state in Durable Objects.

## Reverse Proxy Checklist

- Terminate TLS at the proxy, or use plain HTTP only on a trusted internal network.
- Forward websocket upgrades on `/ws`.
- Preserve query parameters on `/ws` and `/api/session`.
- Keep `/asset-manifest.json` reachable for verification.
- Keep relay paths aligned with the relay base URL saved in LibreOffice.

## Compatibility Check

Run:

```bash
make relay-compat RELAY_URL=https://relay.example.com
```

This validates the public HTTP contract, asset manifest, localization manifest, and session-status behavior. Websocket forwarding still needs implementation-specific tests or the release checklist.
