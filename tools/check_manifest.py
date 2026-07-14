# SPDX-FileCopyrightText: 2026 Bora Yarkın
# SPDX-License-Identifier: GPL-3.0-only

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REQUIRED = [
    "extension/META-INF/manifest.xml",
    "extension/description.xml",
    "extension/Addons.xcu",
    "extension/ProtocolHandler.xcu",
    "extension/web/index.html",
    "extension/python/impress_remote/component.py",
]


def test_required_files_exist() -> None:
    missing = [path for path in REQUIRED if not (ROOT / path).exists()]
    assert not missing, missing
