<!-- SPDX-FileCopyrightText: 2026 Bora Yarkın -->
<!-- SPDX-License-Identifier: GPL-3.0-only -->

# End-to-End Encryption

Current relay and direct IPv6 profile in `0.5.0`:

```text
Pairing secret in QR/manual-link fragment
Relay admission token in QR/manual-link fragment
HKDF-SHA256
AES-256-GCM
Versioned hello/frame/error messages
Replay protection, session binding, and key rotation
```

Today, relay mode protects presenter state, slide assets, and commands from passive or honest-but-curious relay operators. The relay only sees session metadata, the relay admission token, plaintext `hello` negotiation messages, and opaque encrypted `frame` payloads.

Direct IPv6 now uses the same encrypted session profile for presenter state, commands, and slide assets on the phone route. The phone loads the LibreOffice-served web UI, receives plaintext `hello` negotiation messages, and then decrypts `state`, `asset`, and command-related traffic in the browser.

The current bootstrap is still a pre-shared-secret design: LibreOffice generates a pairing secret, places it in the QR/manual link fragment as `k=...`, places the relay admission token in the same fragment as `a=...`, and both sides derive relay keys from that secret. The fragment is not sent in HTTP requests, but any JavaScript running in the loaded page can read it.

Planned next cryptography step:

```text
ECDH P-256
HKDF-SHA256
AES-256-GCM
```

The long-term goal is still one shared encrypted message format across local, relay, and direct IPv6 modes. Today, relay and direct IPv6 use the encrypted frame protocol, while the local-only route still needs to adopt it.

## Important Limitation

If the phone UI is loaded from the relay server, a malicious relay can serve hostile JavaScript. The E2E design protects against passive or honest-but-curious relays, not against a relay that controls frontend delivery unless the frontend is pinned, audited, or installed from a trusted source.

For `0.5.0`, the supported trust model is:

- self-host the published Python or Cloudflare relay bundle
- verify `asset-manifest.json` against the published release artifact before trusting the hosted phone UI

That is a practical deployment policy, not a cryptographic frontend pinning scheme. Stronger frontend trust still depends on future work such as ECDH-based bootstrap plus a more explicit trusted-frontend distribution story.
