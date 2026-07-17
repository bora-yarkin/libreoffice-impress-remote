# SPDX-FileCopyrightText: 2026 Bora Yarkın
# SPDX-License-Identifier: GPL-3.0-only

from aiohttp import WSMsgType
from aiohttp.test_utils import TestClient, TestServer, make_mocked_request
import pytest

from impress_remote_relay.relay import RelayState, create_app, health


@pytest.mark.asyncio
async def test_health_reports_empty_state() -> None:
    state = RelayState()
    request = make_mocked_request("GET", "/health", app={"relay_state": state})
    response = await health(request)
    assert response.status == 200


def test_cleanup_removes_expired_sessions() -> None:
    state = RelayState(session_ttl=1)
    session = state.get("demo")
    session.last_seen -= 60
    state.cleanup()
    assert not state.sessions


@pytest.mark.asyncio
async def test_relay_forwards_plugin_message_to_phone() -> None:
    server = TestServer(create_app(RelayState()))
    client = TestClient(server)
    await client.start_server()
    try:
        plugin = await client.ws_connect("/ws?role=plugin&session=demo")
        phone = await client.ws_connect("/ws?role=phone&session=demo")
        await plugin.send_str("next-slide")
        message = await phone.receive(timeout=1)
        assert message.type == WSMsgType.TEXT
        assert message.data == "next-slide"
        await plugin.close()
        await phone.close()
    finally:
        await client.close()


@pytest.mark.asyncio
async def test_relay_forwards_phone_message_to_plugin() -> None:
    server = TestServer(create_app(RelayState()))
    client = TestClient(server)
    await client.start_server()
    try:
        plugin = await client.ws_connect("/ws?role=plugin&session=demo")
        phone = await client.ws_connect("/ws?role=phone&session=demo")
        await phone.send_str('{"type":"command","command":"next_slide"}')
        message = await plugin.receive(timeout=1)
        assert message.type == WSMsgType.TEXT
        assert "next_slide" in message.data
        await plugin.close()
        await phone.close()
    finally:
        await client.close()


@pytest.mark.asyncio
async def test_second_plugin_replaces_first_one() -> None:
    server = TestServer(create_app(RelayState()))
    client = TestClient(server)
    await client.start_server()
    try:
        first = await client.ws_connect("/ws?role=plugin&session=demo")
        second = await client.ws_connect("/ws?role=plugin&session=demo")
        replaced = await first.receive(timeout=1)
        assert replaced.type == WSMsgType.CLOSE
        await second.close()
    finally:
        await client.close()


@pytest.mark.asyncio
async def test_root_serves_relay_ui() -> None:
    server = TestServer(create_app(RelayState()))
    client = TestClient(server)
    await client.start_server()
    try:
        response = await client.get("/")
        assert response.status == 200
        body = await response.text()
        assert "Relay Presenter" in body
    finally:
        await client.close()


@pytest.mark.asyncio
async def test_new_phone_receives_cached_hello_and_latest_state_frame() -> None:
    server = TestServer(create_app(RelayState()))
    client = TestClient(server)
    await client.start_server()
    try:
        plugin = await client.ws_connect("/ws?role=plugin&session=demo")
        await plugin.send_str(
            '{"type":"hello","v":1,"s":"demo","k":"kid123","nonce":"nonce123"}'
        )
        await plugin.send_str(
            '{"type":"frame","v":1,"s":"demo","k":"kid123","kind":"state","n":"nonce456","ct":"ciphertext"}'
        )

        phone = await client.ws_connect("/ws?role=phone&session=demo")
        first = await phone.receive(timeout=1)
        second = await phone.receive(timeout=1)

        assert first.type == WSMsgType.TEXT
        assert second.type == WSMsgType.TEXT
        assert first.data == '{"type":"hello","v":1,"s":"demo","k":"kid123","nonce":"nonce123"}'
        assert second.data == '{"type":"frame","v":1,"s":"demo","k":"kid123","kind":"state","n":"nonce456","ct":"ciphertext"}'
        await plugin.close()
        await phone.close()
    finally:
        await client.close()


@pytest.mark.asyncio
async def test_plugin_disconnect_clears_cached_secure_state() -> None:
    state = RelayState()
    server = TestServer(create_app(state))
    client = TestClient(server)
    await client.start_server()
    try:
        plugin = await client.ws_connect("/ws?role=plugin&session=demo")
        phone = await client.ws_connect("/ws?role=phone&session=demo")
        await plugin.send_str(
            '{"type":"hello","v":1,"s":"demo","k":"kid123","nonce":"nonce123"}'
        )
        await plugin.send_str(
            '{"type":"frame","v":1,"s":"demo","k":"kid123","kind":"state","n":"nonce456","ct":"ciphertext"}'
        )
        await phone.receive(timeout=1)
        await phone.receive(timeout=1)
        await plugin.close()
        session = state.sessions["demo"]
        assert session.latest_plugin_hello == ""
        assert session.latest_state_frame == ""
        await phone.close()
    finally:
        await client.close()
