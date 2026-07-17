<!-- SPDX-FileCopyrightText: 2026 Bora Yarkın -->
<!-- SPDX-License-Identifier: GPL-3.0-only -->

# Cloudflare Relay Bundle

This bundle hosts the encrypted relay transport on Cloudflare Workers and Durable Objects, and serves the shared mobile remote UI from the same deployment.

It exposes:

- `/` for the phone UI
- `/ws` for the relay websocket transport
- `/api/session` for admission-controlled session status
- `/health` for runtime and limit information
- `/asset-manifest.json` for published web-asset verification

## Deploy

1. Install Wrangler.
2. Review `wrangler.toml` and choose your Worker name and routes.
3. Deploy:

```bash
npx wrangler deploy
```

The mobile UI is served from `public/`, while `/ws`, `/api/session`, and `/health` are handled by the Worker script in `src/index.mjs`.

Verify the deployment with:

```bash
curl https://your-worker.example/health
curl https://your-worker.example/asset-manifest.json
```
