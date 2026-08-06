# SPDX-FileCopyrightText: 2026 Bora Yarkın
# SPDX-License-Identifier: GPL-3.0-only

"""Read the extension version from a packaged or source-tree VERSION file."""

from pathlib import Path


def _read_version() -> str:
    """Read a packaged version first, then the source-tree version file."""
    for candidate in (
        Path(__file__).with_name("VERSION"),
        Path(__file__).resolve().parents[2] / "VERSION",
    ):
        try:
            version = candidate.read_text(encoding="utf-8").strip()
        except OSError:
            continue
        if version:
            return version
    return "0+unknown"


__version__ = _read_version()
