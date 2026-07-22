# SPDX-FileCopyrightText: 2026 Bora Yarkın
# SPDX-License-Identifier: GPL-3.0-only

from __future__ import annotations

import asyncio
import logging
import json
import time
from dataclasses import dataclass, field
from typing import Any

from aiohttp import WSMsgType, web

from impress_remote_relay.assets import localization_manifest, read_web_asset, web_asset_manifest
from impress_remote_relay.localization import translate
from impress_remote_relay.session import RelaySession

RELAY_PROTOCOL_VERSION = 1
_PLUGIN_FRAME_KINDS = {"state", "asset", "error"}
_PHONE_FRAME_KINDS = {"command"}
_REPLAYABLE_PLUGIN_FRAME_KINDS = {"state", "asset", "error"}
_SESSION_ID_CHARS = frozenset(
    "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-_"
)
LOGGER = logging.getLogger("impress_remote_relay")


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
    max_sessions: int = 512
    max_messages_per_window: int = 120
    message_window_seconds: float = 10.0
    send_timeout_seconds: float = 5.0
    sessions: dict[str, RelaySession] = field(default_factory=dict)
    metrics: dict[str, int] = field(
        default_factory=lambda: {
            "sessionsCreated": 0,
            "sessionsExpired": 0,
            "websocketAccepts": 0,
            "websocketCloses": 0,
            "framesReceived": 0,
            "framesForwarded": 0,
            "protocolRejects": 0,
            "authRejects": 0,
            "rateLimitRejects": 0,
            "sendFailures": 0,
            "sessionStatusRequests": 0,
        }
    )

    def get(self, session_id: str) -> RelaySession | None:
        session = self.sessions.get(session_id)
        if session is None:
            self.cleanup()
            if len(self.sessions) >= self.max_sessions:
                return None
            session = RelaySession(session_id=session_id)
            self.sessions[session_id] = session
            self.metrics["sessionsCreated"] += 1
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
            self.metrics["sessionsExpired"] += 1

    def count(self, name: str, amount: int = 1) -> None:
        self.metrics[name] = self.metrics.get(name, 0) + amount


def _log_event(level: int, event: str, **fields: object) -> None:
    payload = {"event": event, **fields}
    LOGGER.log(level, json.dumps(payload, separators=(",", ":"), sort_keys=True))


RELAY_STATE_KEY = web.AppKey("relay_state", RelayState)


def get_relay_state(app) -> RelayState:
    if RELAY_STATE_KEY in app:
        return app[RELAY_STATE_KEY]
    return app["relay_state"]


def create_app(state: RelayState | None = None) -> web.Application:
    app = web.Application()
    app[RELAY_STATE_KEY] = state or RelayState()
    app.router.add_get("/health", health)
    app.router.add_get("/api/session", session_status)
    app.router.add_get("/asset-manifest.json", asset_manifest)
    app.router.add_get("/", index)
    app.router.add_get("/index.html", index)
    app.router.add_get("/app.js", app_js)
    app.router.add_get("/app.css", app_css)
    app.router.add_get("/localizations/{name}", localization_json)
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
                "maxSessions": state.max_sessions,
                "maxMessagesPerWindow": state.max_messages_per_window,
                "messageWindowSeconds": state.message_window_seconds,
                "sendTimeoutSeconds": state.send_timeout_seconds,
            },
            "metrics": dict(state.metrics),
            "active": [session.snapshot() for session in state.sessions.values()],
        }
    )


async def session_status(request: web.Request) -> web.Response:
    state = get_relay_state(request.app)
    state.cleanup()
    state.count("sessionStatusRequests")
    session_id = request.query.get("session", "")
    admission_token = request.query.get("a", "")
    if not session_id:
        raise web.HTTPBadRequest(text=translate("relay.error.sessionRequired"))
    if len(session_id) > state.max_session_id_length or not _is_valid_session_id(session_id):
        raise web.HTTPBadRequest(text=translate("relay.error.sessionFormat"))
    session = state.sessions.get(session_id)
    if session is None:
        raise web.HTTPNotFound(text=translate("relay.error.sessionNotFound"))
    if not session.authorize(admission_token):
        state.count("authRejects")
        raise web.HTTPForbidden(text=translate("relay.error.admissionTokenInvalid"))
    session.touch()
    return web.json_response({"ok": True, "session": session.snapshot()})


async def asset_manifest(_request: web.Request) -> web.Response:
    return web.json_response(web_asset_manifest())


async def index(_request: web.Request) -> web.Response:
    return web.Response(
        text=read_web_asset("index.html"),
        content_type="text/html",
    )


async def app_js(_request: web.Request) -> web.Response:
    return web.Response(
        text=read_web_asset("app.js"),
        content_type="application/javascript",
    )


async def app_css(_request: web.Request) -> web.Response:
    return web.Response(
        text=read_web_asset("app.css"),
        content_type="text/css",
    )


async def localization_json(request: web.Request) -> web.Response:
    name = request.match_info.get("name", "")
    if name == "manifest.json":
        return web.json_response(localization_manifest())
    if "/" in name or not name.endswith(".json"):
        raise web.HTTPNotFound(text=translate("relay.error.localizationNotFound"))
    try:
        return web.Response(
            text=read_web_asset(f"localizations/{name}"),
            content_type="application/json",
        )
    except FileNotFoundError:
        raise web.HTTPNotFound(text=translate("relay.error.localizationNotFound")) from None


async def websocket_handler(request: web.Request) -> web.WebSocketResponse:
    role = request.query.get("role", "")
    session_id = request.query.get("session", "")
    admission_token = request.query.get("a", "")
    if role not in {"plugin", "phone"} or not session_id:
        raise web.HTTPBadRequest(text=translate("relay.error.roleAndSessionRequired"))
    state = get_relay_state(request.app)
    if len(session_id) > state.max_session_id_length:
        raise web.HTTPBadRequest(text=translate("relay.error.sessionTooLong"))
    if not _is_valid_session_id(session_id):
        raise web.HTTPBadRequest(text=translate("relay.error.sessionFormat"))
    session = state.get(session_id)
    if session is None:
        state.count("rateLimitRejects")
        raise web.HTTPServiceUnavailable(text=translate("relay.error.sessionCapacity"))
    if not session.authorize(admission_token):
        state.count("authRejects")
        _log_event(
            logging.WARNING,
            "relay.auth_reject",
            role=role,
            session=session_id,
        )
        raise web.HTTPForbidden(text=translate("relay.error.admissionTokenInvalid"))
    if role == "phone" and session.phone_count() >= state.max_phones_per_session:
        raise web.HTTPTooManyRequests(text=translate("relay.error.tooManyPhones"))
    ws = web.WebSocketResponse(heartbeat=30, max_msg_size=state.max_message_bytes)
    await ws.prepare(request)
    state.count("websocketAccepts")
    _log_event(logging.INFO, "relay.ws_accept", role=role, session=session_id)
    if role == "plugin":
        if session.plugin is not None:
            await session.plugin.close(
                code=4000,
                message=translate("relay.error.pluginReplaced").encode("utf-8")[:120],
            )
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
                if not session.allow_message(
                    ws,
                    max_messages=state.max_messages_per_window,
                    window_seconds=state.message_window_seconds,
                ):
                    state.count("rateLimitRejects")
                    await _reject_protocol(
                        ws,
                        session_id,
                        "rate-limit",
                        "relay.error.rateLimit",
                    )
                    break
                accepted = await relay_message(
                    state,
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
                    "relay.error.binaryUnsupported",
                )
                break
            elif message.type == WSMsgType.ERROR:
                break
    finally:
        if role == "plugin" and session.plugin is ws:
            session.plugin = None
            session.clear_cached_plugin_messages()
            session.last_plugin_disconnect_at = time.time()
        if role == "phone":
            session.phones.discard(ws)
        session.forget_connection(ws)
        state.count("websocketCloses")
        _log_event(logging.INFO, "relay.ws_close", role=role, session=session_id)
        state.cleanup()
    return ws


async def relay_message(
    state: RelayState,
    session: RelaySession,
    role: str,
    ws: web.WebSocketResponse,
    raw_message: str,
    max_cached_plugin_frames: int,
) -> bool:
    state.count("framesReceived")
    try:
        envelope = _validate_protocol_message(
            raw_message,
            role,
            session.session_id,
            session.latest_plugin_hello,
        )
    except _RelayProtocolViolation as exc:
        state.count("protocolRejects")
        await _reject_protocol(ws, session.session_id, exc.code, exc.message)
        _log_event(
            logging.WARNING,
            "relay.protocol_reject",
            code=exc.code,
            role=role,
            session=session.session_id,
        )
        return False

    _record_plugin_metadata(session, role, envelope, raw_message, max_cached_plugin_frames)
    targets = []
    if role == "plugin":
        targets.extend(phone for phone in session.phones if not phone.closed)
    elif session.plugin is not None and not session.plugin.closed:
        targets.append(session.plugin)
    results = await asyncio.gather(
        *(
            send_text_message(target, raw_message, timeout_seconds=state.send_timeout_seconds)
            for target in targets
        ),
        return_exceptions=True,
    )
    successes = 0
    for target, result in zip(targets, results, strict=True):
        if isinstance(result, Exception) or result is False:
            state.count("sendFailures")
            try:
                await target.close(
                    code=1011,
                    message=translate("relay.error.sendFailure").encode("utf-8")[:120],
                )
            except Exception:
                pass
            continue
        successes += 1
    state.count("framesForwarded", successes)
    return True


async def send_text_message(target: Any, raw_message: str, *, timeout_seconds: float) -> bool:
    await asyncio.wait_for(target.send_str(raw_message), timeout=max(timeout_seconds, 0.1))
    return True


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
    if (
        envelope.message_type != "frame"
        or envelope.frame_kind not in _REPLAYABLE_PLUGIN_FRAME_KINDS
    ):
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
        raise _RelayProtocolViolation("invalid-json", "relay.error.invalidJson") from exc
    if not isinstance(payload, dict):
        raise _RelayProtocolViolation("invalid-json", "relay.error.jsonObject")

    message_type = payload.get("type")
    if message_type not in {"hello", "frame", "error"}:
        raise _RelayProtocolViolation(
            "invalid-type",
            "relay.error.invalidEnvelopeType",
        )

    version = payload.get("v")
    if not isinstance(version, int) or version != RELAY_PROTOCOL_VERSION:
        raise _RelayProtocolViolation(
            "unsupported-version",
            "relay.error.unsupportedVersion",
        )

    bound_session = payload.get("s")
    if not isinstance(bound_session, str) or bound_session != session_id:
        raise _RelayProtocolViolation(
            "session-mismatch",
            "relay.error.messageSessionMismatch",
        )

    if message_type == "hello":
        hello_role = _required_string(payload, "role", "relay.error.helloMissingRole")
        if hello_role != role:
            raise _RelayProtocolViolation(
                "invalid-role",
                "relay.error.helloRoleMismatch",
            )
        if role not in {"plugin", "phone"}:
            raise _RelayProtocolViolation(
                "invalid-role",
                "relay.error.helloPluginOnly",
            )
        key_id = _required_string(payload, "k", "relay.error.helloMissingKey")
        _required_string(payload, "nonce", "relay.error.helloMissingNonce")
        _required_string(payload, "pub", "relay.error.helloMissingPublicKey")
        if role == "phone":
            active_key_id = _hello_key_id(latest_plugin_hello)
            if not active_key_id:
                raise _RelayProtocolViolation(
                    "missing-hello",
                    "relay.error.pluginNotReady",
                )
            if key_id != active_key_id:
                raise _RelayProtocolViolation(
                    "invalid-key",
                    "relay.error.pluginKeyMismatch",
                )
        return _RelayEnvelope(message_type="hello", key_id=key_id)

    if message_type == "error":
        if role != "plugin":
            raise _RelayProtocolViolation(
                "invalid-role",
                "relay.error.plainErrorPluginOnly",
            )
        _required_string(payload, "code", "relay.error.errorMissingCode")
        _required_string(payload, "message", "relay.error.errorMissingMessage")
        return _RelayEnvelope(message_type="error")

    key_id = _required_string(payload, "k", "relay.error.frameMissingKey")
    frame_kind = _required_string(payload, "kind", "relay.error.frameMissingKind")
    _required_string(payload, "n", "relay.error.frameMissingNonce")
    _required_string(payload, "ct", "relay.error.frameMissingCiphertext")

    allowed_kinds = _PLUGIN_FRAME_KINDS if role == "plugin" else _PHONE_FRAME_KINDS
    if frame_kind not in allowed_kinds:
        raise _RelayProtocolViolation(
            "invalid-kind",
            "relay.error.frameKindForRole",
        )

    if role == "plugin":
        active_key_id = _hello_key_id(latest_plugin_hello)
        if not active_key_id:
            raise _RelayProtocolViolation(
                "missing-hello",
                "relay.error.pluginHelloRequired",
            )
        if key_id != active_key_id:
            raise _RelayProtocolViolation(
                "invalid-key",
                "relay.error.pluginKeyMismatch",
            )
    elif not latest_plugin_hello:
        raise _RelayProtocolViolation(
            "missing-hello",
            "relay.error.pluginNotReady",
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
