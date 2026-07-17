# SPDX-FileCopyrightText: 2026 Bora Yarkın
# SPDX-License-Identifier: GPL-3.0-only

from __future__ import annotations

import asyncio
from importlib import resources
import json
import time
from dataclasses import dataclass, field
from typing import Any

from aiohttp import WSMsgType, web

from impress_remote_relay.session import RelaySession


@dataclass
class RelayState:
    session_ttl: int = 3600
    max_phones_per_session: int = 8
    max_message_bytes: int = 1024 * 1024
    max_session_id_length: int = 128
    sessions: dict[str, RelaySession] = field(default_factory=dict)

    def get(self, session_id: str) -> RelaySession:
        session = self.sessions.get(session_id)
        if session is None:
            session = RelaySession(session_id=session_id)
            self.sessions[session_id] = session
        session.touch()
        return session

    def cleanup(self) -> None:
        now = time.time()
        expired = [
            key
            for key, session in self.sessions.items()
            if session.empty() or now - session.last_seen > self.session_ttl
        ]
        for key in expired:
            self.sessions.pop(key, None)


RELAY_STATE_KEY = web.AppKey("relay_state", RelayState)


def get_relay_state(app) -> RelayState:
    if RELAY_STATE_KEY in app:
        return app[RELAY_STATE_KEY]
    return app["relay_state"]


def create_app(state: RelayState | None = None) -> web.Application:
    app = web.Application()
    app[RELAY_STATE_KEY] = state or RelayState()
    app.router.add_get("/health", health)
    app.router.add_get("/", index)
    app.router.add_get("/index.html", index)
    app.router.add_get("/app.js", app_js)
    app.router.add_get("/app.css", app_css)
    app.router.add_get("/ws", websocket_handler)
    return app


async def health(request: web.Request) -> web.Response:
    state = get_relay_state(request.app)
    state.cleanup()
    return web.json_response(
        {
            "ok": True,
            "sessions": len(state.sessions),
            "limits": {
                "sessionTtl": state.session_ttl,
                "maxPhonesPerSession": state.max_phones_per_session,
                "maxMessageBytes": state.max_message_bytes,
                "maxSessionIdLength": state.max_session_id_length,
            },
            "active": [session.snapshot() for session in state.sessions.values()],
        }
    )


async def index(_request: web.Request) -> web.Response:
    return web.Response(
        text=_read_web_asset("index.html"),
        content_type="text/html",
    )


async def app_js(_request: web.Request) -> web.Response:
    return web.Response(
        text=_read_web_asset("app.js"),
        content_type="application/javascript",
    )


async def app_css(_request: web.Request) -> web.Response:
    return web.Response(
        text=_read_web_asset("app.css"),
        content_type="text/css",
    )


async def websocket_handler(request: web.Request) -> web.WebSocketResponse:
    role = request.query.get("role", "")
    session_id = request.query.get("session", "")
    if role not in {"plugin", "phone"} or not session_id:
        raise web.HTTPBadRequest(text="role and session are required")
    state = get_relay_state(request.app)
    if len(session_id) > state.max_session_id_length:
        raise web.HTTPBadRequest(text="session id is too long")
    session = state.get(session_id)
    if role == "phone" and session.phone_count() >= state.max_phones_per_session:
        raise web.HTTPTooManyRequests(text="too many phones connected to this session")
    ws = web.WebSocketResponse(heartbeat=30, max_msg_size=state.max_message_bytes)
    await ws.prepare(request)
    if role == "plugin":
        if session.plugin is not None:
            await session.plugin.close(code=4000, message=b"plugin replaced")
        session.plugin = ws
        session.latest_plugin_hello = ""
        session.latest_state_frame = ""
    else:
        session.phones.add(ws)
        if session.latest_plugin_hello:
            await ws.send_str(session.latest_plugin_hello)
        if session.latest_state_frame:
            await ws.send_str(session.latest_state_frame)
    try:
        async for message in ws:
            session.touch()
            if message.type in {WSMsgType.TEXT, WSMsgType.BINARY}:
                await relay_message(session, role, message)
            elif message.type == WSMsgType.ERROR:
                break
    finally:
        if role == "plugin" and session.plugin is ws:
            session.plugin = None
            session.latest_plugin_hello = ""
            session.latest_state_frame = ""
        if role == "phone":
            session.phones.discard(ws)
        state.cleanup()
    return ws


async def relay_message(session: RelaySession, role: str, message: Any) -> None:
    _record_plugin_metadata(session, role, message)
    targets = []
    if role == "plugin":
        targets.extend(phone for phone in session.phones if not phone.closed)
    elif session.plugin is not None and not session.plugin.closed:
        targets.append(session.plugin)
    await asyncio.gather(
        *(send_message(target, message) for target in targets),
        return_exceptions=True,
    )


async def send_message(target: Any, message: Any) -> None:
    if message.type == WSMsgType.TEXT:
        await target.send_str(message.data)
    elif message.type == WSMsgType.BINARY:
        await target.send_bytes(message.data)


def _record_plugin_metadata(session: RelaySession, role: str, message: Any) -> None:
    if role != "plugin" or message.type != WSMsgType.TEXT:
        return
    try:
        payload = json.loads(message.data)
    except (TypeError, json.JSONDecodeError):
        return
    if not isinstance(payload, dict):
        return
    message_type = payload.get("type")
    if message_type == "hello":
        session.latest_plugin_hello = message.data
        session.latest_state_frame = ""
        return
    if message_type == "frame" and payload.get("kind") == "state":
        if session.latest_plugin_hello and payload.get("k") == _hello_key_id(session.latest_plugin_hello):
            session.latest_state_frame = message.data


def _hello_key_id(raw_hello: str) -> str:
    try:
        payload = json.loads(raw_hello)
    except (TypeError, json.JSONDecodeError):
        return ""
    if not isinstance(payload, dict):
        return ""
    key_id = payload.get("k")
    return key_id if isinstance(key_id, str) else ""


def _read_web_asset(name: str) -> str:
    return resources.files("impress_remote_relay.web").joinpath(name).read_text(encoding="utf-8")
