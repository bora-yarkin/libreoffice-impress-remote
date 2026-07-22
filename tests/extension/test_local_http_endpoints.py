# SPDX-FileCopyrightText: 2026 Bora Yarkın
# SPDX-License-Identifier: GPL-3.0-only

from __future__ import annotations

import json
from types import SimpleNamespace
from typing import Any, cast
from urllib.error import HTTPError
from urllib.request import Request, urlopen

import pytest

from impress_remote.config import RemoteConfig
from impress_remote.crypto import base64url_decode
from impress_remote.local_server import RemoteServer, _is_local_compatibility_client
from impress_remote.protocol import SecureRelayCodec, decode_hello_message, encode_hello_message


class FakeController:
    def __init__(self) -> None:
        self.commands: list[tuple[str, int | None]] = []
        self.state_value = SimpleNamespace(
            running=True,
            active=True,
            paused=False,
            document_kind="impress",
            status_message="Running",
            current_slide=1,
            slide_count=5,
            current_title="Intro",
            notes="Speaker notes",
            next_slide=2,
            next_title="Next",
            next_preview="Next",
            can_go_previous=True,
            can_go_next=True,
            remaining_slides=3,
            at_end_of_deck=False,
            elapsed_seconds=12,
            current_render_token="current123",
            next_render_token="next456",
        )

    def state(self):
        return self.state_value

    def command(self, name: str, index: int | None = None) -> None:
        self.commands.append((name, index))

    def current_slide_png_bytes(self) -> bytes:
        return b"current-png"

    def next_slide_png_bytes(self) -> bytes:
        return b"next-png"


@pytest.fixture
def remote_server():
    server = RemoteServer(
        ctx=SimpleNamespace(),
        config=RemoteConfig(
            local_host="127.0.0.1",
            local_port=0,
            enable_local_listener=True,
            enable_ipv6_direct=False,
        ),
    )
    cast(Any, server).controller = FakeController()
    server.start()
    try:
        yield server
    finally:
        server.stop()


def _fake_controller(server: RemoteServer) -> FakeController:
    return cast(FakeController, server.controller)


def _url(server: RemoteServer, path: str) -> str:
    return f"http://127.0.0.1:{server.bound_port}{path}"


def _request(
    server: RemoteServer,
    path: str,
    *,
    method: str = "GET",
    data: bytes | None = None,
    headers: dict[str, str] | None = None,
):
    request = Request(
        _url(server, path),
        data=data,
        headers=headers or {},
        method=method,
    )
    return urlopen(request, timeout=3)


def _json_request(
    server: RemoteServer,
    path: str,
    *,
    method: str = "GET",
    payload: dict[str, object] | None = None,
    headers: dict[str, str] | None = None,
) -> dict[str, object]:
    data = None if payload is None else json.dumps(payload).encode("utf-8")
    request_headers = {"Content-Type": "application/json"} if data is not None else {}
    request_headers.update(headers or {})
    with _request(server, path, method=method, data=data, headers=request_headers) as response:
        return json.loads(response.read().decode("utf-8"))


def _fallback_headers(server: RemoteServer) -> dict[str, str]:
    return {
        "X-Impress-Remote-Session": server.session_id,
        "X-Impress-Remote-Secret": server.pairing_secret,
    }


def _apply_hello(phone: SecureRelayCodec, payload: dict[str, object]) -> dict[str, object]:
    hello = decode_hello_message(json.dumps(payload, separators=(",", ":")))
    assert hello is not None
    response_hello = phone.apply_hello(hello)
    assert response_hello is not None
    return json.loads(encode_hello_message(response_hello))


def _decrypt_frame(
    phone: SecureRelayCodec,
    payload: dict[str, object],
) -> tuple[str, dict[str, object]]:
    frame = phone.decode_frame(json.dumps(payload, separators=(",", ":")))
    assert frame is not None
    return frame.kind, frame.payload


def _complete_direct_handshake(remote_server: RemoteServer) -> SecureRelayCodec:
    hello_payload = _json_request(
        remote_server,
        f"/api/direct/handshake?s={remote_server.session_id}",
    )
    phone = SecureRelayCodec(
        role="phone",
        session_id=remote_server.session_id,
        pairing_secret=remote_server.pairing_secret,
    )
    phone_hello = _apply_hello(phone, hello_payload)
    _json_request(
        remote_server,
        f"/api/direct/handshake?s={remote_server.session_id}",
        method="POST",
        payload=phone_hello,
    )
    return phone


def test_static_phone_ui_uses_browser_security_headers(remote_server: RemoteServer) -> None:
    with _request(remote_server, "/") as response:
        body = response.read().decode("utf-8")

    assert '<script src="/app.js"></script>' in body
    assert response.headers["X-Content-Type-Options"] == "nosniff"
    assert response.headers["Referrer-Policy"] == "no-referrer"
    assert response.headers["X-Frame-Options"] == "DENY"
    assert "frame-ancestors 'none'" in response.headers["Content-Security-Policy"]


def test_static_asset_manifest_is_served_for_local_frontend_verification(
    remote_server: RemoteServer,
) -> None:
    payload = _json_request(remote_server, "/asset-manifest.json")

    assert payload["version"] == 1
    files = payload["files"]
    assert isinstance(files, dict)
    assert "app.js" in files
    assert "localizations/manifest.json" in files


def test_direct_state_requires_session_token(remote_server: RemoteServer) -> None:
    with pytest.raises(HTTPError) as exc_info:
        _json_request(remote_server, "/api/direct/state")

    assert exc_info.value.code == 403


def test_direct_handshake_accepts_matching_session_token(remote_server: RemoteServer) -> None:
    payload = _json_request(remote_server, f"/api/direct/handshake?s={remote_server.session_id}")

    assert payload["type"] == "hello"
    assert payload["s"] == remote_server.session_id


def test_direct_encrypted_http_state_asset_and_command_round_trip(
    remote_server: RemoteServer,
) -> None:
    phone = _complete_direct_handshake(remote_server)

    state_payload = _json_request(
        remote_server,
        f"/api/direct/state?s={remote_server.session_id}",
    )
    state_hello = state_payload.get("hello")
    if isinstance(state_hello, dict):
        phone_hello = _apply_hello(phone, state_hello)
        _json_request(
            remote_server,
            f"/api/direct/handshake?s={remote_server.session_id}",
            method="POST",
            payload=phone_hello,
        )
    state_frame = cast(dict[str, object], state_payload["frame"])
    state_kind, state = _decrypt_frame(phone, state_frame)

    assert state_kind == "state"
    assert state["notes"] == "Speaker notes"
    assert state["currentSlideImageUrl"] == (
        f"/api/direct/slide/current?s={remote_server.session_id}&rev=current123"
    )
    assert state["nextSlideImageUrl"] == (
        f"/api/direct/slide/next?s={remote_server.session_id}&rev=next456"
    )

    current_slide_path = cast(str, state["currentSlideImageUrl"])
    asset_payload = _json_request(remote_server, current_slide_path)
    asset_hello = asset_payload.get("hello")
    if isinstance(asset_hello, dict):
        phone_hello = _apply_hello(phone, asset_hello)
        _json_request(
            remote_server,
            f"/api/direct/handshake?s={remote_server.session_id}",
            method="POST",
            payload=phone_hello,
        )
    asset_frame = cast(dict[str, object], asset_payload["frame"])
    asset_kind, asset = _decrypt_frame(phone, asset_frame)
    asset_data = cast(str, asset["data"])

    assert asset_kind == "asset"
    assert asset["slot"] == "current"
    assert asset["revision"] == "current123"
    assert asset["contentType"] == "image/png"
    assert base64url_decode(asset_data) == b"current-png"

    command_payload = cast(
        dict[str, object],
        json.loads(phone.encode_command_frame("goto_slide", 4)),
    )
    result = _json_request(
        remote_server,
        f"/api/direct/command?s={remote_server.session_id}",
        method="POST",
        payload=command_payload,
    )

    assert result["ok"] is True
    assert _fake_controller(remote_server).commands == [("goto_slide", 4)]


def test_local_fallback_state_requires_pairing_headers(remote_server: RemoteServer) -> None:
    with pytest.raises(HTTPError) as exc_info:
        _json_request(remote_server, "/api/local/state")

    assert exc_info.value.code == 403


def test_local_fallback_state_returns_authenticated_payload(remote_server: RemoteServer) -> None:
    payload = _json_request(
        remote_server,
        "/api/local/state",
        headers=_fallback_headers(remote_server),
    )

    assert payload["transportSecurity"] == "local-authenticated-plaintext"
    assert payload["notes"] == "Speaker notes"
    assert payload["currentSlideImageUrl"] == "/api/local/slide/current?rev=current123"


def test_local_fallback_command_requires_small_payload(remote_server: RemoteServer) -> None:
    with pytest.raises(HTTPError) as exc_info:
        _request(
            remote_server,
            "/api/local/command",
            method="POST",
            data=b'{"command":"' + (b"x" * 17000) + b'"}',
            headers=_fallback_headers(remote_server) | {"Content-Type": "application/json"},
        )

    assert exc_info.value.code == 413


def test_local_fallback_command_controls_presentation(remote_server: RemoteServer) -> None:
    _json_request(
        remote_server,
        "/api/local/command",
        method="POST",
        payload={"command": "goto_slide", "index": 3},
        headers=_fallback_headers(remote_server),
    )

    assert _fake_controller(remote_server).commands == [("goto_slide", 3)]


def test_slide_endpoints_reject_stale_revisions(remote_server: RemoteServer) -> None:
    _complete_direct_handshake(remote_server)

    with pytest.raises(HTTPError) as direct_error:
        _json_request(
            remote_server,
            f"/api/direct/slide/current?s={remote_server.session_id}&rev=stale",
        )
    with pytest.raises(HTTPError) as fallback_error:
        _request(
            remote_server,
            "/api/local/slide/current?rev=stale",
            headers=_fallback_headers(remote_server),
        )

    assert direct_error.value.code == 409
    assert fallback_error.value.code == 409


def test_local_fallback_slide_endpoint_serves_current_png(remote_server: RemoteServer) -> None:
    with _request(
        remote_server,
        "/api/local/slide/current?rev=current123",
        headers=_fallback_headers(remote_server),
    ) as response:
        data = response.read()

    assert response.headers["Content-Type"] == "image/png"
    assert data == b"current-png"


def test_local_compatibility_client_filter_rejects_global_addresses() -> None:
    assert _is_local_compatibility_client("192.168.1.20")
    assert _is_local_compatibility_client("fd12:3456:789a::12")
    assert not _is_local_compatibility_client("2606:4700:4700::1111")
