# SPDX-FileCopyrightText: 2026 Bora Yarkin
# SPDX-License-Identifier: GPL-3.0-only

from pathlib import Path
import runpy

ROOT = Path(__file__).resolve().parents[2]


def test_tool_scripts_can_be_loaded_like_direct_entrypoints() -> None:
    for script in (
        "tools/build_oxt.py",
        "tools/build_release_bundle.py",
        "tools/build_cloudflare_bundle.py",
        "tools/build_cloudflare_dashboard_worker.py",
        "tools/import_localizations.py",
        "tools/validate_relay_compat.py",
    ):
        runpy.run_path(str(ROOT / script), run_name="not_main")
