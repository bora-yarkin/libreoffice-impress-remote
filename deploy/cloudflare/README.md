<!-- SPDX-FileCopyrightText: 2026 Bora Yarkın -->
<!-- SPDX-License-Identifier: GPL-3.0-only -->

# Cloudflare Relay Bundle

This bundle hosts the encrypted relay transport on Cloudflare Workers and Durable Objects, and serves the shared mobile remote UI from the same deployment.

[![Deploy to Cloudflare](https://deploy.workers.cloudflare.com/button)](https://deploy.workers.cloudflare.com/?url=https://github.com/bora-yarkin/libreoffice-impress-remote/tree/main/deploy/cloudflare)

It exposes:

- `/` for the phone UI
- `/ws` for the relay websocket transport
- `/api/session` for admission-controlled session status
- `/health` for runtime and limit information
- `/asset-manifest.json` for published web-asset verification

## Deploy

### Browser-Only Deploy

Click the **Deploy to Cloudflare** button above. Cloudflare will clone this relay app into your GitHub account, generate the `public/` phone UI from the shared upstream web UI, provision the Durable Object binding, and deploy it to your Cloudflare account without requiring Node.js, npm, npx, or Wrangler on your computer.

After deployment, copy the generated `workers.dev` URL and paste it into LibreOffice:

```text
Slide Show -> Remote Settings -> Relay Server (Experimental)
```

### Local CLI Deploy

1. Install Wrangler.
2. Review `wrangler.toml` and choose your Worker name and routes.
3. Deploy:

```bash
npx wrangler deploy
```

The mobile UI is generated into `public/` during deployment and served from there, while `/ws`, `/api/session`, and `/health` are handled by the Worker script in `src/index.mjs`.

Verify the deployment with:

```bash
curl https://your-worker.example/health
curl https://your-worker.example/asset-manifest.json
```
