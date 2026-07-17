# SPDX-FileCopyrightText: 2026 Bora Yarkın
# SPDX-License-Identifier: GPL-3.0-only

from __future__ import annotations

import base64
import hashlib
import json
import os
import socket
import ssl
import threading
import time
from collections.abc import Callable
from urllib.error import URLError
from urllib.parse import urlparse
from urllib.request import Request, urlopen

from impress_remote.config import relay_session_status_url, relay_websocket_url
from impress_remote.protocol import (
    RelayProtocolFailure,
    SecureRelayCodec,
    decode_command_payload,
    decode_error_message,
    decode_hello_message,
    encode_hello_message,
    encode_state_message,
)

StateProvider = Callable[[], dict[str, object]]
RelayAssetProvider = Callable[[str, str], dict[str, object] | None]
CommandHandler = Callable[[str, int | None], None]
ActivityCallback = Callable[[str], None]

GUID = "258EAFA5-E914-47DA-95CA-C5AB0DC85B11"


def _read_exact(sock: socket.socket, size: int) -> bytes:
    chunks = []
    remaining = size
    while remaining > 0:
        chunk = sock.recv(remaining)
        if not chunk:
            raise ConnectionError("websocket connection closed")
        chunks.append(chunk)
        remaining -= len(chunk)
    return b"".join(chunks)


class RelayWebSocket:
    def __init__(self, url: str):
        self.url = url
        self._socket: socket.socket | None = None

    def connect(self) -> None:
        parsed = urlparse(self.url)
        if parsed.scheme not in {"ws", "wss"}:
            raise ValueError(f"Unsupported websocket scheme: {parsed.scheme}")
        if not parsed.hostname:
            raise ValueError("Relay websocket URL is missing a host")

        port = parsed.port or (443 if parsed.scheme == "wss" else 80)
        raw_socket = socket.create_connection((parsed.hostname, port), timeout=5)
        if parsed.scheme == "wss":
            context = ssl.create_default_context()
            raw_socket = context.wrap_socket(raw_socket, server_hostname=parsed.hostname)

        path = parsed.path or "/"
        if parsed.query:
            path = f"{path}?{parsed.query}"

        websocket_key = base64.b64encode(os.urandom(16)).decode("ascii")
        host = parsed.hostname
        if parsed.port and parsed.port not in {80, 443}:
            host = f"{host}:{parsed.port}"
        request = (
            f"GET {path} HTTP/1.1\r\n"
            f"Host: {host}\r\n"
            "Upgrade: websocket\r\n"
            "Connection: Upgrade\r\n"
            f"Sec-WebSocket-Key: {websocket_key}\r\n"
            "Sec-WebSocket-Version: 13\r\n"
            "\r\n"
        )
        raw_socket.sendall(request.encode("ascii"))
        response = self._read_http_response(raw_socket)
        expected_accept = base64.b64encode(
            hashlib.sha1((websocket_key + GUID).encode("ascii")).digest()
        ).decode("ascii")
        if "101" not in response.splitlines()[0]:
            raise ConnectionError(f"Unexpected websocket handshake response: {response!r}")
        if f"sec-websocket-accept: {expected_accept}".lower() not in response.lower():
            raise ConnectionError("Relay websocket handshake could not be verified")

        self._socket = raw_socket

    def close(self) -> None:
        if self._socket is None:
            return
        try:
            self._send_frame(0x8, b"")
        except OSError:
            pass
        try:
            self._socket.close()
        finally:
            self._socket = None

    def send_text(self, text: str) -> None:
        self._send_frame(0x1, text.encode("utf-8"))

    def receive_text(self, timeout: float) -> str | None:
        sock = self._require_socket()
        sock.settimeout(timeout)
        while True:
            try:
                header = _read_exact(sock, 2)
            except TimeoutError:
                return None

            opcode = header[0] & 0x0F
            masked = (header[1] & 0x80) != 0
            length = header[1] & 0x7F
            if length == 126:
                length = int.from_bytes(_read_exact(sock, 2), "big")
            elif length == 127:
                length = int.from_bytes(_read_exact(sock, 8), "big")

            mask = _read_exact(sock, 4) if masked else b""
            payload = _read_exact(sock, length) if length else b""
            if masked:
                payload = bytes(byte ^ mask[index % 4] for index, byte in enumerate(payload))

            if opcode == 0x1:
                return payload.decode("utf-8")
            if opcode == 0x8:
                raise ConnectionError("Relay websocket closed the connection")
            if opcode == 0x9:
                self._send_frame(0xA, payload)
                continue
            if opcode == 0xA:
                continue

    def _read_http_response(self, sock: socket.socket) -> str:
        response = bytearray()
        sock.settimeout(5)
        while b"\r\n\r\n" not in response:
            chunk = sock.recv(4096)
            if not chunk:
                raise ConnectionError("Unexpected EOF during websocket handshake")
            response.extend(chunk)
        return response.decode("iso-8859-1")

    def _require_socket(self) -> socket.socket:
        if self._socket is None:
            raise ConnectionError("Relay websocket is not connected")
        return self._socket

    def _send_frame(self, opcode: int, payload: bytes) -> None:
        sock = self._require_socket()
        first = 0x80 | opcode
        length = len(payload)
        mask = os.urandom(4)
        if length < 126:
            header = bytes([first, 0x80 | length])
        elif length < (1 << 16):
            header = bytes([first, 0x80 | 126]) + length.to_bytes(2, "big")
        else:
            header = bytes([first, 0x80 | 127]) + length.to_bytes(8, "big")
        masked = bytes(byte ^ mask[index % 4] for index, byte in enumerate(payload))
        sock.sendall(header + mask + masked)


class RelayClient:
    def __init__(
        self,
        relay_url: str,
        session_id: str,
        pairing_secret: str,
        admission_token: str,
        state_provider: StateProvider,
        asset_provider: RelayAssetProvider | None,
        command_handler: CommandHandler,
        activity_callback: ActivityCallback | None = None,
    ):
        self.relay_url = relay_url
        self.session_id = session_id
        self.pairing_secret = pairing_secret
        self.admission_token = admission_token
        self.state_provider = state_provider
        self.asset_provider = asset_provider
        self.command_handler = command_handler
        self.activity_callback = activity_callback
        self._session_status_url = relay_session_status_url(
            relay_url,
            session_id,
            admission_token,
        )
        self._thread: threading.Thread | None = None
        self._stop_event = threading.Event()
        self._lock = threading.Lock()
        self._websocket: RelayWebSocket | None = None
        self._connected = False
        self._last_error = ""
        self._codec = SecureRelayCodec(
            role="plugin",
            session_id=session_id,
            pairing_secret=pairing_secret,
        )

    def start(self) -> None:
        if self._thread is not None and self._thread.is_alive():
            return
        self._stop_event.clear()
        self._thread = threading.Thread(target=self._run, daemon=True, name="relay-client")
        self._thread.start()

    def stop(self) -> None:
        self._stop_event.set()
        with self._lock:
            websocket = self._websocket
        if websocket is not None:
            websocket.close()
        if self._thread is not None:
            self._thread.join(timeout=2)
        self._set_status(False, "")

    def is_running(self) -> bool:
        thread = self._thread
        return thread is not None and thread.is_alive() and not self._stop_event.is_set()

    def status(self) -> dict[str, str | bool]:
        with self._lock:
            if self._connected:
                state = "connected"
            elif self._last_error:
                state = "error"
            else:
                state = "connecting" if self._thread and self._thread.is_alive() else "disabled"
            return {
                "state": state,
                "lastError": self._last_error,
            }

    def _run(self) -> None:
        last_state_message = ""
        last_asset_revisions = {"current": "", "next": ""}
        while not self._stop_event.is_set():
            websocket = RelayWebSocket(
                relay_websocket_url(
                    self.relay_url,
                    self.session_id,
                    role="plugin",
                    admission_token=self.admission_token,
                )
            )
            try:
                websocket.connect()
                with self._lock:
                    self._websocket = websocket
                websocket.send_text(encode_hello_message(self._codec.rotate_send_key()))
                self._set_status(True, "")
                last_state_message = ""
                last_asset_revisions = {"current": "", "next": ""}
                last_state_sent_at = 0.0
                last_presence_probe_at = 0.0
                while not self._stop_event.is_set():
                    now = time.monotonic()
                    state = self.state_provider()
                    resend_secure_snapshot = False
                    state_message = encode_state_message(state)
                    if self._codec.should_rotate_send_key():
                        websocket.send_text(encode_hello_message(self._codec.rotate_send_key()))
                        resend_secure_snapshot = True
                        last_state_message = ""
                        last_asset_revisions = {"current": "", "next": ""}
                    if (
                        resend_secure_snapshot
                        or state_message != last_state_message
                        or now - last_state_sent_at >= 1.0
                    ):
                        websocket.send_text(self._codec.encode_state_frame(state))
                        last_state_message = state_message
                        last_state_sent_at = now
                    self._send_asset_frames(websocket, state, last_asset_revisions)
                    if now - last_presence_probe_at >= 1.0:
                        last_presence_probe_at = now
                        self._probe_phone_presence()
                    incoming = websocket.receive_text(timeout=0.5)
                    if incoming:
                        self._handle_message(incoming)
            except Exception as exc:
                self._set_status(False, str(exc))
                if self._stop_event.wait(2):
                    break
            finally:
                with self._lock:
                    self._websocket = None
                websocket.close()
                self._set_status(False, self._last_error)

    def _send_asset_frames(
        self,
        websocket: RelayWebSocket,
        state: dict[str, object],
        last_asset_revisions: dict[str, str],
    ) -> None:
        if self.asset_provider is None:
            return
        for slot, revision_key in (
            ("current", "currentSlideImageRevision"),
            ("next", "nextSlideImageRevision"),
        ):
            revision_value = state.get(revision_key, "")
            revision = revision_value if isinstance(revision_value, str) else ""
            if not revision:
                last_asset_revisions[slot] = ""
                continue
            if last_asset_revisions.get(slot) == revision:
                continue
            asset_payload = self.asset_provider(slot, revision)
            if asset_payload is None:
                continue
            websocket.send_text(self._codec.encode_asset_frame(asset_payload))
            last_asset_revisions[slot] = revision

    def _handle_message(self, raw: str) -> None:
        if decode_hello_message(raw) is not None:
            return
        error_message = decode_error_message(raw)
        if error_message is not None:
            self._set_status(self._connected, error_message.message)
            return
        try:
            frame = self._codec.decode_frame(raw)
        except RelayProtocolFailure as exc:
            self._set_status(self._connected, exc.message)
            return
        if frame is None or frame.kind != "command":
            return
        command = decode_command_payload(frame.payload)
        if command is None:
            return
        if self.activity_callback is not None:
            self.activity_callback("relay")
        self.command_handler(command.command, command.index)

    def _probe_phone_presence(self) -> None:
        if self.activity_callback is None:
            return
        try:
            request = Request(
                self._session_status_url,
                headers={"Accept": "application/json"},
            )
            with urlopen(request, timeout=2) as response:
                payload = json.loads(response.read().decode("utf-8"))
        except (OSError, TimeoutError, ValueError, URLError):
            return
        session = payload.get("session")
        if not isinstance(session, dict):
            return
        phones = session.get("phones")
        if isinstance(phones, int) and phones > 0:
            self.activity_callback("relay")

    def _set_status(self, connected: bool, last_error: str) -> None:
        with self._lock:
            self._connected = connected
            self._last_error = last_error
