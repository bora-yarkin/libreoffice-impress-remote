# SPDX-FileCopyrightText: 2026 Bora Yarkın
# SPDX-License-Identifier: GPL-3.0-only

from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile

from tools.shared_webui import add_webui_to_zip

ROOT = Path(__file__).resolve().parents[1]
EXTENSION = ROOT / "extension"
DIST = ROOT / "dist"
OUT = DIST / "libreoffice-impress-remote.oxt"
INCLUDE = [
    "META-INF",
    "description.xml",
    "Addons.xcu",
    "ProtocolHandler.xcu",
    "Settings.xcs",
    "Settings.xcu",
    "python",
    "icons",
]


def should_include(path: Path) -> bool:
    return "__pycache__" not in path.parts and path.suffix not in {".pyc", ".pyo"}


def add_path(package: ZipFile, path: Path, base: Path) -> None:
    if path.is_dir():
        for child in sorted(path.rglob("*")):
            if child.is_file() and should_include(child):
                package.write(child, child.relative_to(base))
        return
    if path.is_file() and should_include(path):
        package.write(path, path.relative_to(base))


def build_oxt(output_path: Path = OUT) -> Path:
    output_path.parent.mkdir(exist_ok=True)
    if output_path.exists():
        output_path.unlink()
    with ZipFile(output_path, "w", ZIP_DEFLATED) as package:
        for item in INCLUDE:
            add_path(package, EXTENSION / item, EXTENSION)
        add_webui_to_zip(package, "web")
    return output_path


def main() -> None:
    print(build_oxt())


if __name__ == "__main__":
    main()
