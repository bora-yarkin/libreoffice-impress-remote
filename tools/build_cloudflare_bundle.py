# SPDX-FileCopyrightText: 2026 Bora Yarkın
# SPDX-License-Identifier: GPL-3.0-only

from __future__ import annotations

import shutil
from pathlib import Path
import tomllib
from zipfile import ZIP_DEFLATED, ZipFile

from tools.shared_webui import copy_webui

ROOT = Path(__file__).resolve().parents[1]
DIST = ROOT / "dist"
SOURCE = ROOT / "deploy" / "cloudflare"


def project_version() -> str:
    with (ROOT / "pyproject.toml").open("rb") as handle:
        data = tomllib.load(handle)
    return str(data["project"]["version"])


def copy_tree(source: Path, destination: Path) -> None:
    for item in source.rglob("*"):
        if "__pycache__" in item.parts or item.name == ".DS_Store":
            continue
        target = destination / item.relative_to(source)
        if item.is_dir():
            target.mkdir(parents=True, exist_ok=True)
            continue
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(item, target)


def build_cloudflare_bundle() -> tuple[Path, Path]:
    version = project_version()
    bundle_dir = DIST / f"impress-remote-relay-cloudflare-{version}"
    archive_path = DIST / f"impress-remote-relay-cloudflare-{version}.zip"

    if bundle_dir.exists():
        shutil.rmtree(bundle_dir)
    if archive_path.exists():
        archive_path.unlink()

    bundle_dir.mkdir(parents=True, exist_ok=True)
    copy_tree(SOURCE, bundle_dir)
    copy_webui(bundle_dir / "public")

    with ZipFile(archive_path, "w", ZIP_DEFLATED) as archive:
        for path in sorted(bundle_dir.rglob("*")):
            if path.is_file():
                archive.write(path, path.relative_to(DIST))

    return bundle_dir, archive_path


def main() -> None:
    bundle_dir, archive_path = build_cloudflare_bundle()
    print(bundle_dir)
    print(archive_path)


if __name__ == "__main__":
    main()
