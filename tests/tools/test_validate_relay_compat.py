# SPDX-FileCopyrightText: 2026 Bora Yarkın
# SPDX-License-Identifier: GPL-3.0-only

from tools.validate_relay_compat import check_asset_manifest


def test_asset_manifest_compatibility_check_accepts_required_files(monkeypatch) -> None:
    def fake_read_json(_url: str):
        return 200, {
            "files": {
                "index.html": {},
                "app.js": {},
                "app.css": {},
                "localizations/manifest.json": {},
            }
        }

    monkeypatch.setattr("tools.validate_relay_compat.read_json", fake_read_json)

    result = check_asset_manifest("https://relay.example/")

    assert result.ok
    assert result.name == "asset-manifest"
