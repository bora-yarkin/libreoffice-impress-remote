# SPDX-FileCopyrightText: 2026 Bora Yarkın
# SPDX-License-Identifier: GPL-3.0-only

from __future__ import annotations

from functools import lru_cache
import json
import locale
import os
from pathlib import Path
from string import Formatter
from typing import Any

from impress_remote.paths import module_file_path

DEFAULT_LOCALE = "en"


def localization_root() -> Path:
    module_path = module_file_path(__file__)
    packaged_root = module_path.parents[2] / "web" / "localizations"
    if _has_catalog(packaged_root):
        return packaged_root
    shared_root = module_path.parents[3] / "shared" / "localizations"
    if _has_catalog(shared_root):
        return shared_root
    return packaged_root


def _has_catalog(path: Path) -> bool:
    return (path / f"{DEFAULT_LOCALE}.json").is_file()


def available_locales() -> tuple[str, ...]:
    root = localization_root()
    locales = sorted(path.stem for path in root.glob("*.json") if path.name != "manifest.json")
    if DEFAULT_LOCALE not in locales and (root / f"{DEFAULT_LOCALE}.json").is_file():
        locales.insert(0, DEFAULT_LOCALE)
    return tuple(locales or (DEFAULT_LOCALE,))


def localization_manifest() -> dict[str, object]:
    return {
        "version": 1,
        "defaultLocale": DEFAULT_LOCALE,
        "locales": list(available_locales()),
    }


def current_locale() -> str:
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


def normalize_locale(value: str) -> str:
    language = value.strip().replace("-", "_").split(".", 1)[0].split("_", 1)[0].lower()
    return language if language in available_locales() else ""


@lru_cache(maxsize=16)
def load_catalog(language: str = DEFAULT_LOCALE) -> dict[str, str]:
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
    safe_values = _SafeFormatValues(values)
    return Formatter().vformat(template, (), safe_values)


class _SafeFormatValues(dict[str, Any]):
    def __missing__(self, key: str) -> str:
        return "{" + key + "}"
