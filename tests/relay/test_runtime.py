# SPDX-FileCopyrightText: 2026 Bora Yarkın
# SPDX-License-Identifier: GPL-3.0-only

from pathlib import Path

import impress_remote_relay.runtime as runtime
from impress_remote_relay.runtime import ensure_runtime_config, load_runtime_config


def test_ensure_runtime_config_creates_random_port_when_missing(
    tmp_path: Path,
    monkeypatch,
) -> None:
    config_path = tmp_path / "service.json"
    monkeypatch.setattr(runtime, "choose_random_port", lambda: 18443)

    config = ensure_runtime_config(config_path)

    assert config_path.exists()
    assert config.port == 18443
    assert load_runtime_config(config_path).port == config.port


def test_ensure_runtime_config_honors_explicit_defaults_on_first_write(tmp_path: Path) -> None:
    config_path = tmp_path / "service.json"

    config = ensure_runtime_config(
        config_path,
        host_v4="127.0.0.1",
        host_v6="",
        port=19191,
        session_ttl=120,
    )

    assert config.host_v4 == "127.0.0.1"
    assert config.host_v6 == ""
    assert config.port == 19191
    assert config.session_ttl == 120
