# SPDX-FileCopyrightText: 2026 Bora Yarkın
# SPDX-License-Identifier: GPL-3.0-only

import asyncio
import json

from aiohttp import WSMsgType
from aiohttp.test_utils import TestClient, TestServer, make_mocked_request
import pytest

from impress_remote.protocol import (
    SecureRelayCodec,
    decode_command_payload,
    decode_hello_message,
    encode_hello_message,
)
from impress_remote_relay.relay import RelayState, create_app, health

PAIRING_SECRET = "6o2T5h1XXg3YbqfQ9F0P9v38dGrBvM8UuB8jv3j1fKQ"
SESSION_ID = "demo"


def _build_secure_codecs() -> tuple[SecureRelayCodec, SecureRelayCodec, str]:
    plugin = SecureRelayCodec(
        role="plugin",
        session_id=SESSION_ID,
        pairing_secret=PAIRING_SECRET,
    )
    phone = SecureRelayCodec(
        role="phone",
        session_id=SESSION_ID,
        pairing_secret=PAIRING_SECRET,
    )
    hello = plugin.rotate_send_key()
    phone.apply_hello(hello)
    return plugin, phone, encode_hello_message(hello)


@pytest.mark.asyncio
async def test_health_reports_empty_state() -> None:
    state = RelayState()
    request = make_mocked_request("GET", "/health", app={"relay_state": state})
    response = await health(request)
    assert response.status == 200
    response_text = response.text
    assert response_text is not None
    payload = json.loads(response_text)
    assert "metrics" in payload


def test_cleanup_removes_expired_sessions() -> None:
    state = RelayState(session_ttl=1)
    session = state.get(SESSION_ID)
    assert session is not None
    session.last_seen -= 60
    state.cleanup()
    assert not state.sessions


@pytest.mark.asyncio
async def test_relay_forwards_plugin_encrypted_state_frame_to_phone() -> None:
    server = TestServer(create_app(RelayState()))
    client = TestClient(server)
    await client.start_server()
    try:
        plugin_socket = await client.ws_connect(
            f"/ws?role=plugin&session={SESSION_ID}&a=join-token"
        )
        phone_socket = await client.ws_connect(
            f"/ws?role=phone&session={SESSION_ID}&a=join-token"
        )
        plugin_codec, phone_codec, hello_raw = _build_secure_codecs()

        await plugin_socket.send_str(hello_raw)
        hello_message = await phone_socket.receive(timeout=1)
        assert hello_message.type == WSMsgType.TEXT
        assert hello_message.data == hello_raw

        await plugin_socket.send_str(plugin_codec.encode_state_frame({"running": True, "slideCount": 3}))
        frame_message = await phone_socket.receive(timeout=1)
        assert frame_message.type == WSMsgType.TEXT
        decoded = phone_codec.decode_frame(frame_message.data)
        assert decoded is not None
        assert decoded.kind == "state"
        assert decoded.payload["slideCount"] == 3

        await plugin_socket.close()
        await phone_socket.close()
    finally:
        await client.close()


@pytest.mark.asyncio
async def test_relay_forwards_phone_encrypted_command_frame_to_plugin() -> None:
    server = TestServer(create_app(RelayState()))
    client = TestClient(server)
    await client.start_server()
    try:
        plugin_socket = await client.ws_connect(
            f"/ws?role=plugin&session={SESSION_ID}&a=join-token"
        )
        phone_socket = await client.ws_connect(
            f"/ws?role=phone&session={SESSION_ID}&a=join-token"
        )
        plugin_codec, phone_codec, hello_raw = _build_secure_codecs()

        await plugin_socket.send_str(hello_raw)
        await phone_socket.receive(timeout=1)

        await phone_socket.send_str(phone_codec.encode_command_frame("next_slide"))
        frame_message = await plugin_socket.receive(timeout=1)
        assert frame_message.type == WSMsgType.TEXT
        decoded = plugin_codec.decode_frame(frame_message.data)
        assert decoded is not None
        command = decode_command_payload(decoded.payload)
        assert command is not None
        assert command.command == "next_slide"

        await plugin_socket.close()
        await phone_socket.close()
    finally:
        await client.close()


@pytest.mark.asyncio
async def test_second_plugin_replaces_first_one() -> None:
    server = TestServer(create_app(RelayState()))
    client = TestClient(server)
    await client.start_server()
    try:
        first = await client.ws_connect(f"/ws?role=plugin&session={SESSION_ID}&a=join-token")
        second = await client.ws_connect(f"/ws?role=plugin&session={SESSION_ID}&a=join-token")
        replaced = await first.receive(timeout=1)
        assert replaced.type == WSMsgType.CLOSE
        await second.close()
    finally:
        await client.close()


@pytest.mark.asyncio
async def test_root_serves_lightweight_relay_ui() -> None:
    server = TestServer(create_app(RelayState()))
    client = TestClient(server)
    await client.start_server()
    try:
        response = await client.get("/")
        assert response.status == 200
        body = await response.text()
        assert 'id="slide-frame"' in body
        assert 'id="notes"' in body
    finally:
        await client.close()


@pytest.mark.asyncio
async def test_asset_manifest_is_served() -> None:
    server = TestServer(create_app(RelayState()))
    client = TestClient(server)
    await client.start_server()
    try:
        response = await client.get("/asset-manifest.json")
        assert response.status == 200
        payload = await response.json()
        assert "files" in payload
        assert "app.js" in payload["files"]
    finally:
        await client.close()


@pytest.mark.asyncio
async def test_new_phone_receives_cached_hello_state_and_asset_frames() -> None:
    server = TestServer(create_app(RelayState()))
    client = TestClient(server)
    await client.start_server()
    try:
        plugin_socket = await client.ws_connect(
            f"/ws?role=plugin&session={SESSION_ID}&a=join-token"
        )
        plugin_codec, phone_codec, hello_raw = _build_secure_codecs()
        await plugin_socket.send_str(hello_raw)
        await plugin_socket.send_str(
            plugin_codec.encode_state_frame(
                {
                    "running": True,
                    "slideCount": 4,
                    "currentSlide": 1,
                    "currentSlideImageRevision": "current123",
                    "nextSlideImageRevision": "next456",
                }
            )
        )
        await plugin_socket.send_str(
            plugin_codec.encode_asset_frame(
                {
                    "contentType": "image/png",
                    "encoding": "base64url",
                    "data": "aGVsbG8",
                    "slot": "current",
                    "revision": "current123",
                }
            )
        )
        await plugin_socket.send_str(
            plugin_codec.encode_asset_frame(
                {
                    "contentType": "image/png",
                    "encoding": "base64url",
                    "data": "d29ybGQ",
                    "slot": "next",
                    "revision": "next456",
                }
            )
        )

        phone_socket = await client.ws_connect(
            f"/ws?role=phone&session={SESSION_ID}&a=join-token"
        )
        messages = [await phone_socket.receive(timeout=1) for _ in range(4)]
        assert [message.type for message in messages] == [WSMsgType.TEXT] * 4
        assert messages[0].data == hello_raw

        decoded_frames = [phone_codec.decode_frame(message.data) for message in messages[1:]]
        assert [frame.kind for frame in decoded_frames if frame is not None] == ["state", "asset", "asset"]
        assert decoded_frames[1] is not None
        assert decoded_frames[2] is not None
        assert decoded_frames[1].payload["slot"] == "current"
        assert decoded_frames[2].payload["slot"] == "next"

        await plugin_socket.close()
        await phone_socket.close()
    finally:
        await client.close()


@pytest.mark.asyncio
async def test_plugin_disconnect_clears_cached_secure_frames() -> None:
    state = RelayState()
    server = TestServer(create_app(state))
    client = TestClient(server)
    await client.start_server()
    try:
        plugin_socket = await client.ws_connect(
            f"/ws?role=plugin&session={SESSION_ID}&a=join-token"
        )
        plugin_codec, _phone_codec, hello_raw = _build_secure_codecs()
        await plugin_socket.send_str(hello_raw)
        await plugin_socket.send_str(plugin_codec.encode_state_frame({"running": True}))
        await plugin_socket.close()

        assert SESSION_ID not in state.sessions
    finally:
        await client.close()


@pytest.mark.asyncio
async def test_legacy_plaintext_phone_messages_are_rejected() -> None:
    server = TestServer(create_app(RelayState()))
    client = TestClient(server)
    await client.start_server()
    try:
        plugin_socket = await client.ws_connect(
            f"/ws?role=plugin&session={SESSION_ID}&a=join-token"
        )
        phone_socket = await client.ws_connect(
            f"/ws?role=phone&session={SESSION_ID}&a=join-token"
        )
        _plugin_codec, _phone_codec, hello_raw = _build_secure_codecs()

        await plugin_socket.send_str(hello_raw)
        await phone_socket.receive(timeout=1)

        await phone_socket.send_str('{"type":"command","command":"next_slide"}')
        error_message = await phone_socket.receive(timeout=1)
        assert error_message.type == WSMsgType.TEXT
        payload = json.loads(error_message.data)
        assert payload["type"] == "error"
        assert payload["code"] == "invalid-type"

        closing = await phone_socket.receive(timeout=1)
        assert closing.type in {WSMsgType.CLOSE, WSMsgType.CLOSING, WSMsgType.CLOSED}

        with pytest.raises(asyncio.TimeoutError):
            await asyncio.wait_for(plugin_socket.receive(), timeout=0.2)

        await plugin_socket.close()
    finally:
        await client.close()


@pytest.mark.asyncio
async def test_phone_without_admission_token_is_rejected() -> None:
    server = TestServer(create_app(RelayState()))
    client = TestClient(server)
    await client.start_server()
    try:
        response = await client.get(f"/api/session?session={SESSION_ID}")
        assert response.status == 404

        plugin_socket = await client.ws_connect(f"/ws?role=plugin&session={SESSION_ID}&a=join-token")
        response = await client.get(f"/api/session?session={SESSION_ID}")
        assert response.status == 403
        await plugin_socket.close()
    finally:
        await client.close()


@pytest.mark.asyncio
async def test_session_status_requires_matching_admission_token() -> None:
    state = RelayState()
    server = TestServer(create_app(state))
    client = TestClient(server)
    await client.start_server()
    try:
        plugin_socket = await client.ws_connect(f"/ws?role=plugin&session={SESSION_ID}&a=join-token")
        response = await client.get(f"/api/session?session={SESSION_ID}&a=join-token")
        assert response.status == 200
        payload = await response.json()
        assert payload["session"]["admissionControlled"] is True
        assert payload["session"]["waitingForPlugin"] is False
        assert payload["session"]["phones"] == 0

        denied = await client.get(f"/api/session?session={SESSION_ID}&a=wrong-token")
        assert denied.status == 403
        await plugin_socket.close()
    finally:
        await client.close()


@pytest.mark.asyncio
async def test_phone_stays_connected_and_receives_fresh_hello_after_plugin_reconnects() -> None:
    state = RelayState()
    server = TestServer(create_app(state))
    client = TestClient(server)
    await client.start_server()
    try:
        plugin_socket = await client.ws_connect(f"/ws?role=plugin&session={SESSION_ID}&a=join-token")
        phone_socket = await client.ws_connect(f"/ws?role=phone&session={SESSION_ID}&a=join-token")
        first_plugin, first_phone, hello_raw = _build_secure_codecs()
        await plugin_socket.send_str(hello_raw)
        first_hello = await phone_socket.receive(timeout=1)
        assert first_hello.type == WSMsgType.TEXT
        assert first_hello.data == hello_raw
        await plugin_socket.send_str(first_plugin.encode_state_frame({"running": True, "slideCount": 2}))
        first_state_message = await phone_socket.receive(timeout=1)
        first_state = first_phone.decode_frame(first_state_message.data)
        assert first_state is not None
        assert first_state.payload["slideCount"] == 2
        await plugin_socket.close()

        second_plugin, _second_phone, second_hello_raw = _build_secure_codecs()
        plugin_socket = await client.ws_connect(f"/ws?role=plugin&session={SESSION_ID}&a=join-token")
        await plugin_socket.send_str(second_hello_raw)
        refreshed_hello = await phone_socket.receive(timeout=1)
        assert refreshed_hello.type == WSMsgType.TEXT
        assert refreshed_hello.data == second_hello_raw
        second_hello = decode_hello_message(refreshed_hello.data)
        assert second_hello is not None

        await plugin_socket.send_str(second_plugin.encode_state_frame({"running": True, "slideCount": 7}))
        frame_message = await phone_socket.receive(timeout=1)
        reconnect_phone = SecureRelayCodec(
            role="phone",
            session_id=SESSION_ID,
            pairing_secret=PAIRING_SECRET,
        )
        reconnect_phone.apply_hello(second_hello)
        decoded = reconnect_phone.decode_frame(frame_message.data)
        assert decoded is not None
        assert decoded.kind == "state"
        assert decoded.payload["slideCount"] == 7
        await plugin_socket.close()
    finally:
        await client.close()


@pytest.mark.asyncio
async def test_rate_limit_rejects_noisy_phone_connections() -> None:
    state = RelayState(max_messages_per_window=1, message_window_seconds=60.0)
    server = TestServer(create_app(state))
    client = TestClient(server)
    await client.start_server()
    try:
        plugin_socket = await client.ws_connect(f"/ws?role=plugin&session={SESSION_ID}&a=join-token")
        phone_socket = await client.ws_connect(f"/ws?role=phone&session={SESSION_ID}&a=join-token")
        _plugin_codec, phone_codec, hello_raw = _build_secure_codecs()

        await plugin_socket.send_str(hello_raw)
        await phone_socket.receive(timeout=1)

        await phone_socket.send_str(phone_codec.encode_command_frame("next_slide"))
        await phone_socket.send_str(phone_codec.encode_command_frame("next_slide"))
        error_message = await phone_socket.receive(timeout=1)
        assert error_message.type == WSMsgType.TEXT
        payload = json.loads(error_message.data)
        assert payload["code"] == "rate-limit"
        closing = await phone_socket.receive(timeout=1)
        assert closing.type in {WSMsgType.CLOSE, WSMsgType.CLOSING, WSMsgType.CLOSED}

        await plugin_socket.close()
    finally:
        await client.close()
