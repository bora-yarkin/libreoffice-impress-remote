# SPDX-FileCopyrightText: 2026 Bora Yarkın
# SPDX-License-Identifier: GPL-3.0-only

"""Build the companion as a PyInstaller one-folder bundle for this OS/CPU."""

import os
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
BUILD_ROOT = ROOT / "build" / "companion"


def main() -> int:
    command = [
        sys.executable,
        "-m",
        "PyInstaller",
        "--noconfirm",
        "--clean",
        "--onedir",
        "--name",
        "impress-remote-companion",
        "--collect-data",
        "impress_remote_companion",
        "--distpath",
        str(ROOT / "dist" / "companion"),
        "--workpath",
        str(BUILD_ROOT / "work"),
        "--specpath",
        str(BUILD_ROOT / "spec"),
        "--paths",
        str(ROOT / "companion" / "src"),
        str(ROOT / "companion" / "frozen_entry.py"),
    ]
    environment = os.environ.copy()
    environment["PYINSTALLER_CONFIG_DIR"] = str(BUILD_ROOT / "config")
    return subprocess.run(command, cwd=ROOT, env=environment, check=False).returncode


if __name__ == "__main__":
    raise SystemExit(main())
