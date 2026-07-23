# SPDX-FileCopyrightText: 2026 Bora Yarkin
# SPDX-License-Identifier: GPL-3.0-only

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from zipfile import ZipFile

from impress_remote import __version__
from impress_remote.localization import translate
from impress_remote.paths import module_file_path


@dataclass(frozen=True)
class ResourceExport:
    kind: str
    destination: Path
    entries: int


RESOURCE_ARCHIVES = {
    "relay": f"impress-remote-relay-python-{__version__}.zip",
    "docs": f"impress-remote-docs-{__version__}.zip",
}


def default_export_directory() -> Path:
    downloads = Path.home() / "Downloads"
    if downloads.is_dir():
        return downloads
    return Path.home()


def packaged_resource_path(kind: str, module_file: str = __file__) -> Path:
    archive_name = RESOURCE_ARCHIVES.get(kind)
    if archive_name is None:
        raise ValueError(translate("resource.error.unknownKind", kind=kind))

    module_path = module_file_path(module_file)
    packaged_path = module_path.parents[2] / "resources" / archive_name
    if packaged_path.is_file():
        return packaged_path

    source_tree_path = module_path.parents[3] / "dist" / archive_name
    if source_tree_path.is_file():
        return source_tree_path

    raise FileNotFoundError(translate("resource.error.notBundled", name=archive_name))


def export_packaged_resource(
    kind: str,
    destination: Path | None = None,
    module_file: str = __file__,
) -> ResourceExport:
    archive_path = packaged_resource_path(kind, module_file)
    target_dir = (destination or default_export_directory()).expanduser().resolve()
    target_dir.mkdir(parents=True, exist_ok=True)

    entries = 0
    with ZipFile(archive_path) as archive:
        for member in archive.infolist():
            if member.is_dir():
                continue
            output_path = (target_dir / member.filename).resolve()
            if not output_path.is_relative_to(target_dir):
                raise ValueError(translate("resource.error.unsafeArchive", name=member.filename))
            output_path.parent.mkdir(parents=True, exist_ok=True)
            with archive.open(member) as source, output_path.open("wb") as target:
                target.write(source.read())
            entries += 1

    return ResourceExport(kind=kind, destination=target_dir, entries=entries)
