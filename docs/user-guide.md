<!-- SPDX-FileCopyrightText: 2026 Bora Yarkın -->
<!-- SPDX-License-Identifier: GPL-3.0-only -->

# User Guide

LibreOffice Impress Remote is local-first. The normal path is: open a presentation in Impress, start the remote, scan the QR code, and use the phone as a simple remote with the current slide and presenter notes.

## Recommended Local Workflow

1. Open the presentation in LibreOffice Impress.
2. Choose `Slide Show -> Presentation Remote -> Start Remote`.
3. Keep your phone on the same Wi-Fi, or connect the computer to the phone hotspot.
4. Scan the QR code from the phone camera.
5. Use the phone UI for previous, next, tap-to-advance, and presenter notes.

The QR popup closes automatically after a phone connects. To pair another phone, choose Start Remote again while the remote is running.

## Hotspot Workflow

Phone hotspots often work better than public Wi-Fi because the phone and laptop are on a small private network controlled by the phone.

1. Turn on the phone hotspot.
2. Connect the computer running LibreOffice to that hotspot.
3. Start the remote in Impress.
4. Scan the QR code with the same phone.

If the phone opens a URL like `http://172.20.10.8:17865/#...`, that is normal for an iPhone hotspot. Safari may not expose Web Crypto on that plain HTTP local address, so the extension can use an authenticated local compatibility fallback. That fallback is local-only and should be used on trusted local networks.

## Route Choices

Use `Advanced Remote Settings` when you need to force a route:

| Route | Use When | Notes |
| --- | --- | --- |
| Auto | Normal use | Tries local, then direct IPv6, then relay. |
| Local only | Same Wi-Fi or hotspot testing | Recommended primary path. |
| Direct IPv6 only | Both devices have public IPv6 | Requires firewall/router support and is not common on every network. |
| Relay only | Local and IPv6 do not work | Requires a self-hosted relay URL. |

## Manual Link Backup

The QR code is preferred because it preserves the full pairing fragment. If scanning fails:

1. Open `Advanced Remote Settings`.
2. Copy the Manual Link.
3. Send it to the phone without changing the `#...` fragment.

Do not remove the fragment. It contains the session id and pairing verifier required by the phone UI.

## What The Phone UI Intentionally Does Not Do

The phone UI is intentionally a dummy remote. It does not expose route selection, relay settings, IP lists, or troubleshooting controls. Those belong in LibreOffice so the mobile UI stays lightweight and localization-light.
