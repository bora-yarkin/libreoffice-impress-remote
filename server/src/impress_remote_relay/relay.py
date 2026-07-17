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

RELAY_PROTOCOL_VERSION = 1
_PLUGIN_FRAME_KINDS = {"state", "asset", "error"}
_PHONE_FRAME_KINDS = {"command"}
_REPLAYABLE_PLUGIN_FRAME_KINDS = {"state", "asset", "error"}
_SESSION_ID_CHARS = frozenset(
    "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-_"
)


@dataclass(frozen=True)
class _RelayEnvelope:
    message_type: str
    key_id: str = ""
    frame_kind: str = ""


class _RelayProtocolViolation(ValueError):
    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code
        self.message = message


@dataclass
class RelayState:
    session_ttl: int = 3600
    max_phones_per_session: int = 8
    max_message_bytes: int = 8 * 1024 * 1024
    max_cached_plugin_frames: int = 6
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
                "maxCachedPluginFrames": state.max_cached_plugin_frames,
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
    if not _is_valid_session_id(session_id):
        raise web.HTTPBadRequest(text="session id format is invalid")
    session = state.get(session_id)
    if role == "phone" and session.phone_count() >= state.max_phones_per_session:
        raise web.HTTPTooManyRequests(text="too many phones connected to this session")
    ws = web.WebSocketResponse(heartbeat=30, max_msg_size=state.max_message_bytes)
    await ws.prepare(request)
    if role == "plugin":
        if session.plugin is not None:
            await session.plugin.close(code=4000, message=b"plugin replaced")
        session.plugin = ws
        session.clear_cached_plugin_messages()
    else:
        session.phones.add(ws)
        if session.latest_plugin_hello:
            await ws.send_str(session.latest_plugin_hello)
        for raw_message in session.replayable_plugin_frames():
            await ws.send_str(raw_message)
    try:
        async for message in ws:
            session.touch()
            if message.type == WSMsgType.TEXT:
                accepted = await relay_message(
                    session,
                    role,
                    ws,
                    str(message.data),
                    state.max_cached_plugin_frames,
                )
                if not accepted:
                    break
            elif message.type == WSMsgType.BINARY:
                await _reject_protocol(
                    ws,
                    session_id,
                    "binary-unsupported",
                    "Relay messages must be UTF-8 JSON text.",
                )
                break
            elif message.type == WSMsgType.ERROR:
                break
    finally:
        if role == "plugin" and session.plugin is ws:
            session.plugin = None
            session.clear_cached_plugin_messages()
        if role == "phone":
            session.phones.discard(ws)
        state.cleanup()
    return ws


async def relay_message(
    session: RelaySession,
    role: str,
    ws: web.WebSocketResponse,
    raw_message: str,
    max_cached_plugin_frames: int,
) -> bool:
    try:
        envelope = _validate_protocol_message(
            raw_message,
            role,
            session.session_id,
            session.latest_plugin_hello,
        )
    except _RelayProtocolViolation as exc:
        await _reject_protocol(ws, session.session_id, exc.code, exc.message)
        return False

    _record_plugin_metadata(session, role, envelope, raw_message, max_cached_plugin_frames)
    targets = []
    if role == "plugin":
        targets.extend(phone for phone in session.phones if not phone.closed)
    elif session.plugin is not None and not session.plugin.closed:
        targets.append(session.plugin)
    await asyncio.gather(
        *(send_text_message(target, raw_message) for target in targets),
        return_exceptions=True,
    )
    return True


async def send_text_message(target: Any, raw_message: str) -> None:
    await target.send_str(raw_message)


def _record_plugin_metadata(
    session: RelaySession,
    role: str,
    envelope: _RelayEnvelope,
    raw_message: str,
    max_cached_plugin_frames: int,
) -> None:
    if role != "plugin":
        return
    if envelope.message_type == "hello":
        session.latest_plugin_hello = raw_message
        session.cached_plugin_frames.clear()
        return
    if envelope.message_type != "frame" or envelope.frame_kind not in _REPLAYABLE_PLUGIN_FRAME_KINDS:
        return
    session.cache_plugin_frame(raw_message, max_cached_plugin_frames)


def _hello_key_id(raw_hello: str) -> str:
    try:
        payload = json.loads(raw_hello)
    except (TypeError, json.JSONDecodeError):
        return ""
    if not isinstance(payload, dict):
        return ""
    key_id = payload.get("k")
    return key_id if isinstance(key_id, str) else ""


def _validate_protocol_message(
    raw_message: str,
    role: str,
    session_id: str,
    latest_plugin_hello: str,
) -> _RelayEnvelope:
    try:
        payload = json.loads(raw_message)
    except (TypeError, json.JSONDecodeError) as exc:
        raise _RelayProtocolViolation("invalid-json", "Relay messages must be valid JSON.") from exc
    if not isinstance(payload, dict):
        raise _RelayProtocolViolation("invalid-json", "Relay messages must be JSON objects.")

    message_type = payload.get("type")
    if message_type not in {"hello", "frame", "error"}:
        raise _RelayProtocolViolation(
            "invalid-type",
            "Relay messages must use hello, frame, or error envelopes.",
        )

    version = payload.get("v")
    if not isinstance(version, int) or version != RELAY_PROTOCOL_VERSION:
        raise _RelayProtocolViolation(
            "unsupported-version",
            "Unsupported relay protocol version.",
        )

    bound_session = payload.get("s")
    if not isinstance(bound_session, str) or bound_session != session_id:
        raise _RelayProtocolViolation(
            "session-mismatch",
            "Relay message is bound to another session.",
        )

    if message_type == "hello":
        if role != "plugin":
            raise _RelayProtocolViolation(
                "invalid-role",
                "Only the plugin may publish relay hello messages.",
            )
        key_id = _required_string(payload, "k", "Relay hello is missing a key id.")
        _required_string(payload, "nonce", "Relay hello is missing a plugin nonce.")
        return _RelayEnvelope(message_type="hello", key_id=key_id)

    if message_type == "error":
        if role != "plugin":
            raise _RelayProtocolViolation(
                "invalid-role",
                "Only the plugin may publish plaintext relay errors.",
            )
        _required_string(payload, "code", "Relay error messages need an error code.")
        _required_string(payload, "message", "Relay error messages need an error message.")
        return _RelayEnvelope(message_type="error")

    key_id = _required_string(payload, "k", "Encrypted relay frames need a key id.")
    frame_kind = _required_string(payload, "kind", "Encrypted relay frames need a kind.")
    _required_string(payload, "n", "Encrypted relay frames need a nonce.")
    _required_string(payload, "ct", "Encrypted relay frames need ciphertext.")

    allowed_kinds = _PLUGIN_FRAME_KINDS if role == "plugin" else _PHONE_FRAME_KINDS
    if frame_kind not in allowed_kinds:
        raise _RelayProtocolViolation(
            "invalid-kind",
            "Encrypted relay frame kind is not allowed for this role.",
        )

    if role == "plugin":
        active_key_id = _hello_key_id(latest_plugin_hello)
        if not active_key_id:
            raise _RelayProtocolViolation(
                "missing-hello",
                "The plugin must publish a relay hello before encrypted frames.",
            )
        if key_id != active_key_id:
            raise _RelayProtocolViolation(
                "invalid-key",
                "Plugin frame key id does not match the active relay hello.",
            )
    elif not latest_plugin_hello:
        raise _RelayProtocolViolation(
            "missing-hello",
            "The relay plugin is not ready for encrypted commands yet.",
        )

    return _RelayEnvelope(message_type="frame", key_id=key_id, frame_kind=frame_kind)


def _required_string(payload: dict[str, object], key: str, message: str) -> str:
    value = payload.get(key)
    if not isinstance(value, str) or not value:
        raise _RelayProtocolViolation("invalid-envelope", message)
    return value


async def _reject_protocol(
    ws: web.WebSocketResponse,
    session_id: str,
    code: str,
    message: str,
) -> None:
    try:
        if not ws.closed:
            await ws.send_str(_encode_error_message(session_id, code, message))
    except Exception:
        pass
    try:
        if not ws.closed:
            await ws.close(code=1008, message=message.encode("utf-8")[:120])
    except Exception:
        pass


def _encode_error_message(session_id: str, code: str, message: str) -> str:
    return json.dumps(
        {
            "type": "error",
            "v": RELAY_PROTOCOL_VERSION,
            "s": session_id,
            "code": code,
            "message": message,
        },
        separators=(",", ":"),
    )


def _is_valid_session_id(session_id: str) -> bool:
    return bool(session_id) and all(character in _SESSION_ID_CHARS for character in session_id)


def _read_web_asset(name: str) -> str:
    return resources.files("impress_remote_relay.web").joinpath(name).read_text(encoding="utf-8")
