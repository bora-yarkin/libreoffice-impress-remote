# SPDX-FileCopyrightText: 2026 Bora Yarkın
# SPDX-License-Identifier: GPL-3.0-only

from __future__ import annotations

from io import BytesIO
import json

import pytest

from impress_remote import localtunnel_client
from impress_remote.localtunnel_client import _request_tunnel_info, normalize_tunnel_host


class FakeResponse:
    status = 200

    def __init__(self, payload: dict[str, object]) -> None:
        self.payload = payload

    def __enter__(self):
        return self

    def __exit__(self, *_args) -> None:
        return None

    def read(self) -> bytes:
        return json.dumps(self.payload).encode("utf-8")


def test_normalize_tunnel_host_defaults_to_https() -> None:
    assert normalize_tunnel_host("localtunnel.me") == "https://localtunnel.me"


def test_normalize_tunnel_host_rejects_unsupported_scheme() -> None:
    with pytest.raises(ValueError):
        normalize_tunnel_host("ftp://localtunnel.me")


def test_request_tunnel_info_uses_random_endpoint(monkeypatch) -> None:
    requested_urls: list[str] = []

    def fake_urlopen(url: str, timeout: float):
        requested_urls.append(url)
        assert timeout > 0
        return FakeResponse(
            {
                "id": "demo-tunnel",
                "url": "https://demo-tunnel.localtunnel.me",
                "port": 43210,
                "max_conn_count": 2,
            }
        )

    monkeypatch.setattr(localtunnel_client, "urlopen", fake_urlopen)

    info = _request_tunnel_info("https://localtunnel.me")

    assert requested_urls == ["https://localtunnel.me/?new"]
    assert info.name == "demo-tunnel"
    assert info.url == "https://demo-tunnel.localtunnel.me"
    assert info.remote_host == "localtunnel.me"
    assert info.remote_port == 43210
    assert info.max_connections == 2


def test_request_tunnel_info_uses_requested_subdomain(monkeypatch) -> None:
    requested_urls: list[str] = []

    def fake_urlopen(url: str, timeout: float):
        requested_urls.append(url)
        assert timeout > 0
        return FakeResponse(
            {
                "id": "slides-demo",
                "url": "https://slides-demo.localtunnel.me",
                "port": 43210,
            }
        )

    monkeypatch.setattr(localtunnel_client, "urlopen", fake_urlopen)

    info = _request_tunnel_info("https://localtunnel.me", "Slides-Demo")

    assert requested_urls == ["https://localtunnel.me/slides-demo"]
    assert info.name == "slides-demo"


def test_request_tunnel_info_rejects_invalid_payload(monkeypatch) -> None:
    class InvalidResponse:
        status = 200

        def __enter__(self):
            return self

        def __exit__(self, *_args) -> None:
            return None

        def read(self) -> bytes:
            return BytesIO(b"[]").read()

    monkeypatch.setattr(localtunnel_client, "urlopen", lambda *_args, **_kwargs: InvalidResponse())

    with pytest.raises(ConnectionError):
        _request_tunnel_info("https://localtunnel.me")
