<!-- SPDX-FileCopyrightText: 2026 Bora Yarkın -->
<!-- SPDX-License-Identifier: GPL-3.0-only -->

# Test Before Release

Use this checklist before publishing a release. CI proves the package can be built and the protocol code still works; this checklist proves the installed OXT works in real LibreOffice and real phone browsers.

Record date, version, OS, LibreOffice version, phone browser, route, result, and notes for every manual run. Mark unavailable environments as skipped with a reason.

## Release Candidate Setup

- Confirm `VERSION` contains the release candidate version.
- Run `make clean`.
- Run `make venv`.
- Run `make lint`.
- Run `make test`.
- Run `make oxt`.
- Confirm `dist/libreoffice-impress-remote-<version>.oxt` exists.
- Confirm the OXT contains `resources/impress-remote-docs-<version>.zip`.
- Confirm the OXT contains the Python relay bundle and does not contain a Cloudflare relay archive.
- Install the generated OXT into a clean LibreOffice profile when possible.
- Use an Impress deck with at least five slides, titles, notes, and one image-heavy slide.

## OXT Install And Menu Integration

- Install the OXT through LibreOffice Extension Manager.
- Confirm Extension Manager shows icon, localized name, publisher, and description.
- Restart LibreOffice.
- Confirm `Slide Show -> Start Remote` and `Slide Show -> Remote Settings` appear in Impress.
- Confirm the remote actions do not appear in Writer, Calc, or the LibreOffice start center.
- Start the remote and confirm the menu item changes to `Stop Remote`.
- Stop the remote and confirm it changes back to `Start Remote`.
- Confirm toolbar or notebookbar buttons appear near built-in slideshow controls where LibreOffice supports addon toolbar merging.

## Remote Settings

- Open `Slide Show -> Remote Settings`.
- Confirm the mode selector includes Local network, Direct IPv6, Relay Server, and LocalTunnel.
- Confirm Local network is selected by default on a clean profile.
- Confirm relay URL and resource export controls are hidden unless Relay Server is selected.
- Select Relay Server and confirm relay URL, Get Relay Server, Deploy to Cloudflare, and Get Documentation appear.
- Confirm Remote Settings contains only mode selection, relay-only controls, Help, Save, and Close.
- Change a setting while the remote is running, save, and confirm the remote stops.
- Open Help and confirm it is a static readable information page.

## QR Pairing Popup

- Start Remote.
- Confirm the QR popup shows a QR code and `Copy URL`.
- Confirm Copy URL copies a full URL with the `#...` fragment intact.
- Scan the QR code with a phone.
- Confirm the popup closes after the phone connects.
- Confirm LibreOffice starts the slideshow from the first slide after pairing.

## Local Same-Wi-Fi Mode

- Put desktop and phone on the same Wi-Fi.
- Select Local network mode.
- Start Remote and scan the QR code.
- Confirm slide image, presenter notes, previous, next, and tap-to-advance work.
- Confirm notes are the only scrollable phone region.
- Confirm slide number appears as `current / total`.
- Confirm the phone has no settings UI.
- Stop Remote and confirm the phone shows reconnect/offline feedback.

## Hotspot Local Mode

- Turn on phone hotspot.
- Connect the desktop to that hotspot.
- Select Local network mode.
- Start Remote and scan the QR code with the same phone.
- Confirm the hotspot URL works and controls the presentation.
- Stop Remote and confirm the listener is torn down.

## Safari Local Compatibility

- Use iOS or iPadOS Safari over same Wi-Fi or hotspot.
- Scan a Local network QR code.
- Confirm Safari does not show a Web Crypto unavailable error.
- Confirm the authenticated local fallback reads state and sends previous/next/goto commands.
- Confirm LocalTunnel, Direct IPv6, and Relay Server still require Web Crypto.
- Confirm Copy URL works if QR scanning fails.

## LocalTunnel Mode

Experimental route. Test it when possible, but do not block the local `1.0.0` path on this route.

- Select LocalTunnel mode.
- Start Remote.
- Wait for a public tunnel URL.
- Scan the QR code or use Copy URL.
- Confirm the phone loads through HTTPS from the tunnel URL.
- Confirm encrypted state, slide assets, previous/next, tap-to-advance, and goto-slide work.
- Stop Remote and confirm the tunnel closes.
- Record the tunnel provider URL and any provider interstitial or rate-limit behavior.

## Direct IPv6 Mode

Experimental route. Test it only on a network that can realistically prove public IPv6 behavior.

- Test only on a network where the desktop has a globally reachable IPv6 address.
- Select Direct IPv6 mode.
- Start Remote.
- Confirm only global IPv6 addresses are advertised.
- Scan from a phone network that can reach the desktop IPv6 address.
- Confirm encrypted state, slide assets, previous/next, tap-to-advance, and goto-slide work.
- Confirm unavailable IPv6 reports useful firewall/router/network guidance.
- If no public IPv6 environment is available, mark skipped with the network reason.

## Python Relay Mode

Experimental route. Test it when validating advanced self-hosted behavior.

- Select Relay Server mode.
- Export the bundled Python relay package.
- Extract it outside the repository.
- Run the foreground relay helper.
- Confirm `/health` returns successfully.
- Save the relay URL in Remote Settings.
- Start Remote and scan the relay QR code.
- Confirm the phone receives the shared web UI from the relay.
- Confirm slide image, notes, previous, next, tap-to-advance, and goto-slide work.
- Confirm the relay logs do not contain decrypted presenter notes, slide text, commands, or image data.

## Python Relay Service Scripts

- On Linux, run the install script on a disposable VM and confirm the service starts.
- Confirm it chooses or persists an available port and `/health` works.
- Run the Linux uninstaller and confirm the service is removed.
- On Windows, install the service on a disposable VM and confirm `/health` works.
- Run the Windows uninstaller and confirm the service is removed.
- Mark unavailable platforms as skipped with a reason.

## Cloudflare Relay Mode

Experimental route. Test it when validating advanced self-hosted or edge-hosted behavior.

- Select Relay Server mode.
- Open the Deploy to Cloudflare button from LibreOffice Remote Settings, `docs/relay.md`, or `deploy/cloudflare/README.md`.
- Deploy the Worker/Durable Object app from the browser flow.
- Confirm `/health` and `/asset-manifest.json` work.
- Save the deployed relay URL in Remote Settings.
- Start Remote and scan the QR code.
- Confirm slide image, notes, previous, next, tap-to-advance, and goto-slide work.
- Confirm no shared web UI files need editing after bundle generation.

## Phone Browser UI

- Test iOS Safari.
- Test Android Chrome.
- Test Android Firefox when available.
- Confirm slide image is pinned to the top at maximum useful width.
- Confirm notes scroll independently.
- Confirm previous/next stay pinned to the bottom.
- Confirm the overflow drawer has first slide, last slide, timer pause/resume, and go-to-slide only.
- Confirm fullscreen slide mode hides notes and expands the slide.
- Confirm retry/reload feedback appears when the server disappears.
- Confirm the page opens as a normal browser page with no app-install step.

## Presentation State And Controls

- Start from slide one and confirm the phone shows `1 / total`.
- Advance through at least three slides.
- Go backward at least once.
- Jump to a slide by number.
- Use first-slide and last-slide controls.
- Verify presenter notes update for each slide.
- Verify image-heavy slides render correctly.
- Verify total presentation timer keeps counting across slide changes.
- Verify current-slide timer resets on each slide change.
- Verify closing the document or switching away from Impress produces a clear not-ready state.

## Localization

- Run LibreOffice in English and confirm menu, dialogs, errors, and phone strings are understandable.
- Force or select Turkish and confirm the shipped Turkish catalog is used.
- Confirm untranslated keys do not appear in normal UI.
- Confirm icon-only phone previous/next controls remain usable without translated button text.

## Security And Protocol

- Confirm the QR/Copy URL fragment contains the session id and pairing verifier.
- Confirm relay links also include the admission token in the fragment.
- Confirm `/api/direct/state` without the session id returns forbidden.
- Confirm `/api/local/state` without session and secret headers returns forbidden.
- Confirm stale slide revision URLs return conflict.
- Confirm oversized command payloads are rejected.
- Confirm replayed encrypted frames are rejected by automated tests.
- Confirm relay traffic remains opaque encrypted protocol frames from the relay perspective.
- Confirm new security limitations are documented in `docs/security/e2ee.md`.

## Documentation And Release Notes

- Confirm README current status matches `docs/feature-matrix.md`.
- Confirm `TODO.md` matches implemented and planned behavior.
- Confirm `CHANGELOG.md` has an entry for the release candidate.
- Confirm `docs/release-readiness.md` reflects current gates.
- Confirm troubleshooting covers any new install, pairing, Safari, IPv6, tunnel, relay, or export issue found in this pass.
- Confirm README screenshots or placeholders match the current UI.

## Result Template

| Date | Version | Tester | Platform | LibreOffice | Phone Browser | Route | Result | Notes |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| YYYY-MM-DD | 0.x.y | Name | OS/version | LO version | Browser/version | Local/LocalTunnel/IPv6/Relay | Pass/Fail/Skip | Link issue or reason |
