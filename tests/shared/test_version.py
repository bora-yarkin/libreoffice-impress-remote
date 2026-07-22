# SPDX-FileCopyrightText: 2026 Bora Yarkin
# SPDX-License-Identifier: GPL-3.0-only

from pathlib import Path
import tomllib

from impress_remote import __version__ as extension_version
from impress_remote_relay import __version__ as relay_version
from tools.project_version import read_project_version

ROOT = Path(__file__).resolve().parents[2]


def test_python_runtime_versions_come_from_root_version_file() -> None:
    version = read_project_version()

    assert extension_version == version
    assert relay_version == version


def test_pyproject_versions_are_dynamic() -> None:
    for path in (ROOT / "pyproject.toml", ROOT / "server" / "pyproject.toml"):
        with path.open("rb") as handle:
            data = tomllib.load(handle)
        assert data["project"]["dynamic"] == ["version"]
        assert "version" not in data["project"]
