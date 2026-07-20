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
        "extension/Settings.xcs",
        "extension/Settings.xcu",
        "extension/python/impress_remote/component.py",
        "shared/webui/index.html",
        "localizations/en.json",
        "localizations/tr.json",
    ]
    missing = [path for path in required if not (ROOT / path).exists()]
    assert not missing


def test_python_component_manifest_entry_uses_python_component_media_type() -> None:
    manifest = (ROOT / "extension/META-INF/manifest.xml").read_text(encoding="utf-8")
    assert 'application/vnd.sun.star.uno-component;type=Python' in manifest


def test_extension_manifest_includes_settings_schema_and_data() -> None:
    manifest = (ROOT / "extension/META-INF/manifest.xml").read_text(encoding="utf-8")
    assert 'application/vnd.sun.star.configuration-schema' in manifest
    assert 'manifest:full-path="Settings.xcs"' in manifest
    assert 'manifest:full-path="Settings.xcu"' in manifest
