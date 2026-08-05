# SPDX-FileCopyrightText: 2026 Bora Yarkın
# SPDX-License-Identifier: GPL-3.0-only

from pathlib import Path


def _read_version() -> str:
    for candidate in (
        Path(__file__).with_name("VERSION"),
        Path(__file__).resolve().parents[3] / "VERSION",
    ):
        try:
            version = candidate.read_text(encoding="utf-8").strip()
        except OSError:
            continue
        if version:
            return version
    return "0+unknown"


__version__ = _read_version()
