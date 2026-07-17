# SPDX-FileCopyrightText: 2026 Bora Yarkın
# SPDX-License-Identifier: GPL-3.0-only

from pathlib import Path
import sys
from zipfile import ZipFile

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.build_oxt import build_oxt


def test_build_oxt_packages_shared_webui_assets(tmp_path) -> None:
    output = tmp_path / "libreoffice-impress-remote.oxt"

    build_oxt(output)

    with ZipFile(output) as package:
        names = set(package.namelist())

    assert "web/index.html" in names
    assert "web/app.css" in names
    assert "web/app.js" in names
