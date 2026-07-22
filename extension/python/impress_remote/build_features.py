# SPDX-FileCopyrightText: 2026 Bora Yarkın
# SPDX-License-Identifier: GPL-3.0-only

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

FEATURES_FILE = Path(__file__).with_name("BUILD_FEATURES.json")

DEFAULT_FEATURES: dict[str, bool] = {
    "localtunnel": True,
    "relay": True,
}


def _coerce_bool(value: Any, default: bool) -> bool:
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.strip().lower() in {"1", "true", "yes", "on"}
    return bool(value)


def build_features() -> dict[str, bool]:
    features = dict(DEFAULT_FEATURES)
    try:
        payload = json.loads(FEATURES_FILE.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        payload = {}
    if isinstance(payload, dict):
        for key, default in DEFAULT_FEATURES.items():
            features[key] = _coerce_bool(payload.get(key), default)

    relay_override = os.environ.get("IMPRESS_REMOTE_ENABLE_RELAY")
    if relay_override is not None:
        features["relay"] = _coerce_bool(relay_override, features["relay"])
    return features


def feature_enabled(name: str) -> bool:
    return build_features().get(name, False)


def relay_enabled() -> bool:
    return feature_enabled("relay")


def localtunnel_enabled() -> bool:
    return feature_enabled("localtunnel")
