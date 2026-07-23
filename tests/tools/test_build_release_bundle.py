# SPDX-FileCopyrightText: 2026 Bora Yarkın
# SPDX-License-Identifier: GPL-3.0-only

from pathlib import Path
import sys
from zipfile import ZipFile

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.build_release_bundle import build_bundle  # noqa: E402


def test_build_release_bundle_contains_only_relay_runtime_assets(tmp_path) -> None:
    dist_dir = ROOT / "dist"
    if dist_dir.exists():
        before = {path.relative_to(dist_dir) for path in dist_dir.rglob("*")}
    else:
        before = set()

    try:
        bundle_dir, archive_path = build_bundle()
        bundle_name = bundle_dir.name
        with ZipFile(archive_path) as archive:
            names = set(archive.namelist())
        assert f"{bundle_name}/LICENSE" in names
        assert f"{bundle_name}/run-relay.py" in names
        assert f"{bundle_name}/install-linux-service.sh" in names
        assert f"{bundle_name}/install-windows-service.ps1" in names
        assert f"{bundle_name}/relay/web/index.html" in names
        assert f"{bundle_name}/relay/web/app.js" in names
        assert f"{bundle_name}/relay/web/manifest.webmanifest" not in names
        assert f"{bundle_name}/relay/web/sw.js" not in names
        assert f"{bundle_name}/relay/web/icons/remote.svg" not in names
        assert f"{bundle_name}/relay/web/localizations/en.json" in names
        assert f"{bundle_name}/relay/web/localizations/tr.json" in names
        assert all(not name.endswith(".oxt") for name in names)
        assert all("/shared/" not in name for name in names)
        assert all("__pycache__/" not in name for name in names)
        assert all(not name.endswith((".pyc", ".pyo")) for name in names)
    finally:
        if dist_dir.exists():
            for path in sorted(dist_dir.rglob("*"), reverse=True):
                relative = path.relative_to(dist_dir)
                if relative not in before:
                    if path.is_file():
                        path.unlink()
                    elif path.is_dir():
                        path.rmdir()
