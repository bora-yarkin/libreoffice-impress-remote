# SPDX-FileCopyrightText: 2026 Bora Yarkın
# SPDX-License-Identifier: GPL-3.0-only

from __future__ import annotations

from collections import deque
from dataclasses import dataclass, field
import json
from typing import Any

from impress_remote.crypto import (
    aes_gcm_decrypt,
    aes_gcm_encrypt,
    base64url_decode,
    base64url_encode,
    hkdf_sha256,
    random_bytes,
    random_token,
)
from impress_remote.localization import translate

RELAY_PROTOCOL_VERSION = 1
RELAY_CIPHER_SUITE = "HKDF-SHA256+AES-256-GCM+PSK"
RELAY_KEY_ROTATION_MESSAGES = 300
RELAY_KIND_STATE = "state"
RELAY_KIND_COMMAND = "command"
RELAY_KIND_ERROR = "error"
RELAY_KIND_ASSET = "asset"
_RELAY_PROTOCOL_LABEL = b"impress-remote-relay/v1"


@dataclass(frozen=True)
class RelayCommand:
    command: str
    index: int | None = None


@dataclass(frozen=True)
class RelayHello:
    version: int
    session_id: str
    key_id: str
    plugin_nonce: str
    cipher_suite: str = RELAY_CIPHER_SUITE
    key_rotation_messages: int = RELAY_KEY_ROTATION_MESSAGES
    features: tuple[str, ...] = (
        RELAY_KIND_STATE,
        RELAY_KIND_COMMAND,
        RELAY_KIND_ERROR,
        RELAY_KIND_ASSET,
    )


@dataclass(frozen=True)
class RelayError:
    code: str
    message: str
    session_id: str = ""
    version: int = RELAY_PROTOCOL_VERSION


@dataclass(frozen=True)
class RelayDecryptedFrame:
    kind: str
    payload: dict[str, object]
    key_id: str


class RelayProtocolFailure(ValueError):
    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code
        self.message = message


@dataclass
class _ReplayCache:
    max_entries: int
    _values: set[str] = field(default_factory=set)
    _order: deque[str] = field(default_factory=deque)

    def seen(self, nonce_text: str) -> bool:
        return nonce_text in self._values

    def remember(self, nonce_text: str) -> None:
        if nonce_text in self._values:
            return
        self._values.add(nonce_text)
        self._order.append(nonce_text)
        while len(self._order) > self.max_entries:
            expired = self._order.popleft()
            self._values.discard(expired)


@dataclass
class _RelayKeySet:
    key_id: str
    plugin_nonce: str
    state_key: bytes
    command_key: bytes
    plugin_replay: _ReplayCache
    phone_replay: _ReplayCache


class SecureRelayCodec:
    def __init__(
        self,
        *,
        role: str,
        session_id: str,
        pairing_secret: str,
        key_rotation_messages: int = RELAY_KEY_ROTATION_MESSAGES,
        replay_cache_size: int = 1024,
    ):
        if role not in {"plugin", "phone"}:
            raise ValueError(translate("protocol.error.unsupportedRole", role=role))
        self.role = role
        self.session_id = session_id
        self._secret = base64url_decode(pairing_secret)
        self._key_rotation_messages = max(int(key_rotation_messages), 1)
        self._replay_cache_size = max(int(replay_cache_size), 32)
        self._keys: dict[str, _RelayKeySet] = {}
        self._key_order: deque[str] = deque()
        self._active_key_id = ""
        self._sent_with_active_key = 0

    def ready(self) -> bool:
        return bool(self._active_key_id)

    def should_rotate_send_key(self) -> bool:
        return self.role == "plugin" and self._sent_with_active_key >= self._key_rotation_messages

    def rotate_send_key(self) -> RelayHello:
        if self.role != "plugin":
            raise ValueError(translate("protocol.error.rotatePluginOnly"))
        key_id = random_token(9)
        plugin_nonce = base64url_encode(random_bytes(16))
        key_set = _derive_key_set(
            self._secret,
            self.session_id,
            key_id,
            plugin_nonce,
            self._replay_cache_size,
        )
        self._store_key_set(key_set)
        self._active_key_id = key_id
        self._sent_with_active_key = 0
        return RelayHello(
            version=RELAY_PROTOCOL_VERSION,
            session_id=self.session_id,
            key_id=key_id,
            plugin_nonce=plugin_nonce,
            key_rotation_messages=self._key_rotation_messages,
        )

    def apply_hello(self, hello: RelayHello) -> None:
        if hello.version != RELAY_PROTOCOL_VERSION:
            raise RelayProtocolFailure(
                "unsupported-version",
                translate("protocol.error.unsupportedVersion"),
            )
        if hello.session_id != self.session_id:
            raise RelayProtocolFailure(
                "session-mismatch",
                translate("protocol.error.helloSessionMismatch"),
            )
        key_set = _derive_key_set(
            self._secret,
            hello.session_id,
            hello.key_id,
            hello.plugin_nonce,
            self._replay_cache_size,
        )
        self._store_key_set(key_set)
        self._active_key_id = hello.key_id
        self._sent_with_active_key = 0

    def encode_state_frame(self, state: dict[str, object]) -> str:
        return self._encode_frame(RELAY_KIND_STATE, state)

    def encode_command_frame(self, command: str, index: int | None = None) -> str:
        payload: dict[str, Any] = {"command": command}
        if index is not None:
            payload["index"] = index
        return self._encode_frame(RELAY_KIND_COMMAND, payload)

    def encode_error_frame(self, code: str, message: str) -> str:
        return self._encode_frame(RELAY_KIND_ERROR, {"code": code, "message": message})

    def encode_asset_frame(self, payload: dict[str, object]) -> str:
        return self._encode_frame(RELAY_KIND_ASSET, payload)

    def decode_frame(self, raw: str) -> RelayDecryptedFrame | None:
        payload = _parse_json(raw)
        if payload.get("type") != "frame":
            return None
        version = payload.get("v")
        session_id = payload.get("s")
        key_id = payload.get("k")
        kind = payload.get("kind")
        nonce_text = payload.get("n")
        ciphertext_text = payload.get("ct")
        if version != RELAY_PROTOCOL_VERSION:
            raise RelayProtocolFailure(
                "unsupported-version",
                translate("protocol.error.unsupportedVersion"),
            )
        if session_id != self.session_id:
            raise RelayProtocolFailure(
                "session-mismatch",
                translate("protocol.error.frameSessionMismatch"),
            )
        if not isinstance(key_id, str) or not key_id:
            raise RelayProtocolFailure(
                "invalid-key",
                translate("protocol.error.frameMissingKey"),
            )
        if not isinstance(kind, str) or kind not in {
            RELAY_KIND_STATE,
            RELAY_KIND_COMMAND,
            RELAY_KIND_ERROR,
            RELAY_KIND_ASSET,
        }:
            raise RelayProtocolFailure(
                "invalid-kind",
                translate("protocol.error.frameUnknownKind"),
            )
        if not isinstance(nonce_text, str) or not nonce_text:
            raise RelayProtocolFailure(
                "invalid-nonce",
                translate("protocol.error.frameMissingNonce"),
            )
        if not isinstance(ciphertext_text, str) or not ciphertext_text:
            raise RelayProtocolFailure(
                "invalid-ciphertext",
                translate("protocol.error.frameEmptyCiphertext"),
            )
        key_set = self._keys.get(key_id)
        if key_set is None:
            raise RelayProtocolFailure(
                "unknown-key",
                translate("protocol.error.frameUnknownKey"),
            )
        replay_cache = key_set.phone_replay if self.role == "plugin" else key_set.plugin_replay
        if replay_cache.seen(nonce_text):
            raise RelayProtocolFailure(
                "replay-detected",
                translate("protocol.error.frameReplay"),
            )
        blob = base64url_decode(ciphertext_text)
        if len(blob) < 16:
            raise RelayProtocolFailure(
                "invalid-ciphertext",
                translate("protocol.error.frameTruncated"),
            )
        ciphertext = blob[:-16]
        tag = blob[-16:]
        nonce = base64url_decode(nonce_text)
        aad = _frame_aad(self.session_id, key_id, kind, nonce_text)
        key = _receive_key_for_kind(self.role, key_set, kind)
        plaintext = aes_gcm_decrypt(key, nonce, ciphertext, tag, aad)
        replay_cache.remember(nonce_text)
        decoded = _parse_json_bytes(plaintext)
        if not isinstance(decoded, dict):
            raise RelayProtocolFailure(
                "invalid-payload",
                translate("protocol.error.framePayloadObject"),
            )
        return RelayDecryptedFrame(kind=kind, payload=decoded, key_id=key_id)

    def _encode_frame(self, kind: str, payload: dict[str, object]) -> str:
        if kind not in {RELAY_KIND_STATE, RELAY_KIND_COMMAND, RELAY_KIND_ERROR, RELAY_KIND_ASSET}:
            raise ValueError(translate("protocol.error.unsupportedFrameKind", kind=kind))
        if not self._active_key_id:
            raise RelayProtocolFailure(
                "missing-hello",
                translate("protocol.error.missingNegotiatedKey"),
            )
        key_set = self._keys[self._active_key_id]
        key = _send_key_for_kind(self.role, key_set, kind)
        nonce = random_bytes(12)
        nonce_text = base64url_encode(nonce)
        plaintext = json.dumps(payload, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
        aad = _frame_aad(self.session_id, self._active_key_id, kind, nonce_text)
        ciphertext, tag = aes_gcm_encrypt(key, nonce, plaintext, aad)
        self._sent_with_active_key += 1
        return json.dumps(
            {
                "type": "frame",
                "v": RELAY_PROTOCOL_VERSION,
                "s": self.session_id,
                "k": self._active_key_id,
                "kind": kind,
                "n": nonce_text,
                "ct": base64url_encode(ciphertext + tag),
            },
            separators=(",", ":"),
        )

    def _store_key_set(self, key_set: _RelayKeySet) -> None:
        if key_set.key_id in self._keys:
            self._keys[key_set.key_id] = key_set
            return
        self._keys[key_set.key_id] = key_set
        self._key_order.append(key_set.key_id)
        while len(self._key_order) > 3:
            expired = self._key_order.popleft()
            if expired != self._active_key_id:
                self._keys.pop(expired, None)


def encode_state_message(state: dict[str, object]) -> str:
    return json.dumps({"type": "state", "state": state}, separators=(",", ":"))


def encode_command_message(command: str, index: int | None = None) -> str:
    payload: dict[str, Any] = {"type": "command", "command": command}
    if index is not None:
        payload["index"] = index
    return json.dumps(payload, separators=(",", ":"))


def decode_command_message(raw: str) -> RelayCommand | None:
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError:
        return None
    return decode_command_payload(payload)


def decode_command_payload(payload: object) -> RelayCommand | None:
    if not isinstance(payload, dict):
        return None
    message_type = payload.get("type")
    if message_type not in {None, "command"}:
        return None
    command = payload.get("command")
    if not isinstance(command, str) or not command:
        return None
    index = payload.get("index")
    if index is not None:
        try:
            index = int(index)
        except (TypeError, ValueError):
            index = None
    return RelayCommand(command=command, index=index)


def encode_hello_message(hello: RelayHello) -> str:
    return json.dumps(
        {
            "type": "hello",
            "v": hello.version,
            "s": hello.session_id,
            "k": hello.key_id,
            "nonce": hello.plugin_nonce,
            "suite": hello.cipher_suite,
            "rotate": hello.key_rotation_messages,
            "features": list(hello.features),
        },
        separators=(",", ":"),
    )


def decode_hello_message(raw: str) -> RelayHello | None:
    payload = _parse_json(raw)
    if payload.get("type") != "hello":
        return None
    version = payload.get("v")
    session_id = payload.get("s")
    key_id = payload.get("k")
    plugin_nonce = payload.get("nonce")
    cipher_suite = payload.get("suite", RELAY_CIPHER_SUITE)
    rotation = payload.get("rotate", RELAY_KEY_ROTATION_MESSAGES)
    features = payload.get(
        "features",
        [RELAY_KIND_STATE, RELAY_KIND_COMMAND, RELAY_KIND_ERROR, RELAY_KIND_ASSET],
    )
    if (
        not isinstance(version, int)
        or version != RELAY_PROTOCOL_VERSION
        or not isinstance(session_id, str)
        or not session_id
        or not isinstance(key_id, str)
        or not key_id
        or not isinstance(plugin_nonce, str)
        or not plugin_nonce
        or not isinstance(cipher_suite, str)
        or not isinstance(rotation, int)
        or not isinstance(features, list)
    ):
        return None
    feature_names = tuple(feature for feature in features if isinstance(feature, str) and feature)
    return RelayHello(
        version=version,
        session_id=session_id,
        key_id=key_id,
        plugin_nonce=plugin_nonce,
        cipher_suite=cipher_suite,
        key_rotation_messages=max(int(rotation), 1),
        features=feature_names
        or (RELAY_KIND_STATE, RELAY_KIND_COMMAND, RELAY_KIND_ERROR, RELAY_KIND_ASSET),
    )


def encode_error_message(code: str, message: str, session_id: str = "") -> str:
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


def decode_error_message(raw: str) -> RelayError | None:
    payload = _parse_json(raw)
    if payload.get("type") != "error":
        return None
    code = payload.get("code")
    message = payload.get("message")
    session_id = payload.get("s", "")
    version = payload.get("v", RELAY_PROTOCOL_VERSION)
    if (
        not isinstance(code, str)
        or not code
        or not isinstance(message, str)
        or not isinstance(session_id, str)
        or not isinstance(version, int)
    ):
        return None
    return RelayError(code=code, message=message, session_id=session_id, version=version)


def _derive_key_set(
    secret: bytes,
    session_id: str,
    key_id: str,
    plugin_nonce_text: str,
    replay_cache_size: int,
) -> _RelayKeySet:
    plugin_nonce = base64url_decode(plugin_nonce_text)
    salt = _RELAY_PROTOCOL_LABEL + b"\0" + session_id.encode("utf-8")
    info = b"relay-keys\0" + key_id.encode("utf-8") + b"\0" + plugin_nonce
    material = hkdf_sha256(secret, salt, info, length=64)
    return _RelayKeySet(
        key_id=key_id,
        plugin_nonce=plugin_nonce_text,
        state_key=material[:32],
        command_key=material[32:64],
        plugin_replay=_ReplayCache(replay_cache_size),
        phone_replay=_ReplayCache(replay_cache_size),
    )


def _send_key_for_kind(role: str, key_set: _RelayKeySet, kind: str) -> bytes:
    if role == "plugin" and kind in {RELAY_KIND_STATE, RELAY_KIND_ERROR, RELAY_KIND_ASSET}:
        return key_set.state_key
    if role == "phone" and kind == RELAY_KIND_COMMAND:
        return key_set.command_key
    raise RelayProtocolFailure(
        "invalid-direction",
        translate("protocol.error.invalidSendDirection", role=role, kind=kind),
    )


def _receive_key_for_kind(role: str, key_set: _RelayKeySet, kind: str) -> bytes:
    if role == "plugin" and kind == RELAY_KIND_COMMAND:
        return key_set.command_key
    if role == "phone" and kind in {RELAY_KIND_STATE, RELAY_KIND_ERROR, RELAY_KIND_ASSET}:
        return key_set.state_key
    raise RelayProtocolFailure(
        "invalid-direction",
        translate("protocol.error.invalidReceiveDirection", role=role, kind=kind),
    )


def _frame_aad(session_id: str, key_id: str, kind: str, nonce_text: str) -> bytes:
    return json.dumps(
        {
            "kind": kind,
            "k": key_id,
            "n": nonce_text,
            "s": session_id,
            "v": RELAY_PROTOCOL_VERSION,
        },
        separators=(",", ":"),
    ).encode("utf-8")


def _parse_json(raw: str) -> dict[str, object]:
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise RelayProtocolFailure(
            "invalid-json",
            translate("protocol.error.messageJson"),
        ) from exc
    if not isinstance(payload, dict):
        raise RelayProtocolFailure(
            "invalid-json",
            translate("protocol.error.messageObject"),
        )
    return payload


def _parse_json_bytes(raw: bytes) -> object:
    try:
        return json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise RelayProtocolFailure(
            "invalid-payload",
            translate("protocol.error.payloadJson"),
        ) from exc
