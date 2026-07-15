# SPDX-FileCopyrightText: 2026 Bora Yarkın
# SPDX-License-Identifier: GPL-3.0-only

from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile

ROOT = Path(__file__).resolve().parents[1]
EXTENSION = ROOT / "extension"
DIST = ROOT / "dist"
OUT = DIST / "libreoffice-impress-remote.oxt"
INCLUDE = ["META-INF", "description.xml", "Addons.xcu", "ProtocolHandler.xcu", "python", "web", "icons"]


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


def main() -> None:
    DIST.mkdir(exist_ok=True)
    if OUT.exists():
        OUT.unlink()
    with ZipFile(OUT, "w", ZIP_DEFLATED) as package:
        for item in INCLUDE:
            add_path(package, EXTENSION / item, EXTENSION)
    print(OUT)


if __name__ == "__main__":
    main()
