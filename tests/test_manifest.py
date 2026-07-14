# SPDX-FileCopyrightText: 2026 Bora Yarkın
# SPDX-License-Identifier: GPL-3.0-only

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_extension_manifest_files_exist() -> None:
    required = [
        "extension/META-INF/manifest.xml",
        "extension/description.xml",
        "extension/Addons.xcu",
        "extension/ProtocolHandler.xcu",
        "extension/python/impress_remote/component.py",
        "extension/web/index.html",
    ]
    missing = [path for path in required if not (ROOT / path).exists()]
    assert not missing
