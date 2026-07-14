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
        expired = [key for key, session in self.sessions.items() if session.empty() or now - session.last_seen > self.session_ttl]
        for key in expired:
            self.sessions.pop(key, None)


def create_app(state: RelayState | None = None) -> web.Application:
    app = web.Application()
    app["relay_state"] = state or RelayState()
    app.router.add_get("/health", health)
    app.router.add_get("/", index)
    app.router.add_get("/ws", websocket_handler)
    return app


async def health(request: web.Request) -> web.Response:
    state: RelayState = request.app["relay_state"]
    state.cleanup()
    return web.json_response({"ok": True, "sessions": len(state.sessions)})


async def index(_request: web.Request) -> web.Response:
    return web.Response(text="LibreOffice Impress Remote relay is running.\n", content_type="text/plain")


async def websocket_handler(request: web.Request) -> web.WebSocketResponse:
    role = request.query.get("role", "")
    session_id = request.query.get("session", "")
    if role not in {"plugin", "phone"} or not session_id:
        raise web.HTTPBadRequest(text="role and session are required")
    ws = web.WebSocketResponse(heartbeat=30)
    await ws.prepare(request)
    state: RelayState = request.app["relay_state"]
    session = state.get(session_id)
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
    await asyncio.gather(*(send_message(target, message) for target in targets), return_exceptions=True)


async def send_message(target: Any, message: Any) -> None:
    if message.type == WSMsgType.TEXT:
        await target.send_str(message.data)
    elif message.type == WSMsgType.BINARY:
        await target.send_bytes(message.data)
