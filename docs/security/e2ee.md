<!-- SPDX-FileCopyrightText: 2026 Bora Yarkın -->
<!-- SPDX-License-Identifier: GPL-3.0-only -->

# End-to-End Encryption

Current local, LocalTunnel, direct IPv6, and relay profile in `1.0.3`:

```text
Pairing verifier in QR/Copy URL fragment
Relay admission token in QR/Copy URL fragment
ECDH P-256
HKDF-SHA256
AES-256-GCM
Versioned hello/frame/error messages
Replay protection, session binding, and key rotation
```

Today, relay mode protects presenter state, slide assets, and commands from passive or honest-but-curious relay operators. The relay only sees session metadata, the relay admission token, plaintext `hello` negotiation messages, and opaque encrypted `frame` payloads.

Web-Crypto-capable local mode and direct IPv6 now use the same encrypted session profile for presenter state, commands, and slide assets on the phone route. The phone loads the LibreOffice-served web UI, receives plaintext `hello` negotiation messages, and then decrypts `state`, `asset`, and command-related traffic in the browser.

Safari and some locked-down browser contexts do not expose Web Crypto on plain LAN HTTP origins such as `http://172.20.10.8:17865`. For local mode only, the phone UI can fall back to authenticated plaintext polling on `/api/local/*` when Web Crypto is unavailable. That fallback requires the session id and pairing verifier from the QR/Copy URL fragment on every request, is restricted to local-network clients, but it is not encrypted and should be treated as same-LAN compatibility behavior, not as E2EE.

LibreOffice generates a pairing verifier, places it in the QR/Copy URL fragment as `k=...`, places the relay admission token in the same fragment as `a=...`, and both sides derive transport keys from ephemeral P-256 ECDH plus that verifier. The fragment is not sent in HTTP requests, but any JavaScript running in the loaded page can read it.

The long-term goal is still one shared encrypted message format across local, relay, and direct IPv6 modes. The current implementation uses the same encrypted frame contract for relay, direct IPv6, and local mode when Web Crypto is available.

## Route Security Summary

| Route | Confidentiality Today | Authentication Today | Main Remaining Risk |
| --- | --- | --- | --- |
| Local with Web Crypto | AES-256-GCM encrypted frames for state, commands, and slide assets. | Ephemeral P-256 ECDH plus pairing verifier; direct HTTP requests must also carry the session id. | Static web shell is still served over HTTP. |
| Local Safari compatibility | Plaintext state, commands, and slide assets. | Every `/api/local/*` request must include the session id and pairing verifier headers and come from a local-network client. | Same-LAN observers can see traffic; use only on trusted local networks. |
| LocalTunnel | AES-256-GCM encrypted frames for state, commands, and slide assets through the tunnel. | Ephemeral P-256 ECDH plus pairing verifier; direct HTTP requests must also carry the session id. | The tunnel provider and public URL must be trusted as frontend delivery infrastructure. |
| Direct IPv6 | AES-256-GCM encrypted frames for state, commands, and slide assets. | Ephemeral P-256 ECDH plus pairing verifier; direct HTTP requests must also carry the session id. | Public reachability and firewall exposure must be handled carefully. |
| Relay | AES-256-GCM encrypted frames through the relay. | Ephemeral P-256 ECDH plus pairing verifier and relay admission token. | Relay-hosted frontend delivery still has to be trusted or verified. |

## Important Limitation

If the phone UI is loaded from the relay server, a malicious relay can serve hostile JavaScript. The E2E design protects against passive or honest-but-curious relays, not against a relay that controls frontend delivery unless the frontend is pinned, audited, or installed from a trusted source.

For `1.0.3`, the supported relay trust model is:

- self-host the published Python or Cloudflare relay bundle
- verify `asset-manifest.json` against the published release artifact before trusting the hosted phone UI
- use the packaged page with subresource-integrity attributes for the shared CSS and JavaScript assets

For local, LocalTunnel, and direct IPv6, the supported trust model is:

- the QR/Copy URL carries the pairing verifier in the fragment, which is not sent in HTTP requests
- presenter state, slide assets, and commands use encrypted frames after the web shell loads
- direct local/tunnel/IPv6 endpoints require the session id from the pairing fragment before being treated as paired client activity
- Safari local compatibility can use local-network-only authenticated plaintext `/api/local/*` polling only when the browser does not expose Web Crypto
- LocalTunnel, direct IPv6, and relay mode still require Web Crypto and fail closed when encrypted transport is unavailable
- the web shell itself is still served over HTTP, so this protects against passive local-network observers but not an active local attacker that can modify JavaScript in transit
- LocalTunnel serves the same web shell through the tunnel provider, so treat the public tunnel URL as secret and trust the provider as frontend delivery infrastructure

That is a practical deployment policy and a frontend-integrity baseline, not a complete defense against an attacker that can replace the initial HTML page. Stronger local frontend trust still depends on future work such as local HTTPS or an installed/trusted phone shell.
