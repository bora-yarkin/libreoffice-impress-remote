# SPDX-FileCopyrightText: 2026 Bora Yarkın
# SPDX-License-Identifier: GPL-3.0-only

from __future__ import annotations

import hashlib
import json
import shutil
from pathlib import Path
from zipfile import ZipFile

ROOT = Path(__file__).resolve().parents[1]
SHARED_WEB_ROOT = ROOT / "shared" / "webui"


def iter_webui_files() -> tuple[Path, ...]:
    return tuple(
        sorted(
            path
            for path in SHARED_WEB_ROOT.rglob("*")
            if path.is_file() and "__pycache__" not in path.parts
        )
    )


def build_webui_manifest() -> dict[str, object]:
    file_entries: dict[str, dict[str, object]] = {}
    bundle_hash = hashlib.sha256()
    for source in iter_webui_files():
        relative_name = str(source.relative_to(SHARED_WEB_ROOT)).replace("\\", "/")
        data = source.read_bytes()
        digest = hashlib.sha256(data).hexdigest()
        file_entries[relative_name] = {"sha256": digest, "bytes": len(data)}
        bundle_hash.update(relative_name.encode("utf-8"))
        bundle_hash.update(b"\0")
        bundle_hash.update(digest.encode("ascii"))
    return {
        "version": 1,
        "bundleSha256": bundle_hash.hexdigest(),
        "files": file_entries,
    }


def build_webui_manifest_text() -> str:
    return json.dumps(build_webui_manifest(), indent=2, sort_keys=True) + "\n"


def copy_webui(destination: Path) -> tuple[Path, ...]:
    copied: list[Path] = []
    destination.mkdir(parents=True, exist_ok=True)
    for source in iter_webui_files():
        target = destination / source.relative_to(SHARED_WEB_ROOT)
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, target)
        copied.append(target)
    manifest_path = destination / "asset-manifest.json"
    manifest_path.write_text(build_webui_manifest_text(), encoding="utf-8")
    copied.append(manifest_path)
    return tuple(copied)


def add_webui_to_zip(package: ZipFile, destination_root: str) -> None:
    for source in iter_webui_files():
        package.write(
            source,
            Path(destination_root) / source.relative_to(SHARED_WEB_ROOT),
        )
    package.writestr(
        str(Path(destination_root) / "asset-manifest.json"),
        build_webui_manifest_text(),
    )
