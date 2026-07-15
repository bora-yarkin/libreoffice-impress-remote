# SPDX-FileCopyrightText: 2026 Bora Yarkın
# SPDX-License-Identifier: GPL-3.0-only

from __future__ import annotations

from dataclasses import dataclass
import json
import os
from pathlib import Path
import sys
from typing import Any
from urllib.parse import urlencode, urlparse, urlunparse

APP_NAME = "libreoffice-impress-remote"
DEFAULT_LOCAL_HOST = "0.0.0.0"
DEFAULT_LOCAL_PORT = 17865
DEFAULT_PREFERRED_ROUTE = "auto"
ROUTE_LABELS = {
    "auto": "Auto (Local -> IPv6 -> Relay)",
    "local": "Local network",
    "ipv6": "Direct IPv6",
    "relay": "Relay server",
}


def default_config_dir() -> Path:
    home = Path.home()
    if sys.platform == "darwin":
        return home / "Library" / "Application Support" / APP_NAME
    if os.name == "nt":
        base = Path(os.environ.get("APPDATA", home / "AppData" / "Roaming"))
        return base / APP_NAME
    base = Path(os.environ.get("XDG_CONFIG_HOME", home / ".config"))
    return base / APP_NAME


def config_path(base_dir: Path | None = None) -> Path:
    return (base_dir or default_config_dir()) / "config.json"


def _coerce_bool(value: Any, default: bool) -> bool:
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.strip().lower() in {"1", "true", "yes", "on"}
    return bool(value)


def _coerce_local_port(value: Any, default: int = DEFAULT_LOCAL_PORT) -> int:
    try:
        port = int(value)
    except (TypeError, ValueError):
        return default
    return port if 1 <= port <= 65535 else default


def normalize_preferred_route(value: Any, default: str = DEFAULT_PREFERRED_ROUTE) -> str:
    if isinstance(value, str):
        normalized = value.strip().lower()
        aliases = {
            "direct": "ipv6",
            "direct_ipv6": "ipv6",
            "direct-ipv6": "ipv6",
            "ipv6_direct": "ipv6",
            "ipv6-direct": "ipv6",
        }
        normalized = aliases.get(normalized, normalized)
        if normalized in ROUTE_LABELS:
            return normalized
    return default


def route_label(route: str) -> str:
    return ROUTE_LABELS.get(route, ROUTE_LABELS[DEFAULT_PREFERRED_ROUTE])


def _looks_local_host(host: str) -> bool:
    lowered = host.lower()
    return lowered.startswith(("localhost", "127.", "[::1]", "::1", "192.168.", "10.", "172."))


def normalize_relay_url(value: str) -> str:
    text = value.strip()
    if not text:
        return ""

    parsed = urlparse(text)
    if not parsed.scheme:
        scheme = "http" if _looks_local_host(text) else "https"
        parsed = urlparse(f"{scheme}://{text}")

    if parsed.scheme not in {"http", "https", "ws", "wss"}:
        raise ValueError(f"Unsupported relay URL scheme: {parsed.scheme}")
    if not parsed.netloc:
        raise ValueError("Relay URL must include a host")

    normalized_path = parsed.path.rstrip("/")
    return urlunparse((parsed.scheme, parsed.netloc, normalized_path, "", "", ""))


def relay_websocket_url(relay_url: str, session_id: str) -> str:
    parsed = urlparse(normalize_relay_url(relay_url))
    scheme = {"http": "ws", "https": "wss"}.get(parsed.scheme, parsed.scheme)
    path = parsed.path.rstrip("/")
    if not path:
        path = "/ws"
    elif not path.endswith("/ws"):
        path = f"{path}/ws"
    query = urlencode({"role": "plugin", "session": session_id})
    return urlunparse((scheme, parsed.netloc, path, "", query, ""))


def relay_join_url(relay_url: str, session_id: str) -> str:
    parsed = urlparse(normalize_relay_url(relay_url))
    scheme = {"ws": "http", "wss": "https"}.get(parsed.scheme, parsed.scheme)
    path = parsed.path.rstrip("/")
    if path.endswith("/ws"):
        path = path[:-3]
    if not path:
        path = "/"
    fragment = urlencode({"mode": "relay", "s": session_id})
    return urlunparse((scheme, parsed.netloc, path, "", "", fragment))


@dataclass(frozen=True)
class RemoteConfig:
    local_host: str = DEFAULT_LOCAL_HOST
    local_port: int = DEFAULT_LOCAL_PORT
    relay_url: str = ""
    enable_relay: bool = False
    enable_ipv6_direct: bool = True
    preferred_route: str = DEFAULT_PREFERRED_ROUTE

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> RemoteConfig:
        relay_url = payload.get("relay_url", payload.get("relayUrl", ""))
        normalized_relay_url = normalize_relay_url(str(relay_url)) if relay_url else ""
        return cls(
            local_host=str(payload.get("local_host", payload.get("localHost", DEFAULT_LOCAL_HOST))),
            local_port=_coerce_local_port(payload.get("local_port", payload.get("localPort"))),
            relay_url=normalized_relay_url,
            enable_relay=_coerce_bool(
                payload.get("enable_relay", payload.get("enableRelay")),
                False,
            ),
            enable_ipv6_direct=_coerce_bool(
                payload.get("enable_ipv6_direct", payload.get("enableIpv6Direct")),
                True,
            ),
            preferred_route=normalize_preferred_route(
                payload.get("preferred_route", payload.get("preferredRoute")),
            ),
        )

    @classmethod
    def load(cls, base_dir: Path | None = None) -> RemoteConfig:
        path = config_path(base_dir)
        if not path.exists():
            return cls()
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError, ValueError):
            return cls()
        return cls.from_dict(payload)

    def to_dict(self) -> dict[str, object]:
        return {
            "localHost": self.local_host,
            "localPort": self.local_port,
            "relayUrl": self.relay_url,
            "enableRelay": self.enable_relay,
            "enableIpv6Direct": self.enable_ipv6_direct,
            "preferredRoute": self.preferred_route,
        }

    def save(self, base_dir: Path | None = None) -> Path:
        path = config_path(base_dir)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(self.to_dict(), indent=2, sort_keys=True), encoding="utf-8")
        return path

    def merge(self, payload: dict[str, Any]) -> RemoteConfig:
        current = self.to_dict()
        current.update(payload)
        return RemoteConfig.from_dict(current)
