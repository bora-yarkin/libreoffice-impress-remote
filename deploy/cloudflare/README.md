<!-- SPDX-FileCopyrightText: 2026 Bora Yarkın -->
<!-- SPDX-License-Identifier: GPL-3.0-only -->

# Cloudflare Relay

This bundle hosts the encrypted relay transport on Cloudflare Workers and Durable Objects, and serves the shared mobile remote UI from the same deployment.

It exposes:

- `/` for the phone UI
- `/ws` for the relay websocket transport
- `/api/session` for admission-controlled session status
- `/health` for runtime and limit information
- `/asset-manifest.json` for published web-asset verification

## Deploy

### Cloudflare Dashboard Deploy

This path needs only a Cloudflare account.

1. Open `dashboard-worker.mjs` and copy the whole file.
2. In Cloudflare, open `Workers & Pages`, create a Worker, open the code editor, replace the starter code with the copied Worker, then deploy it.
3. In the deployed Worker settings, add a Durable Object binding named `RELAY_ROOMS` that points to the exported class `RelayRoom`, then redeploy if Cloudflare asks for it.
4. Visit `https://your-worker.workers.dev/health`. It should return JSON with `runtime: "cloudflare-workers"`.

After deployment, copy the generated `workers.dev` URL and paste it into LibreOffice:

```text
Slide Show -> Remote Settings -> Relay Server (Experimental)
```

`dashboard-worker.mjs` is generated from `src/index.mjs`, `shared/webui`, and `shared/localizations`. Do not edit it by hand; regenerate it with:

```bash
python tools/build_cloudflare_dashboard_worker.py
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
