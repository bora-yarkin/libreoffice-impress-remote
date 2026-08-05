# SPDX-FileCopyrightText: 2026 Bora Yarkın
# SPDX-License-Identifier: GPL-3.0-only

from __future__ import annotations

from pathlib import Path
from urllib.parse import unquote, urlparse
from urllib.request import url2pathname


def module_file_path(module_file: str) -> Path:
    if module_file.startswith("file://"):
        parsed = urlparse(module_file)
        return Path(url2pathname(unquote(parsed.path))).resolve()
    return Path(module_file).resolve()


def _has_packaged_content(path: Path) -> bool:
    if path.is_file():
        return True
    if not path.is_dir():
        return False
    return (path / "index.html").exists()


def resolve_packaged_or_shared_dir(
    module_file: str,
    packaged_parts: tuple[str, ...],
    shared_parts: tuple[str, ...],
) -> Path:
    module_path = module_file_path(module_file)
    packaged_root = module_path.parents[2].joinpath(*packaged_parts)
    if _has_packaged_content(packaged_root):
        return packaged_root
    shared_root = module_path.parents[3].joinpath(*shared_parts)
    if _has_packaged_content(shared_root):
        return shared_root
    return packaged_root
