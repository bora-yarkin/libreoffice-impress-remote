# SPDX-FileCopyrightText: 2026 Bora Yarkın
# SPDX-License-Identifier: GPL-3.0-only

from impress_remote.localization import (
    DEFAULT_LOCALE,
    available_locales,
    localization_manifest,
    load_catalog,
    normalize_locale,
    translate,
)


def test_loads_english_catalog() -> None:
    catalog = load_catalog(DEFAULT_LOCALE)

    assert catalog["component.menu.startRemote"] == "Start Remote"


def test_translates_turkish_catalog_for_testing() -> None:
    assert translate("component.menu.startRemote", language="tr") == "Kumandayi Baslat"


def test_falls_back_to_english_for_missing_turkish_key() -> None:
    assert translate("missing.key", language="tr") == "missing.key"
    assert translate("component.menu.stopRemote", language="tr") == "Kumandayi Durdur"


def test_normalizes_locale_codes() -> None:
    assert normalize_locale("tr_TR.UTF-8") == "tr"
    assert normalize_locale("en-US") == "en"
    assert normalize_locale("de_DE.UTF-8") == ""


def test_reports_available_locales_for_manifest_driven_clients() -> None:
    locales = available_locales()
    manifest = localization_manifest()

    assert DEFAULT_LOCALE in locales
    assert "tr" in locales
    assert manifest["defaultLocale"] == DEFAULT_LOCALE
    manifest_locales = manifest["locales"]
    assert isinstance(manifest_locales, list)
    assert "tr" in manifest_locales


def test_formats_localized_message_values() -> None:
    assert (
        translate(
            "component.status.slideOf",
            language="en",
            message="Ready",
            current=2,
            total=9,
        )
        == "Ready. Slide 2 of 9."
    )
