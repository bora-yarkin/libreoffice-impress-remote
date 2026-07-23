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


def test_export_packaged_resource_wraps_flat_bundles_in_archive_named_folder(
    tmp_path: Path,
) -> None:
    module_file = _fake_module_file(tmp_path / "extension-root")
    archive_name = f"impress-remote-relay-python-{__version__}.zip"
    archive_path = tmp_path / "extension-root" / "resources" / archive_name
    archive_path.parent.mkdir()
    with ZipFile(archive_path, "w", ZIP_DEFLATED) as archive:
        archive.writestr("run-relay.py", "runner")
        archive.writestr("README.md", "relay docs")

    destination = tmp_path / "Downloads"
    result = export_packaged_resource("relay", destination, str(module_file))

    assert result.entries == 2
    export_root = destination / f"impress-remote-relay-python-{__version__}"
    assert (export_root / "run-relay.py").read_text(encoding="utf-8") == "runner"
    assert (export_root / "README.md").read_text(encoding="utf-8") == "relay docs"
    assert not (destination / "run-relay.py").exists()


def test_export_packaged_resource_rejects_unsafe_archive_members(tmp_path: Path) -> None:
    module_file = _fake_module_file(tmp_path / "extension-root")
    archive_path = tmp_path / "extension-root" / "resources" / _docs_archive_name()
    archive_path.parent.mkdir()
    with ZipFile(archive_path, "w", ZIP_DEFLATED) as archive:
        archive.writestr("../outside.txt", "nope")

    with pytest.raises(ValueError):
        export_packaged_resource("docs", tmp_path / "Downloads", str(module_file))
