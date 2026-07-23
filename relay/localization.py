# SPDX-FileCopyrightText: 2026 Bora Yarkın
# SPDX-License-Identifier: GPL-3.0-only

from __future__ import annotations

from functools import lru_cache
import json
from pathlib import Path
from string import Formatter
from typing import Any

DEFAULT_LOCALE = "en"
PACKAGE_LOCALIZATION_ROOT = Path(__file__).resolve().with_name("web") / "localizations"
SOURCE_LOCALIZATION_ROOT = Path(__file__).resolve().parents[3] / "shared" / "localizations"


def localization_root() -> Path:
    if (PACKAGE_LOCALIZATION_ROOT / f"{DEFAULT_LOCALE}.json").is_file():
        return PACKAGE_LOCALIZATION_ROOT
    return SOURCE_LOCALIZATION_ROOT


@lru_cache(maxsize=4)
def load_catalog(language: str = DEFAULT_LOCALE) -> dict[str, str]:
    path = localization_root() / f"{language}.json"
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        payload = {}
    if not isinstance(payload, dict):
        return {}
    return {str(key): str(value) for key, value in payload.items()}


def translate(key: str, **values: Any) -> str:
    text = load_catalog(DEFAULT_LOCALE).get(key, key)
    if not values:
        return text
    return Formatter().vformat(text, (), _SafeFormatValues(values))


class _SafeFormatValues(dict[str, Any]):
    def __missing__(self, key: str) -> str:
        return "{" + key + "}"
