# SPDX-FileCopyrightText: 2026 Bora Yarkın
# SPDX-License-Identifier: GPL-3.0-only

from __future__ import annotations

import argparse
import base64
from collections.abc import Sequence
import hashlib
import json
from pathlib import Path
import re
import shutil
import sys
from tempfile import TemporaryDirectory
from zipfile import ZIP_DEFLATED, ZipFile

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

VERSION_FILE = ROOT / "VERSION"
EXTENSION = ROOT / "extension"
DIST = ROOT / "dist"
RELAY_ROOT = ROOT / "relay"
RELAY_SCRIPTS = RELAY_ROOT / "scripts"
SHARED_WEB_ROOT = ROOT / "shared" / "webui"
LOCALIZATION_ROOT = ROOT / "shared" / "localizations"
DEFAULT_LOCALE = "en"
RUNTIME_DIR_NAME = "relay-runtime"
OUT = DIST / f"libreoffice-impress-remote-{VERSION_FILE.read_text(encoding='utf-8').strip()}.oxt"
INCLUDE = [
    "META-INF",
    "description.xml",
    "Addons.xcu",
    "ProtocolHandler.xcu",
    "Settings.xcs",
    "Settings.xcu",
    "python",
    "icons",
    "descriptions",
]
USER_GUIDE = ROOT / "docs" / "user-guide.md"
EXCLUDED_NAMES = {".DS_Store", "__MACOSX"}
SRI_ASSETS = {
    'href="/app.css"': "app.css",
    'src="/app.js"': "app.js",
}


def read_project_version() -> str:
    version = VERSION_FILE.read_text(encoding="utf-8").strip()
    if not version:
        raise RuntimeError("VERSION is empty")
    return version


def project_version() -> str:
    return read_project_version()


def should_include(path: Path) -> bool:
    return (
        "__pycache__" not in path.parts
        and not any(part in EXCLUDED_NAMES for part in path.parts)
        and path.suffix not in {".pyc", ".pyo"}
    )


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
    return {
        "version": 1,
        "defaultLocale": DEFAULT_LOCALE,
        "locales": [path.stem for path in iter_localization_files()],
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
        html = html.replace(marker, f'{marker} integrity="{_asset_sri(source)}"', 1)
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
            package.writestr(str(Path(destination_root) / relative_path), trusted_index_html())
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


def add_path(package: ZipFile, path: Path, base: Path) -> None:
    if path.is_dir():
        for child in sorted(path.rglob("*")):
            if child.is_file() and should_include(child):
                package.write(child, child.relative_to(base))
        return
    if path.is_file() and should_include(path):
        package.write(path, path.relative_to(base))


def clean_oxt_dist(output_path: Path) -> None:
    if not DIST.exists() or output_path.parent.resolve() != DIST.resolve():
        return
    for path in DIST.iterdir():
        if path.resolve() == output_path.resolve():
            continue
        if path.is_dir():
            shutil.rmtree(path)
            continue
        path.unlink()


def add_description_xml(package: ZipFile) -> None:
    versioned_description = re.sub(
        r'<version value="[^"]+"/>',
        f'<version value="{project_version()}"/>',
        (EXTENSION / "description.xml").read_text(encoding="utf-8"),
        count=1,
    )
    package.writestr("description.xml", versioned_description)


def copy_python_package(source: Path, destination: Path) -> None:
    for path in sorted(source.glob("*.py")):
        target = destination / path.relative_to(source)
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(path, target)


def copy_deploy_files(source: Path, destination: Path, *, exclude: set[str] | None = None) -> None:
    exclude = exclude or set()
    for path in sorted(source.rglob("*")):
        if (
            path.is_dir()
            or path.name == ".DS_Store"
            or path.name in exclude
            or "__pycache__" in path.parts
            or path.suffix in {".pyc", ".pyo"}
        ):
            continue
        target = destination / path.relative_to(source)
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(path, target)


def build_bundle(dist_dir: Path = DIST) -> tuple[Path, Path]:
    version = project_version()
    dist_dir.mkdir(parents=True, exist_ok=True)
    bundle_dir = dist_dir / f"impress-remote-relay-python-{version}"
    archive_path = dist_dir / f"impress-remote-relay-python-{version}.zip"

    if bundle_dir.exists():
        shutil.rmtree(bundle_dir)
    if archive_path.exists():
        archive_path.unlink()

    bundle_dir.mkdir(parents=True, exist_ok=True)
    shutil.copy2(RELAY_SCRIPTS / "configure.sh", bundle_dir / "configure.sh")
    shutil.copy2(RELAY_SCRIPTS / "configure.ps1", bundle_dir / "configure.ps1")

    runtime_dir = bundle_dir / RUNTIME_DIR_NAME
    runtime_dir.mkdir(parents=True, exist_ok=True)
    shutil.copy2(ROOT / "LICENSE", runtime_dir / "LICENSE")
    copy_deploy_files(RELAY_SCRIPTS, runtime_dir, exclude={"configure.sh", "configure.ps1"})
    shutil.copy2(RELAY_ROOT / "README.md", runtime_dir / "README.md")
    relay_src = runtime_dir / "relay"
    relay_src.mkdir(parents=True, exist_ok=True)
    copy_python_package(RELAY_ROOT, relay_src)
    (relay_src / "VERSION").write_text(version + "\n", encoding="utf-8")
    copy_webui(relay_src / "web")

    with ZipFile(archive_path, "w", ZIP_DEFLATED) as archive:
        for path in sorted(bundle_dir.rglob("*")):
            if path.is_file():
                archive.write(path, path.relative_to(dist_dir))

    return bundle_dir, archive_path


def build_oxt(output_path: Path = OUT, *, clean_dist: bool = True) -> Path:
    output_path.parent.mkdir(exist_ok=True)
    if clean_dist:
        clean_oxt_dist(output_path)
    if output_path.exists():
        output_path.unlink()

    with TemporaryDirectory(prefix="impress-remote-oxt-") as temp_dir_name:
        temp_dir = Path(temp_dir_name)
        _bundle_dir, relay_archive = build_bundle(temp_dir)
        with ZipFile(output_path, "w", ZIP_DEFLATED) as package:
            for item in INCLUDE:
                if item == "description.xml":
                    add_description_xml(package)
                    continue
                add_path(package, EXTENSION / item, EXTENSION)
            package.write(USER_GUIDE, "resources/user-guide.md")
            package.writestr("python/impress_remote/VERSION", project_version() + "\n")
            package.writestr(
                "python/impress_remote/BUILD_FEATURES.json",
                json.dumps({"localtunnel": True, "relay": True}, indent=2, sort_keys=True) + "\n",
            )
            add_webui_to_zip(package, "web")
            package.write(relay_archive, Path("resources") / relay_archive.name)
    return output_path


def main(argv: Sequence[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Build release artifacts.")
    parser.add_argument(
        "artifact",
        nargs="?",
        default="oxt",
        choices=("oxt", "relay"),
        help="Artifact to build. Defaults to the LibreOffice OXT.",
    )
    args = parser.parse_args(argv)

    if args.artifact == "relay":
        bundle_dir, archive_path = build_bundle()
        print(bundle_dir)
        print(archive_path)
        return
    print(build_oxt())


if __name__ == "__main__":
    main()
