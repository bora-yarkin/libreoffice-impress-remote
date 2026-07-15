# SPDX-FileCopyrightText: 2026 Bora Yarkın
# SPDX-License-Identifier: GPL-3.0-only

from __future__ import annotations

import asyncio
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
        text="LibreOffice Impress Remote relay is running.\n",
        content_type="text/plain",
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
    else:
        session.phones.add(ws)
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
        if role == "phone":
            session.phones.discard(ws)
        state.cleanup()
    return ws


async def relay_message(session: RelaySession, role: str, message: Any) -> None:
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
