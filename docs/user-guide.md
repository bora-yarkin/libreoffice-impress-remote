<!-- SPDX-FileCopyrightText: 2026 Bora Yarkın -->
<!-- SPDX-License-Identifier: GPL-3.0-only -->

# User Guide

LibreOffice Impress Remote turns a phone browser into a simple remote for an Impress slideshow. The normal flow is local-first: open an Impress file, start the remote from LibreOffice, scan a QR code, and control the presentation from the phone.

## Start A Local Remote

1. Open a presentation in LibreOffice Impress.
2. Choose `Slide Show -> Start Remote`.
3. Keep the phone and computer on the same Wi-Fi, or connect the computer to the phone hotspot.
4. Scan the QR code shown by LibreOffice.
5. Use the phone for current slide preview, presenter notes, effect-aware previous/next, tap-to-advance, timers, first slide, last slide, fullscreen, and go-to-slide.

The QR popup closes automatically after a non-loopback phone connects. If scanning fails, use `Copy URL` in the QR popup and open the copied link on the phone without editing the `#...` fragment.

## Choose A Mode

Open `Slide Show -> Remote Settings` only when you need to change the connection mode.

| Mode | Use When | Notes |
| --- | --- | --- |
| Local network | Phone and computer are on the same Wi-Fi or hotspot. | Default, tested, and recommended mode. |
| LocalTunnel | Local network access is blocked and you want a temporary public URL. | Experimental. Uses the vendored LocalTunnel-compatible client. Treat the generated URL as secret. |
| Direct IPv6 | Both devices have public IPv6 and the desktop firewall allows the remote port. | Experimental. Useful only on networks where public IPv6 actually works end to end. |
| Relay Server | You run the included Python relay, Cloudflare relay, or a compatible self-hosted relay. | Experimental. Enter the relay URL in Remote Settings before starting. |

Remote Settings is intentionally small: mode selector, relay URL when Relay Server is selected, relay/documentation export buttons when Relay Server is selected, Help, Save, and Close.

Changing settings while the remote is running stops the remote. Start it again to use the saved mode.

## Hotspot Workflow

Phone hotspots often work better than public Wi-Fi because the phone and laptop are on a private network controlled by the phone.

1. Turn on the phone hotspot.
2. Connect the computer running LibreOffice to that hotspot.
3. Keep Remote Settings on `Local network`.
4. Choose `Slide Show -> Start Remote`.
5. Scan the QR code with the same phone.

An iPhone hotspot URL such as `http://172.20.10.8:17865/#...` is normal. Safari may not expose Web Crypto on that plain local HTTP origin, so local mode can use an authenticated LAN-only fallback. Use it only on trusted local networks.

## Phone UI

The phone page is deliberately not a settings app. It has:

- the current slide image pinned to the top
- slide number as `current / total`
- presenter notes as the scrollable area
- previous and next controls pinned to the bottom; these trigger effects first, then move between slides
- tap-to-advance on the slide image, using the same effect-aware next action
- an overflow drawer for first slide, last slide, timer pause/resume, and go-to-slide
- a fullscreen slide mode button
- reconnect/offline feedback with retry and reload

Route selection, relay configuration, exported resources, and help stay in LibreOffice.

## Project Expectations

This is a volunteer FOSS extension. Local network mode is the main supported path right now. LocalTunnel, Direct IPv6, and Relay Server mode are useful for testing and hard networks, but they should be treated as experimental unless you have verified them in your own environment.
