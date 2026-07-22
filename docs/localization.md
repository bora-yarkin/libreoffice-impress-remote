<!-- SPDX-FileCopyrightText: 2026 Bora Yarkın -->
<!-- SPDX-License-Identifier: GPL-3.0-only -->

# Localization

The project ships English as the source catalog and Turkish as the first test translation. Runtime code, the LibreOffice UI, and the phone UI load catalogs from `shared/localizations/` in the source tree.

## Import A Translation

Translation files can be plain key/value JSON named after the locale:

```json
{
  "component.menu.startRemote": "Start Remote"
}
```

They can also include explicit metadata:

```json
{
  "locale": "de-DE",
  "messages": {
    "component.menu.startRemote": "Fernbedienung starten"
  }
}
```

Import with:

```sh
make localization-import ARGS="path/to/de-DE.json"
```

The importer rejects unknown keys and placeholder mismatches such as translating `{name}` as `{nombre}`. By default it also rejects incomplete catalogs. Use `--allow-incomplete` only when intentionally relying on English fallback:

```sh
make localization-import ARGS="--allow-incomplete path/to/de-DE.json"
```

## Runtime Discovery

The packaged phone UI and relay bundles expose `/localizations/manifest.json`. The phone UI reads that manifest before choosing the browser language, so imported catalogs do not require editing `shared/webui/app.js`.
