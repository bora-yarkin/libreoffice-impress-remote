<!-- SPDX-FileCopyrightText: 2026 Bora Yarkın -->
<!-- SPDX-License-Identifier: GPL-3.0-only -->

# Test Before Release

Use this checklist before creating a preview release. It is intentionally practical: CI proves the package can be built and the protocol code still works, while this document catches real LibreOffice, browser, phone, and network behavior that automated tests do not fully cover yet.

Record the date, OS, LibreOffice version, phone browser, route, and result for every manual run. If a feature cannot be tested in the current environment, mark it as skipped with the reason instead of silently treating it as passed.

## Release Candidate Setup

- Confirm the root `VERSION` file contains the release candidate version.
- Run `make clean`.
- Run `make venv`.
- Run `make lint`.
- Run `make test`.
- Run `make release-full`.
- Confirm `dist/libreoffice-impress-remote-<version>.oxt` exists.
- Confirm the Python relay, Cloudflare relay, and docs bundles exist in `dist/`.
- Install the generated `.oxt` into a clean LibreOffice user profile when possible.
- Use an Impress document with at least five slides, slide titles, presenter notes, and one image-heavy slide.

## OXT Install And Menu Integration

- Open LibreOffice Impress.
- Install the generated `.oxt` through Extension Manager.
- Restart LibreOffice.
- Confirm `Slide Show -> Presentation Remote` appears in Impress.
- Confirm the Presentation Remote menu does not appear in Writer, Calc, or the LibreOffice start center.
- Confirm `Start Remote` is visible before the server starts.
- Start the remote and confirm the same menu item changes to `Stop Remote`.
- Stop the remote and confirm the menu item changes back to `Start Remote`.
- Confirm `Advanced Remote Settings` opens from the Presentation Remote submenu.
- Confirm toolbar or notebookbar buttons appear near the built-in slideshow controls where LibreOffice supports addon toolbar merging.

## Advanced Remote Settings

- Open `Advanced Remote Settings`.
- Confirm route selection includes Auto, Local, Direct IPv6, and Relay.
- Confirm local port, local listener, direct IPv6, and relay settings persist after closing and reopening the dialog.
- Confirm route status shows useful guidance when IPv6 or relay is unavailable.
- Confirm the manual link is available as a backup.
- Export the bundled Python relay package and confirm the zip filename matches the extension version.
- Export the bundled Cloudflare relay package and confirm the zip filename matches the extension version.
- Export the bundled documentation package and confirm the zip filename matches the extension version.
- Confirm export to Downloads works when folder selection is unavailable.

## Local Same-Wi-Fi Mode

- Connect the desktop and phone to the same Wi-Fi network.
- In Impress, choose Auto or Local route.
- Start Remote.
- Scan the QR code from the phone.
- Confirm the QR popup closes when the phone connects.
- Confirm LibreOffice starts the slideshow from the first slide after pairing.
- Confirm the phone shows the current slide image pinned at the top.
- Confirm presenter notes scroll independently while the slide and controls stay fixed.
- Tap the slide and confirm it advances.
- Use the next button and confirm it advances.
- Use the previous button and confirm it goes back.
- Confirm the slide counter is shown as only `current / total`.
- Confirm there is no settings UI on the phone.
- Stop Remote from LibreOffice and confirm the phone shows a disconnected or retry state.

## Hotspot Local Mode

- Turn on phone hotspot.
- Connect the desktop to the phone hotspot.
- Start Remote in Auto or Local route.
- Scan the QR code.
- Confirm pairing works through the hotspot address.
- Confirm slide image, notes, tap-to-advance, previous, and next all work.
- Stop Remote and confirm the listener is torn down.

## Safari Local Compatibility

- Use Safari on iPhone or iPad over same Wi-Fi or hotspot.
- Scan the local QR code.
- Confirm Safari does not show the Web Crypto unavailable error.
- Confirm the authenticated local fallback can read state and send previous/next commands.
- Confirm relay and direct IPv6 routes still require encrypted Web Crypto support.
- Confirm the manual link works if QR scanning fails.

## Direct IPv6 Mode

- Test on a network where the desktop has a globally reachable IPv6 address.
- Enable Direct IPv6 in Advanced Remote Settings.
- Select Direct IPv6 manually.
- Start Remote.
- Confirm LibreOffice advertises only global IPv6 addresses, not link-local or private addresses.
- Scan the QR code from a phone on a network that can reach the desktop IPv6 address.
- Confirm encrypted state, slide assets, and commands work.
- Disconnect the phone and reconnect with the same QR/manual link.
- Confirm Auto route falls back cleanly when Direct IPv6 is unavailable.
- If no public IPv6 environment is available, record this test as skipped with the network reason.

## Python Relay Mode

- Export the bundled Python relay package from Advanced Remote Settings.
- Extract it outside the repository.
- Run the foreground relay helper.
- Confirm `/health` returns successfully.
- Configure the relay URL in LibreOffice.
- Select Relay route manually.
- Start Remote.
- Scan the relay QR code.
- Confirm the phone receives the relay-hosted shared web UI.
- Confirm slide image, presenter notes, previous, next, and tap-to-advance work.
- Confirm LibreOffice detects the joined phone and starts the slideshow from the first slide.
- Confirm stopping Remote disconnects the relay plugin session.
- Confirm the relay logs do not contain presenter notes, slide text, commands, or image data in decrypted form.

## Python Relay Service Scripts

- On Linux, run the install script on a disposable server or VM.
- Confirm it chooses an available port or respects the supplied port.
- Confirm the service starts automatically and `/health` works.
- Run the Linux uninstaller and confirm the service is removed.
- On Windows, install the service on a disposable machine or VM.
- Confirm the Windows service starts automatically and `/health` works.
- Run the Windows uninstaller and confirm the service is removed.
- If Linux or Windows is unavailable for this release, record the service-script test as skipped with the platform reason.

## Cloudflare Relay Mode

- Export the bundled Cloudflare relay package from Advanced Remote Settings.
- Deploy the Worker and Durable Object from the generated bundle.
- Confirm the deployed `/health` endpoint returns successfully.
- Configure the Cloudflare relay URL in LibreOffice.
- Select Relay route manually.
- Start Remote.
- Scan the QR code.
- Confirm slide image, presenter notes, previous, next, and tap-to-advance work.
- Confirm the Cloudflare relay does not require editing shared web UI files after bundle generation.
- Confirm relay content remains opaque encrypted protocol frames from the relay perspective.

## Phone Browser UI

- Test iOS Safari.
- Test Chrome on Android.
- Test Firefox on Android when available.
- Confirm the slide is pinned to the top at maximum useful width.
- Confirm the bottom controls stay pinned.
- Confirm presenter notes are the only scrollable region.
- Confirm button icons are understandable without translated labels.
- Confirm offline, reconnect, retry, and reload states are visible when the server disappears.
- Confirm the PWA metadata does not break normal browser usage.

## Presentation State And Controls

- Start from slide one and confirm the phone shows `1 / total`.
- Advance through at least three slides.
- Go backward at least once.
- Verify presenter notes update for each slide.
- Verify image-heavy slides render correctly.
- Verify blank screen state appears correctly if blanking is triggered.
- Verify end-of-deck state appears correctly on the final slide.
- Verify closing the document or switching away from Impress produces a clear not-ready state.

## Localization

- Run LibreOffice with English UI settings and confirm menu, dialog, errors, and phone strings are understandable.
- Run LibreOffice with Turkish UI settings or force the Turkish catalog if locale switching is not available.
- Confirm menu labels, dialog labels, status text, errors, and phone copy use Turkish strings.
- Confirm untranslated keys are visible only as a test failure, not in normal UI.
- Confirm the phone remote remains usable without translated next/previous button text.

## Security And Protocol

- Confirm the QR/manual link fragment contains the session and pairing verifier, not query parameters sent to the relay.
- Confirm `/api/direct/state` without the session id returns forbidden.
- Confirm `/api/local/state` without session and secret headers returns forbidden.
- Confirm a stale slide revision URL returns a conflict instead of a mismatched slide image.
- Confirm local/direct command payloads larger than the configured limit are rejected.
- Confirm replayed encrypted frames are rejected by automated tests.
- Confirm the relay can forward frames but cannot decrypt presenter notes, commands, or slide images.
- Confirm any new security limitation is documented in `docs/security/e2ee.md`.

## Documentation And Release Notes

- Confirm the README current status matches `docs/feature-matrix.md`.
- Confirm `TODO.md` has accurate Implemented and Planned sections.
- Confirm `CHANGELOG.md` has an entry for the release candidate.
- Confirm `docs/release-readiness.md` reflects the current gates.
- Confirm troubleshooting covers any install, pairing, Safari, IPv6, relay, or resource-export issue discovered during this test pass.
- Confirm screenshots or README placeholders match the current UI before publishing.

## Result Template

| Date | Version | Tester | Platform | LibreOffice | Phone Browser | Route | Result | Notes |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| YYYY-MM-DD | 0.x.y | Name | OS/version | LO version | Browser/version | Local/IPv6/Relay | Pass/Fail/Skip | Link issue or reason |
