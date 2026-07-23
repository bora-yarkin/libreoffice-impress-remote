<!-- SPDX-FileCopyrightText: 2026 Bora Yarkın -->
<!-- SPDX-License-Identifier: GPL-3.0-only -->

# TODO

Open work only. Implemented work belongs in `CHANGELOG.md`.

- Record broader Local network mode results across supported LibreOffice versions, macOS, Windows, Linux, iOS Safari, Android Chrome, and Android Firefox.
- Add browser-level E2E tests for the phone UI, Safari local fallback, encrypted local/direct handshakes, reconnect flows, and command round trips.
- Verify accessibility for keyboard navigation, focus order, screen-reader labels, status announcements, QR fallback, Copy URL fallback, and phone controls.
- Keep release readiness evidence for real same-Wi-Fi and hotspot workflows after each release.
- Test LocalTunnel creation, teardown, provider failure behavior, browser loading, encrypted state/assets, and encrypted commands on real networks.
- Test Direct IPv6 discovery, firewall guidance, encrypted browser behavior, and unavailable-IPv6 messaging on real networks.
- Test Relay Server mode with the bundled Python relay, service install/uninstall, reverse proxies, reconnect behavior, and compatible third-party relays.
- Keep Direct IPv6, Relay Server, and LocalTunnel clearly labeled as experimental in UI and docs.
- Improve LibreOffice Help content for local network use, hotspot setup, common errors, and experimental route warnings.
- Expand localization beyond English and Turkish after source strings settle.
- Improve frontend trust for local HTTP and relay-hosted UI delivery with local HTTPS, signed assets, pinned assets, or an equivalent trusted shell approach.
- Keep project documentation concise, current, and honest about volunteer maintenance limits.
- Revisit MS Office, browser-extension, or other office-suite adapters only if someone volunteers to build and maintain them.
