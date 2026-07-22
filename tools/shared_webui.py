# SPDX-FileCopyrightText: 2026 Bora Yarkın
# SPDX-License-Identifier: GPL-3.0-only

from __future__ import annotations

import hashlib
import json
import base64
import shutil
from pathlib import Path
from zipfile import ZipFile

ROOT = Path(__file__).resolve().parents[1]
SHARED_WEB_ROOT = ROOT / "shared" / "webui"
LOCALIZATION_ROOT = ROOT / "shared" / "localizations"
DEFAULT_LOCALE = "en"
SRI_ASSETS = {
    'href="/app.css"': "app.css",
    'src="/app.js"': "app.js",
}


def iter_webui_files() -> tuple[tuple[Path, Path], ...]:
    entries: list[tuple[Path, Path]] = []
    for source in sorted(SHARED_WEB_ROOT.rglob("*")):
        if source.is_file() and "__pycache__" not in source.parts:
            entries.append((source, source.relative_to(SHARED_WEB_ROOT)))
    for source in sorted(LOCALIZATION_ROOT.glob("*.json")):
        entries.append((source, Path("localizations") / source.name))
    return tuple(entries)


def iter_localization_files() -> tuple[Path, ...]:
    return tuple(sorted(LOCALIZATION_ROOT.glob("*.json")))


def build_localization_manifest() -> dict[str, object]:
    locales = [path.stem for path in iter_localization_files()]
    return {
        "version": 1,
        "defaultLocale": DEFAULT_LOCALE,
        "locales": locales,
    }


def build_localization_manifest_text() -> str:
    return json.dumps(build_localization_manifest(), indent=2, sort_keys=True) + "\n"


def _asset_sri(source: Path) -> str:
    digest = hashlib.sha256(source.read_bytes()).digest()
    return "sha256-" + base64.b64encode(digest).decode("ascii")


def trusted_index_html() -> str:
    html = (SHARED_WEB_ROOT / "index.html").read_text(encoding="utf-8")
    for marker, relative_name in SRI_ASSETS.items():
        source = SHARED_WEB_ROOT / relative_name
        replacement = f'{marker} integrity="{_asset_sri(source)}"'
        html = html.replace(marker, replacement, 1)
    return html


def build_webui_manifest() -> dict[str, object]:
    file_entries: dict[str, dict[str, object]] = {}
    bundle_hash = hashlib.sha256()
    for source, relative_path in iter_webui_files():
        relative_name = str(relative_path).replace("\\", "/")
        data = (
            trusted_index_html().encode("utf-8")
            if relative_name == "index.html"
            else source.read_bytes()
        )
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
    localization_manifest = build_localization_manifest_text().encode("utf-8")
    localization_digest = hashlib.sha256(localization_manifest).hexdigest()
    file_entries["localizations/manifest.json"] = {
        "sha256": localization_digest,
        "sha256SRI": "sha256-"
        + base64.b64encode(hashlib.sha256(localization_manifest).digest()).decode("ascii"),
        "bytes": len(localization_manifest),
    }
    bundle_hash.update(b"localizations/manifest.json\0")
    bundle_hash.update(localization_digest.encode("ascii"))
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
    for source, relative_path in iter_webui_files():
        target = destination / relative_path
        target.parent.mkdir(parents=True, exist_ok=True)
        if relative_path == Path("index.html"):
            target.write_text(trusted_index_html(), encoding="utf-8")
        else:
            shutil.copy2(source, target)
        copied.append(target)
    localization_manifest_path = destination / "localizations" / "manifest.json"
    localization_manifest_path.parent.mkdir(parents=True, exist_ok=True)
    localization_manifest_path.write_text(build_localization_manifest_text(), encoding="utf-8")
    copied.append(localization_manifest_path)
    manifest_path = destination / "asset-manifest.json"
    manifest_path.write_text(build_webui_manifest_text(), encoding="utf-8")
    copied.append(manifest_path)
    return tuple(copied)


def add_webui_to_zip(package: ZipFile, destination_root: str) -> None:
    for source, relative_path in iter_webui_files():
        if relative_path == Path("index.html"):
            package.writestr(
                str(Path(destination_root) / relative_path),
                trusted_index_html(),
            )
        else:
            package.write(source, Path(destination_root) / relative_path)
    package.writestr(
        str(Path(destination_root) / "localizations" / "manifest.json"),
        build_localization_manifest_text(),
    )
    package.writestr(
        str(Path(destination_root) / "asset-manifest.json"),
        build_webui_manifest_text(),
    )
