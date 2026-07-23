# SPDX-FileCopyrightText: 2026 Bora Yarkın
# SPDX-License-Identifier: GPL-3.0-only

from __future__ import annotations

import base64
import hashlib
import json
from pathlib import Path

PACKAGE_WEB_ROOT = Path(__file__).resolve().with_name("web")
SHARED_WEB_ROOT = Path(__file__).resolve().parents[1] / "shared" / "webui"
LOCALIZATION_ROOT = Path(__file__).resolve().parents[1] / "shared" / "localizations"
DEFAULT_LOCALE = "en"
SRI_ASSETS = {
    'href="/app.css"': "app.css",
    'src="/app.js"': "app.js",
}


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
    if name == "index.html":
        index_path = web_root() / "index.html"
        html = index_path.read_text(encoding="utf-8")
        if " integrity=" in html:
            return html
        return _trusted_index_html(html)
    if name.startswith("localizations/"):
        if name == "localizations/manifest.json":
            path = web_root() / name
            if path.exists():
                return path.read_text(encoding="utf-8")
            return localization_manifest_text()
        path = web_root() / name
        if path.exists():
            return path.read_text(encoding="utf-8")
        return (LOCALIZATION_ROOT / Path(name).name).read_text(encoding="utf-8")
    return (web_root() / name).read_text(encoding="utf-8")


def localization_files() -> tuple[Path, ...]:
    packaged_root = web_root() / "localizations"
    if packaged_root.exists():
        files = tuple(
            sorted(
                path for path in packaged_root.glob("*.json") if path.name != "manifest.json"
            )
        )
        if files:
            return files
    return tuple(sorted(LOCALIZATION_ROOT.glob("*.json")))


def localization_manifest() -> dict[str, object]:
    return {
        "version": 1,
        "defaultLocale": DEFAULT_LOCALE,
        "locales": [path.stem for path in localization_files()],
    }


def localization_manifest_text() -> str:
    return json.dumps(localization_manifest(), indent=2, sort_keys=True) + "\n"


def _trusted_index_html(html: str) -> str:
    for marker, relative_name in SRI_ASSETS.items():
        source = web_root() / relative_name
        if not source.exists():
            continue
        digest = hashlib.sha256(source.read_bytes()).digest()
        integrity = "sha256-" + base64.b64encode(digest).decode("ascii")
        html = html.replace(marker, f'{marker} integrity="{integrity}"', 1)
    return html


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
        if relative_name == "index.html":
            data = read_web_asset("index.html").encode("utf-8")
        digest = hashlib.sha256(data).hexdigest()
        file_entries[relative_name] = {
            "sha256": digest,
            "sha256SRI": "sha256-"
            + base64.b64encode(hashlib.sha256(data).digest()).decode("ascii"),
            "bytes": len(data),
        }
        bundle_hash.update(relative_name.encode("utf-8"))
        bundle_hash.update(b"\0")
        bundle_hash.update(digest.encode("ascii"))
    if root == SHARED_WEB_ROOT or not (root / "localizations" / "manifest.json").exists():
        for path in localization_files():
            relative_name = f"localizations/{path.name}"
            data = path.read_bytes()
            digest = hashlib.sha256(data).hexdigest()
            file_entries[relative_name] = {
                "sha256": digest,
                "sha256SRI": "sha256-"
                + base64.b64encode(hashlib.sha256(data).digest()).decode("ascii"),
                "bytes": len(data),
            }
            bundle_hash.update(relative_name.encode("utf-8"))
            bundle_hash.update(b"\0")
            bundle_hash.update(digest.encode("ascii"))
    manifest_data = read_web_asset("localizations/manifest.json").encode("utf-8")
    manifest_digest = hashlib.sha256(manifest_data).hexdigest()
    file_entries["localizations/manifest.json"] = {
        "sha256": manifest_digest,
        "sha256SRI": "sha256-"
        + base64.b64encode(hashlib.sha256(manifest_data).digest()).decode("ascii"),
        "bytes": len(manifest_data),
    }
    bundle_hash.update(b"localizations/manifest.json\0")
    bundle_hash.update(manifest_digest.encode("ascii"))
    return {
        "version": 1,
        "bundleSha256": bundle_hash.hexdigest(),
        "files": file_entries,
    }
