# SPDX-FileCopyrightText: 2026 Bora Yarkin
# SPDX-License-Identifier: GPL-3.0-only

from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile

import pytest

from impress_remote import __version__
from impress_remote.resources import export_packaged_resource


def _fake_module_file(root: Path) -> Path:
    module_file = root / "python" / "impress_remote" / "resources.py"
    module_file.parent.mkdir(parents=True)
    module_file.write_text("", encoding="utf-8")
    return module_file


def _docs_archive_name() -> str:
    return f"impress-remote-docs-{__version__}.zip"


def _cloudflare_archive_name() -> str:
    return f"impress-remote-relay-cloudflare-{__version__}.zip"


def test_export_packaged_resource_extracts_versioned_bundle(tmp_path: Path) -> None:
    module_file = _fake_module_file(tmp_path / "extension-root")
    archive_path = tmp_path / "extension-root" / "resources" / _docs_archive_name()
    archive_path.parent.mkdir()
    with ZipFile(archive_path, "w", ZIP_DEFLATED) as archive:
        archive.writestr(f"impress-remote-docs-{__version__}/README.md", "docs")

    destination = tmp_path / "Downloads"
    result = export_packaged_resource("docs", destination, str(module_file))

    assert result.entries == 1
    assert result.destination == destination
    assert (destination / f"impress-remote-docs-{__version__}" / "README.md").read_text(
        encoding="utf-8"
    ) == "docs"


def test_export_packaged_resource_extracts_cloudflare_bundle(tmp_path: Path) -> None:
    module_file = _fake_module_file(tmp_path / "extension-root")
    archive_path = tmp_path / "extension-root" / "resources" / _cloudflare_archive_name()
    archive_path.parent.mkdir()
    with ZipFile(archive_path, "w", ZIP_DEFLATED) as archive:
        archive.writestr(f"impress-remote-relay-cloudflare-{__version__}/wrangler.toml", "cfg")

    destination = tmp_path / "Downloads"
    result = export_packaged_resource("cloudflare", destination, str(module_file))

    assert result.entries == 1
    assert (
        destination / f"impress-remote-relay-cloudflare-{__version__}" / "wrangler.toml"
    ).read_text(encoding="utf-8") == "cfg"


def test_export_packaged_resource_rejects_unsafe_archive_members(tmp_path: Path) -> None:
    module_file = _fake_module_file(tmp_path / "extension-root")
    archive_path = tmp_path / "extension-root" / "resources" / _docs_archive_name()
    archive_path.parent.mkdir()
    with ZipFile(archive_path, "w", ZIP_DEFLATED) as archive:
        archive.writestr("../outside.txt", "nope")

    with pytest.raises(ValueError):
        export_packaged_resource("docs", tmp_path / "Downloads", str(module_file))
