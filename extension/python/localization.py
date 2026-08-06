# SPDX-FileCopyrightText: 2026 Bora Yarkın
# SPDX-License-Identifier: GPL-3.0-only

"""Locale discovery, catalog loading, and safe message formatting.

The same catalog layout is used by the extension and the relay bundle. The
module falls back to English when a locale or translation is unavailable so
localization failures cannot prevent the remote from starting.
"""

from __future__ import annotations

from functools import lru_cache
import json
import locale
import os
from pathlib import Path
from string import Formatter
from typing import Any

from paths import module_file_path

DEFAULT_LOCALE = "en"


def localization_root() -> Path:
    """Choose packaged catalogs first and source-tree catalogs in development."""
    module_path = module_file_path(__file__)
    packaged_root = module_path.parents[1] / "web" / "localizations"
    if _has_catalog(packaged_root):
        return packaged_root
    shared_root = module_path.parents[2] / "shared" / "localizations"
    if _has_catalog(shared_root):
        return shared_root
    return packaged_root


def _has_catalog(path: Path) -> bool:
    """Return whether a locale catalog exists at *path*."""
    return (path / f"{DEFAULT_LOCALE}.json").is_file()


def available_locales() -> tuple[str, ...]:
    """Return sorted locale names available to the local UI."""
    root = localization_root()
    locales = sorted(path.stem for path in root.glob("*.json") if path.name != "manifest.json")
    if DEFAULT_LOCALE not in locales and (root / f"{DEFAULT_LOCALE}.json").is_file():
        locales.insert(0, DEFAULT_LOCALE)
    return tuple(locales or (DEFAULT_LOCALE,))


def localization_manifest() -> dict[str, object]:
    """Return the locale manifest served to the browser."""
    return {
        "version": 1,
        "defaultLocale": DEFAULT_LOCALE,
        "locales": list(available_locales()),
    }


def current_locale() -> str:
    """Read the user's OS locale without allowing locale errors to escape."""
    for value in (
        os.environ.get("IMPRESS_REMOTE_LANG", ""),
        os.environ.get("LANGUAGE", "").split(":", 1)[0],
        os.environ.get("LC_ALL", ""),
        os.environ.get("LC_MESSAGES", ""),
        os.environ.get("LANG", ""),
        locale.getlocale()[0] or "",
    ):
        normalized = normalize_locale(value)
        if normalized:
            return normalized
    return DEFAULT_LOCALE


def _normalize_locale_name(value: str) -> str:
    """Normalize separators and casing for locale lookup."""
    return value.strip().replace("_", "-").split(".", 1)[0].lower()


def _locale_candidates(value: str) -> list[str]:
    """Return progressively broader locale candidates for fallback lookup."""
    normalized = _normalize_locale_name(value)
    if not normalized:
        return []
    parts = [part for part in normalized.split("-") if part]
    if not parts:
        return []
    candidates: list[str] = []
    for index in range(len(parts), 0, -1):
        candidate = "-".join(parts[:index])
        if candidate not in candidates:
            candidates.append(candidate)
    return candidates


def normalize_locale(value: str) -> str:
    """Resolve a requested locale to the closest shipped catalog."""
    available = available_locales()
    available_lookup = {_normalize_locale_name(locale): locale for locale in available}
    for candidate in _locale_candidates(value):
        if candidate in available_lookup:
            return available_lookup[candidate]
    if not value:
        return ""
    base = _normalize_locale_name(value).split("-", 1)[0]
    return available_lookup.get(base, "")


@lru_cache(maxsize=16)
def load_catalog(language: str = DEFAULT_LOCALE) -> dict[str, str]:
    """Load one catalog, falling back to English when it is unavailable."""
    normalized = normalize_locale(language) or DEFAULT_LOCALE
    path = localization_root() / f"{normalized}.json"
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        payload = {}
    if not isinstance(payload, dict):
        return {}
    return {str(key): str(value) for key, value in payload.items()}


def translate(key: str, language: str | None = None, **values: Any) -> str:
    """Translate *key* and safely interpolate values into its message."""
    selected_language = normalize_locale(language or "") or current_locale()
    text = load_catalog(selected_language).get(key)
    if text is None and selected_language != DEFAULT_LOCALE:
        text = load_catalog(DEFAULT_LOCALE).get(key)
    if text is None:
        return key
    if not values:
        return text
    return _format_message(text, values)


def _format_message(template: str, values: dict[str, Any]) -> str:
    """Format a message while preserving unknown placeholders verbatim."""
    safe_values = _SafeFormatValues(values)
    return Formatter().vformat(template, (), safe_values)


class _SafeFormatValues(dict[str, Any]):
    """Formatting mapping that leaves missing localization fields visible."""
    def __missing__(self, key: str) -> str:
        return "{" + key + "}"
