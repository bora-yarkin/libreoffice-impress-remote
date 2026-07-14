<!-- SPDX-FileCopyrightText: 2026 Bora Yarkın -->
<!-- SPDX-License-Identifier: GPL-3.0-only -->

# End-to-End Encryption

Planned production profile:

```text
ECDH P-256
HKDF-SHA256
AES-256-GCM
```

The same encrypted message format should be used in local, relay, and direct IPv6 modes.

## Important Limitation

If the phone UI is loaded from the relay server, a malicious relay can serve hostile JavaScript. The E2E design protects against passive or honest-but-curious relays, not against a relay that controls frontend delivery unless the frontend is pinned, audited, or installed from a trusted source.
