# SPDX-FileCopyrightText: 2026 Bora Yarkın
# SPDX-License-Identifier: GPL-3.0-only

from __future__ import annotations

from dataclasses import asdict, dataclass
import json
from pathlib import Path
import socket

from relay.localization import translate

DEFAULT_HOST_V4 = "0.0.0.0"
DEFAULT_HOST_V6 = "::"
DEFAULT_SESSION_TTL = 3600


@dataclass(frozen=True)
class RelayRuntimeConfig:
    host_v4: str = DEFAULT_HOST_V4
    host_v6: str = DEFAULT_HOST_V6
    port: int = 8080
    session_ttl: int = DEFAULT_SESSION_TTL

    @classmethod
    def from_dict(cls, payload: dict[str, object]) -> RelayRuntimeConfig:
        host_v4 = payload.get("host_v4", DEFAULT_HOST_V4)
        host_v6 = payload.get("host_v6", DEFAULT_HOST_V6)
        port = payload.get("port", 8080)
        session_ttl = payload.get("session_ttl", DEFAULT_SESSION_TTL)
        if not isinstance(host_v4, str):
            raise ValueError(translate("relay.error.runtimeHostV4"))
        if not isinstance(host_v6, str):
            raise ValueError(translate("relay.error.runtimeHostV6"))
        if isinstance(port, bool) or not isinstance(port, int):
            raise ValueError(translate("relay.error.runtimePort"))
        if isinstance(session_ttl, bool) or not isinstance(session_ttl, int):
            raise ValueError(translate("relay.error.runtimeSessionTtl"))
        return cls(
            host_v4=host_v4,
            host_v6=host_v6,
            port=port,
            session_ttl=session_ttl,
        )

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


def choose_random_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def load_runtime_config(path: Path) -> RelayRuntimeConfig:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(translate("relay.error.runtimeConfigObject"))
    return RelayRuntimeConfig.from_dict(payload)


def save_runtime_config(path: Path, config: RelayRuntimeConfig) -> RelayRuntimeConfig:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(config.to_dict(), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return config


def ensure_runtime_config(
    path: Path,
    *,
    host_v4: str | None = None,
    host_v6: str | None = None,
    port: int | None = None,
    session_ttl: int | None = None,
) -> RelayRuntimeConfig:
    if path.exists():
        return load_runtime_config(path)
    return save_runtime_config(
        path,
        RelayRuntimeConfig(
            host_v4=host_v4 if host_v4 is not None else DEFAULT_HOST_V4,
            host_v6=host_v6 if host_v6 is not None else DEFAULT_HOST_V6,
            port=port if port is not None else choose_random_port(),
            session_ttl=session_ttl if session_ttl is not None else DEFAULT_SESSION_TTL,
        ),
    )
