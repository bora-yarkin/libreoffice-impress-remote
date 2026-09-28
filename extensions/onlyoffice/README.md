<!-- SPDX-FileCopyrightText: 2026 Bora Yarkın -->
<!-- SPDX-License-Identifier: GPL-3.0-only -->

# ONLYOFFICE API Probe

This development plugin is the first Phase 0 feasibility slice for the
cross-suite companion. It exercises documented presentation APIs and reports
editor version, slide count, slide-show events, and speaker notes. Its manual
controls can start/end a show, navigate, and pause/resume it.

It does not connect to a phone or companion process, provide a whole-slide
preview, or claim support for ONLYOFFICE Docs, Desktop Editors, or Euro-Office.
Live behavior must be checked against the exact host editions and versions
before compatibility is claimed. The LibreOffice extension and its packaging
are not changed by this probe.

## Install for a desktop-editor check

1. Zip `config.json`, `index.html`, `plugin.js`, and `probe.css` with those files
   at the archive root, then change the archive extension to `.plugin`.
2. In ONLYOFFICE Desktop Editors, install that file with Plugin Manager.
3. Open a presentation, open **Plugins → Impress Remote API Probe**, and select
   **Read current editor slide and notes** before trying slideshow controls.
4. Check slide changes, presenter notes, and animation effects with a test
   presentation. The controls change slideshow state, so use a disposable or
   non-live presentation.

The plugin loads ONLYOFFICE's documented plugin SDK from
`https://onlyoffice.github.io/sdkjs-plugins/v1/plugins.js`; the editor must be
able to retrieve that official runtime script. Presenter notes are displayed
inside the plugin only. The probe does not send presentation data elsewhere.

Installation and behavior in ONLYOFFICE Docs and Euro-Office are not yet
verified. Consult [the cross-suite plan](../../docs/cross-suite-companion-plan.md)
for the remaining feasibility gates and capability matrix.
