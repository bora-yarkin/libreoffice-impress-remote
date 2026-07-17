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
SERVER_ROOT = ROOT / "server"
SERVER_PACKAGE = SERVER_ROOT / "src" / "impress_remote_relay"
DEPLOY_ROOT = ROOT / "deploy" / "python-relay"


def project_version() -> str:
    with (ROOT / "pyproject.toml").open("rb") as handle:
        data = tomllib.load(handle)
    return str(data["project"]["version"])


def copy_python_package(source: Path, destination: Path) -> None:
    for path in sorted(source.rglob("*.py")):
        if "__pycache__" in path.parts:
            continue
        target = destination / path.relative_to(source)
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(path, target)


def copy_deploy_files(source: Path, destination: Path) -> None:
    for path in sorted(source.rglob("*")):
        if (
            path.is_dir()
            or path.name == ".DS_Store"
            or "__pycache__" in path.parts
            or path.suffix in {".pyc", ".pyo"}
        ):
            continue
        target = destination / path.relative_to(source)
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(path, target)


def build_bundle() -> tuple[Path, Path]:
    version = project_version()
    bundle_dir = DIST / f"impress-remote-relay-python-{version}"
    archive_path = DIST / f"impress-remote-relay-python-{version}.zip"

    if bundle_dir.exists():
        shutil.rmtree(bundle_dir)
    if archive_path.exists():
        archive_path.unlink()

    bundle_dir.mkdir(parents=True, exist_ok=True)
    shutil.copy2(ROOT / "LICENSE", bundle_dir / "LICENSE")
    copy_deploy_files(DEPLOY_ROOT, bundle_dir)
    relay_src = bundle_dir / "src" / "impress_remote_relay"
    relay_src.mkdir(parents=True, exist_ok=True)
    copy_python_package(SERVER_PACKAGE, relay_src)
    copy_webui(relay_src / "web")

    with ZipFile(archive_path, "w", ZIP_DEFLATED) as archive:
        for path in sorted(bundle_dir.rglob("*")):
            if path.is_file():
                archive.write(path, path.relative_to(DIST))

    return bundle_dir, archive_path


def main() -> None:
    bundle_dir, archive_path = build_bundle()
    print(bundle_dir)
    print(archive_path)


if __name__ == "__main__":
    main()
