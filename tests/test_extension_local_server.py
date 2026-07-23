# SPDX-FileCopyrightText: 2026 Bora Yarkın
# SPDX-License-Identifier: GPL-3.0-only
# ruff: noqa: E402,F811

from __future__ import annotations

import json
import socket
import unittest
from typing import cast

from types import SimpleNamespace

from impress_remote.config import RemoteConfig
from impress_remote.local_server import RemoteServer, SecureDirectSession, _url_with_fragment_params
from impress_remote.protocol import SecureRelayCodec, decode_hello_message, encode_hello_message


class PairingServerStub:
    route_urls = RemoteServer.route_urls
    preview_route_urls = RemoteServer.preview_route_urls
    pairing_target = RemoteServer.pairing_target
    preview_pairing_target = RemoteServer.preview_pairing_target
    console_url = RemoteServer.console_url
    mark_client_activity = RemoteServer.mark_client_activity
    _start_presentation_for_client = RemoteServer._start_presentation_for_client
    _pairing_hint = RemoteServer._pairing_hint
    _direct_ipv6_status = RemoteServer._direct_ipv6_status
    _direct_ipv6_hint = RemoteServer._direct_ipv6_hint
    _network_settings = RemoteServer._network_settings
    _route_mode = RemoteServer._route_mode
    _route_uses_local_listener = RemoteServer._route_uses_local_listener

    def __init__(
        self,
        *,
        running: bool = True,
        local_urls: list[str] | None = None,
        direct_urls: list[str] | None = None,
        enable_relay: bool = False,
        relay_url: str = "",
        preferred_route: str = "local",
        enable_local_listener: bool = True,
        enable_tunnel: bool = True,
        enable_ipv6_direct: bool = True,
        local_port: int = 17865,
    ) -> None:
        self._running = running
        self.http_servers = []
        if running and enable_local_listener:
            self.http_servers.append(SimpleNamespace(address_family=socket.AF_INET))
        if running and enable_ipv6_direct:
            self.http_servers.append(SimpleNamespace(address_family=socket.AF_INET6))
        self.local_urls = local_urls or []
        self.direct_urls = direct_urls or []
        self.direct_ipv6_addresses = ["2606:4700:4700::1111"] if direct_urls else []
        self.direct_ipv6_ready_addresses = ["2606:4700:4700::1111"] if direct_urls else []
        self.session_id = "demo123"
        self.pairing_secret = "pairsecret"
        self.relay_admission_token = "relaytoken"
        self.url = ""
        self.bound_port = local_port
        self.commands: list[tuple[str, int | None]] = []
        self.config = RemoteConfig(
            local_port=local_port,
            enable_relay=enable_relay,
            relay_url=relay_url,
            preferred_route=preferred_route,
            enable_local_listener=enable_local_listener,
            enable_tunnel=enable_tunnel,
            tunnel_host="https://localtunnel.me",
            tunnel_subdomain="",
            enable_ipv6_direct=enable_ipv6_direct,
        )
        self.tunnel_client = None
        self.controller = SimpleNamespace(
            state=lambda: SimpleNamespace(
                document_kind="impress",
                running=False,
                slide_count=len(self.local_urls) or 3,
            ),
            command=lambda name, index=None: self.commands.append((name, index)),
        )
        self._active_network_settings = (local_port, preferred_route)
        self.client_connected = False
        self.client_connection_source = ""
        self.last_client_seen_at = 0.0

    def is_running(self) -> bool:
        return self._running


class LocalServerTests(unittest.TestCase):
    def test_url_with_fragment_params_preserves_existing_fragment_values(self) -> None:
        self.assertEqual(
            _url_with_fragment_params(
                "http://127.0.0.1:17865/#mode=local&s=demo123&k=pairsecret",
                view="settings",
            ),
            "http://127.0.0.1:17865/#mode=local&s=demo123&k=pairsecret&view=settings",
        )

    def test_url_with_fragment_params_replaces_existing_values(self) -> None:
        self.assertEqual(
            _url_with_fragment_params(
                "http://127.0.0.1:17865/#mode=local&s=demo123&k=pairsecret&view=console",
                view="settings",
            ),
            "http://127.0.0.1:17865/#mode=local&s=demo123&k=pairsecret&view=settings",
        )

    def test_current_slide_image_url_is_empty_without_an_impress_slide(self) -> None:
        state = SimpleNamespace(document_kind="none", slide_count=0, current_render_token="")
        server = cast(RemoteServer, SimpleNamespace(controller=None, session_id="demo123"))

        self.assertEqual(
            RemoteServer.current_slide_image_url(server, state),
            "",
        )

    def test_current_slide_image_url_uses_the_render_token(self) -> None:
        state = SimpleNamespace(
            document_kind="impress",
            slide_count=8,
            current_render_token="current123",
        )
        server = cast(RemoteServer, SimpleNamespace(controller=None, session_id="demo123"))

        self.assertEqual(
            RemoteServer.current_slide_image_url(server, state),
            "/api/direct/slide/current?s=demo123&rev=current123",
        )

    def test_next_slide_image_url_is_empty_without_a_next_slide(self) -> None:
        state = SimpleNamespace(next_slide=None, next_render_token="")
        server = cast(RemoteServer, SimpleNamespace(controller=None, session_id="demo123"))

        self.assertEqual(
            RemoteServer.next_slide_image_url(server, state),
            "",
        )

    def test_next_slide_image_url_uses_the_render_token(self) -> None:
        state = SimpleNamespace(next_slide=3, next_render_token="next456")
        server = cast(RemoteServer, SimpleNamespace(controller=None, session_id="demo123"))

        self.assertEqual(
            RemoteServer.next_slide_image_url(server, state),
            "/api/direct/slide/next?s=demo123&rev=next456",
        )

    def test_local_fallback_current_slide_image_url_uses_authenticated_endpoint(self) -> None:
        state = SimpleNamespace(
            document_kind="impress",
            slide_count=8,
            current_render_token="current123",
        )
        server = cast(RemoteServer, SimpleNamespace(controller=None))

        self.assertEqual(
            RemoteServer.local_fallback_current_slide_image_url(server, state),
            "/api/local/slide/current?rev=current123",
        )

    def test_local_fallback_next_slide_image_url_uses_authenticated_endpoint(self) -> None:
        state = SimpleNamespace(next_slide=3, next_render_token="next456")
        server = cast(RemoteServer, SimpleNamespace(controller=None))

        self.assertEqual(
            RemoteServer.local_fallback_next_slide_image_url(server, state),
            "/api/local/slide/next?rev=next456",
        )

    def test_local_fallback_state_payload_marks_plaintext_compatibility_transport(self) -> None:
        state = SimpleNamespace(
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
        class StatePayloadServerStub:
            _state_payload = RemoteServer._state_payload
            local_fallback_current_slide_image_url = (
                RemoteServer.local_fallback_current_slide_image_url
            )
            local_fallback_next_slide_image_url = RemoteServer.local_fallback_next_slide_image_url

            def __init__(self) -> None:
                self.controller = SimpleNamespace(state=lambda: state)

            def connection_info(self) -> dict[str, object]:
                return {"session": "demo123"}

        server = cast(RemoteServer, StatePayloadServerStub())

        payload = RemoteServer.local_fallback_state_payload(server)

        self.assertEqual(payload["transportSecurity"], "local-authenticated-plaintext")
        self.assertEqual(payload["currentSlideImageUrl"], "/api/local/slide/current?rev=current123")
        self.assertEqual(payload["nextSlideImageUrl"], "/api/local/slide/next?rev=next456")

    def test_prewarm_local_slide_cache_records_controller_status(self) -> None:
        controller = SimpleNamespace(
            prewarm_slide_previews=lambda: {
                "state": "ready",
                "slides": 4,
                "cacheSize": 12,
            },
        )
        server = cast(
            RemoteServer,
            SimpleNamespace(
                http_servers=[object()],
                controller=controller,
                listener_warnings=[],
            ),
        )

        RemoteServer._prewarm_local_slide_cache(server)

        self.assertEqual(
            server.preload_status,
            {"state": "ready", "slides": 4, "cacheSize": 12, "lastError": ""},
        )

    def test_prewarm_local_slide_cache_records_non_fatal_failures(self) -> None:
        def fail():
            raise RuntimeError("export failed")

        server = cast(
            RemoteServer,
            SimpleNamespace(
                http_servers=[object()],
                controller=SimpleNamespace(prewarm_slide_previews=fail),
                listener_warnings=[],
            ),
        )

        RemoteServer._prewarm_local_slide_cache(server)

        self.assertEqual(server.preload_status["state"], "error")
        self.assertEqual(server.preload_status["lastError"], "export failed")
        self.assertTrue(server.listener_warnings)

    def test_relay_asset_payload_encodes_current_slide_png_for_the_expected_revision(self) -> None:
        state = SimpleNamespace(
            document_kind="impress",
            slide_count=5,
            current_render_token="current123",
            next_slide=2,
            next_render_token="next456",
        )
        controller = SimpleNamespace(
            state=lambda: state,
            current_slide_png_bytes=lambda: b"png-bytes",
            next_slide_png_bytes=lambda: b"next-png-bytes",
        )
        server = cast(RemoteServer, SimpleNamespace(controller=controller))

        payload = RemoteServer.relay_asset_payload(server, "current", "current123")

        self.assertIsNotNone(payload)
        assert payload is not None
        self.assertEqual(payload["slot"], "current")
        self.assertEqual(payload["revision"], "current123")
        self.assertEqual(payload["encoding"], "base64url")

    def test_relay_asset_payload_returns_none_when_the_revision_is_stale(self) -> None:
        state = SimpleNamespace(
            document_kind="impress",
            slide_count=5,
            current_render_token="current123",
            next_slide=2,
            next_render_token="next456",
        )
        controller = SimpleNamespace(
            state=lambda: state,
            current_slide_png_bytes=lambda: b"png-bytes",
            next_slide_png_bytes=lambda: b"next-png-bytes",
        )
        server = cast(RemoteServer, SimpleNamespace(controller=controller))

        payload = RemoteServer.relay_asset_payload(server, "current", "stale999")

        self.assertIsNone(payload)

    def test_pairing_target_uses_local_route_by_default(self) -> None:
        server = PairingServerStub(
            local_urls=["http://192.168.1.20:17865/#s=demo123&k=pairsecret"],
            direct_urls=["http://[2606:4700:4700::1111]:17865/#mode=ipv6&s=demo123&k=pairsecret"],
            enable_relay=True,
            relay_url="https://relay.example.com",
        )

        pairing = server.pairing_target()

        self.assertEqual(pairing["requestedRoute"], "local")
        self.assertEqual(pairing["selectedRoute"], "local")
        self.assertEqual(
            pairing["selectedUrl"],
            "http://192.168.1.20:17865/#s=demo123&k=pairsecret",
        )

    def test_pairing_target_uses_explicit_relay_mode(self) -> None:
        server = PairingServerStub(
            local_urls=[],
            direct_urls=[],
            enable_relay=True,
            relay_url="https://relay.example.com/base",
            preferred_route="relay",
        )

        pairing = server.pairing_target()

        self.assertEqual(pairing["requestedRoute"], "relay")
        self.assertEqual(pairing["selectedRoute"], "relay")
        self.assertEqual(
            pairing["selectedUrl"],
            "https://relay.example.com/base#mode=relay&s=demo123&k=pairsecret&a=relaytoken",
        )

    def test_console_url_is_empty_when_selected_route_is_unavailable(self) -> None:
        server = PairingServerStub(
            local_urls=["http://192.168.1.20:17865/#s=demo123&k=pairsecret"],
            direct_urls=[],
            enable_relay=False,
            relay_url="",
            preferred_route="ipv6",
        )

        self.assertEqual(server.console_url(), "")

    def test_mark_client_activity_ignores_loopback_requests(self) -> None:
        server = PairingServerStub()

        server.mark_client_activity("local", "127.0.0.1")

        self.assertFalse(server.client_connected)
        self.assertEqual(server.commands, [])

    def test_mark_client_activity_records_non_loopback_clients(self) -> None:
        server = PairingServerStub()

        server.mark_client_activity("local", "192.168.1.20")

        self.assertTrue(server.client_connected)
        self.assertEqual(server.client_connection_source, "local")
        self.assertEqual(server.commands, [("start_presentation_from_first_slide", None)])

    def test_mark_client_activity_only_auto_starts_on_first_client_connection(self) -> None:
        server = PairingServerStub()

        server.mark_client_activity("local", "192.168.1.20")
        server.mark_client_activity("local", "192.168.1.20")

        self.assertEqual(server.commands, [("start_presentation_from_first_slide", None)])

    def test_direct_ipv6_hint_reports_missing_public_ipv6(self) -> None:
        server = PairingServerStub(direct_urls=[], preferred_route="ipv6")
        server.direct_ipv6_addresses = []
        server.direct_ipv6_ready_addresses = []

        hint = server._direct_ipv6_hint()

        self.assertIn("globally reachable ipv6 address", hint.lower())

    def test_direct_ipv6_hint_reports_self_test_failures(self) -> None:
        server = PairingServerStub(direct_urls=[], preferred_route="ipv6")
        server.direct_ipv6_addresses = ["2606:4700:4700::1111"]
        server.direct_ipv6_ready_addresses = []

        hint = server._direct_ipv6_hint()

        self.assertIn("could not reach its own ipv6 listener", hint.lower())

    def test_secure_direct_session_round_trips_commands_and_assets(self) -> None:
        session = SecureDirectSession("demo", "6o2T5h1XXg3YbqfQ9F0P9v38dGrBvM8UuB8jv3j1fKQ")

        hello = session.current_hello_payload()
        self.assertEqual(hello["type"], "hello")

        phone = SecureRelayCodec(
            role="phone",
            session_id="demo",
            pairing_secret="6o2T5h1XXg3YbqfQ9F0P9v38dGrBvM8UuB8jv3j1fKQ",
        )
        decoded_hello = decode_hello_message(json.dumps(hello))
        self.assertIsNotNone(decoded_hello)
        assert decoded_hello is not None
        phone_hello = phone.apply_hello(decoded_hello)
        self.assertIsNotNone(phone_hello)
        assert phone_hello is not None
        session.apply_phone_hello(
            cast(dict[str, object], json.loads(encode_hello_message(phone_hello)))
        )

        state_response = session.state_response({"running": True, "slideCount": 4})
        self.assertIsNone(state_response["hello"])
        self.assertEqual(cast(dict[str, object], state_response["frame"])["type"], "frame")

        asset_response = session.asset_response(
            content_type="image/png",
            data=b"png-bytes",
            slot="current",
            revision="rev123",
        )
        self.assertEqual(cast(dict[str, object], asset_response["frame"])["kind"], "asset")

        frame = phone.encode_command_frame("next_slide")
        command = session.decode_command(cast(dict[str, object], json.loads(frame)))
        self.assertEqual(command.command, "next_slide")


if __name__ == "__main__":
    unittest.main()


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


def test_plaintext_compatibility_allows_global_clients_only_for_ipv6_route() -> None:
    local_server = RemoteServer(
        ctx=SimpleNamespace(),
        config=RemoteConfig(preferred_route="local"),
    )
    ipv6_server = RemoteServer(
        ctx=SimpleNamespace(),
        config=RemoteConfig(preferred_route="ipv6"),
    )

    assert not local_server.allows_plaintext_compatibility_client("2606:4700:4700::1111")
    assert ipv6_server.allows_plaintext_compatibility_client("2606:4700:4700::1111")
