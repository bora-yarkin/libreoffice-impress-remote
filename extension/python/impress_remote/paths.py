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
