# SPDX-FileCopyrightText: 2026 Bora Yarkın
# SPDX-License-Identifier: GPL-3.0-only

from __future__ import annotations

import shutil
from pathlib import Path
import sys
from zipfile import ZIP_DEFLATED, ZipFile

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.project_version import read_project_version  # noqa: E402
from tools.shared_webui import copy_webui  # noqa: E402

DIST = ROOT / "dist"
SOURCE = ROOT / "deploy" / "cloudflare"


def project_version() -> str:
    return read_project_version()


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


def build_cloudflare_bundle(dist_dir: Path = DIST) -> tuple[Path, Path]:
    version = project_version()
    dist_dir.mkdir(parents=True, exist_ok=True)
    bundle_dir = dist_dir / f"impress-remote-relay-cloudflare-{version}"
    archive_path = dist_dir / f"impress-remote-relay-cloudflare-{version}.zip"

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
                archive.write(path, path.relative_to(dist_dir))

    return bundle_dir, archive_path


def main() -> None:
    bundle_dir, archive_path = build_cloudflare_bundle()
    print(bundle_dir)
    print(archive_path)


if __name__ == "__main__":
    main()
