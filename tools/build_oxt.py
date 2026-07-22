# SPDX-FileCopyrightText: 2026 Bora Yarkın
# SPDX-License-Identifier: GPL-3.0-only

from pathlib import Path
import argparse
import json
import re
import shutil
import sys
from tempfile import TemporaryDirectory
from zipfile import ZIP_DEFLATED, ZipFile

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.build_release_bundle import build_bundle  # noqa: E402
from tools.build_cloudflare_bundle import build_cloudflare_bundle  # noqa: E402
from tools.project_version import read_project_version  # noqa: E402
from tools.shared_webui import add_webui_to_zip  # noqa: E402

EXTENSION = ROOT / "extension"
DIST = ROOT / "dist"
OUT = DIST / f"libreoffice-impress-remote-{read_project_version()}.oxt"
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
DOC_SOURCE_FILES = (
    "README.md",
    "CHANGELOG.md",
    "TODO.md",
    "LICENSE",
    "REUSE.toml",
)
EXCLUDED_NAMES = {".DS_Store", "__MACOSX"}


def should_include(path: Path) -> bool:
    return (
        "__pycache__" not in path.parts
        and not any(part in EXCLUDED_NAMES for part in path.parts)
        and path.suffix not in {".pyc", ".pyo"}
    )


def add_path(package: ZipFile, path: Path, base: Path) -> None:
    if path.is_dir():
        for child in sorted(path.rglob("*")):
            if child.is_file() and should_include(child):
                package.write(child, child.relative_to(base))
        return
    if path.is_file() and should_include(path):
        package.write(path, path.relative_to(base))


def project_version() -> str:
    return read_project_version()


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


def iter_documentation_files() -> tuple[Path, ...]:
    files: set[Path] = set()
    for relative_name in DOC_SOURCE_FILES:
        path = ROOT / relative_name
        if path.is_file():
            files.add(path)
    for root in (ROOT / "docs", ROOT / ".github", ROOT / "deploy"):
        if not root.exists():
            continue
        for path in root.rglob("*"):
            if path.is_file() and should_include(path):
                files.add(path)
    return tuple(sorted(files))


def build_documentation_bundle(dist_dir: Path = DIST) -> Path:
    version = project_version()
    dist_dir.mkdir(parents=True, exist_ok=True)
    archive_path = dist_dir / f"impress-remote-docs-{version}.zip"
    bundle_root = Path(f"impress-remote-docs-{version}")
    if archive_path.exists():
        archive_path.unlink()
    with ZipFile(archive_path, "w", ZIP_DEFLATED) as archive:
        for path in iter_documentation_files():
            archive.write(path, bundle_root / path.relative_to(ROOT))
    return archive_path


def build_oxt(
    output_path: Path = OUT,
    *,
    clean_dist: bool = True,
) -> Path:
    output_path.parent.mkdir(exist_ok=True)
    if clean_dist:
        clean_oxt_dist(output_path)
    if output_path.exists():
        output_path.unlink()
    with TemporaryDirectory(prefix="impress-remote-oxt-") as temp_dir_name:
        temp_dir = Path(temp_dir_name)
        _bundle_dir, relay_archive = build_bundle(temp_dir)
        _cloudflare_dir, cloudflare_archive = build_cloudflare_bundle(temp_dir)
        docs_archive = build_documentation_bundle(temp_dir)
        support_archives = (relay_archive, cloudflare_archive, docs_archive)
        with ZipFile(output_path, "w", ZIP_DEFLATED) as package:
            for item in INCLUDE:
                if item == "description.xml":
                    add_description_xml(package)
                    continue
                add_path(package, EXTENSION / item, EXTENSION)
            package.writestr("python/impress_remote/VERSION", project_version() + "\n")
            package.writestr(
                "python/impress_remote/BUILD_FEATURES.json",
                json.dumps(
                    {"localtunnel": True, "relay": True},
                    indent=2,
                    sort_keys=True,
                )
                + "\n",
            )
            add_webui_to_zip(package, "web")
            for archive_path in support_archives:
                package.write(archive_path, Path("resources") / archive_path.name)
    return output_path


def main() -> None:
    parser = argparse.ArgumentParser(description="Build LibreOffice Impress Remote OXT packages.")
    parser.parse_args()
    print(build_oxt())


if __name__ == "__main__":
    main()
