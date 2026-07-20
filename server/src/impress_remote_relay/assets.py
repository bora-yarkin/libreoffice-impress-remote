# SPDX-FileCopyrightText: 2026 Bora Yarkın
# SPDX-License-Identifier: GPL-3.0-only

from __future__ import annotations

import hashlib
import json
from pathlib import Path

PACKAGE_WEB_ROOT = Path(__file__).resolve().with_name("web")
SHARED_WEB_ROOT = Path(__file__).resolve().parents[3] / "shared" / "webui"
LOCALIZATION_ROOT = Path(__file__).resolve().parents[3] / "localizations"


def _has_packaged_content(path: Path) -> bool:
    if path.is_file():
        return True
    if not path.is_dir():
        return False
    return (path / "index.html").exists()


def web_root() -> Path:
    if _has_packaged_content(PACKAGE_WEB_ROOT):
        return PACKAGE_WEB_ROOT
    if _has_packaged_content(SHARED_WEB_ROOT):
        return SHARED_WEB_ROOT
    return PACKAGE_WEB_ROOT


def read_web_asset(name: str) -> str:
    if name.startswith("localizations/"):
        path = web_root() / name
        if path.exists():
            return path.read_text(encoding="utf-8")
        return (LOCALIZATION_ROOT / Path(name).name).read_text(encoding="utf-8")
    return (web_root() / name).read_text(encoding="utf-8")


def web_asset_manifest() -> dict[str, object]:
    root = web_root()
    manifest_path = root / "asset-manifest.json"
    if manifest_path.exists():
        payload = json.loads(manifest_path.read_text(encoding="utf-8"))
        if isinstance(payload, dict):
            return payload

    file_entries: dict[str, dict[str, object]] = {}
    bundle_hash = hashlib.sha256()
    for path in sorted(root.rglob("*")):
        if not path.is_file() or path.name == "asset-manifest.json":
            continue
        relative_name = str(path.relative_to(root)).replace("\\", "/")
        data = path.read_bytes()
        digest = hashlib.sha256(data).hexdigest()
        file_entries[relative_name] = {"sha256": digest, "bytes": len(data)}
        bundle_hash.update(relative_name.encode("utf-8"))
        bundle_hash.update(b"\0")
        bundle_hash.update(digest.encode("ascii"))
    if root == SHARED_WEB_ROOT:
        for path in sorted(LOCALIZATION_ROOT.glob("*.json")):
            relative_name = f"localizations/{path.name}"
            data = path.read_bytes()
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
