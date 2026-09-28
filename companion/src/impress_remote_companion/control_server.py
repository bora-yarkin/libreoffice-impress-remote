# SPDX-FileCopyrightText: 2026 Bora Yarkın
# SPDX-License-Identifier: GPL-3.0-only

"""Loopback-only HTTP server for the desktop setup page."""

from __future__ import annotations

from hmac import compare_digest
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, HTTPServer
from importlib.resources import files
import json
import secrets

_LOOPBACK_HOST = "127.0.0.1"
_SECURITY_HEADERS = (
    ("Cache-Control", "no-store"),
    (
        "Content-Security-Policy",
        "default-src 'self'; base-uri 'none'; connect-src 'self'; "
        "form-action 'none'; frame-ancestors 'none'; img-src 'self'; "
        "script-src 'self'; style-src 'self'",
    ),
    ("Permissions-Policy", "camera=(), geolocation=(), microphone=()"),
    ("Referrer-Policy", "same-origin"),
    ("X-Content-Type-Options", "nosniff"),
    ("X-Frame-Options", "DENY"),
)


class LocalControlServer(HTTPServer):
    """Serve only the local setup page and its shutdown action."""

    allow_reuse_address = False
    request_queue_size = 8

    def __init__(self) -> None:
        self.shutdown_token = secrets.token_urlsafe(32)
        self.shutdown_requested = False
        super().__init__((_LOOPBACK_HOST, 0), ControlRequestHandler)
        self.timeout = 0.5
        self.origin = f"http://{_LOOPBACK_HOST}:{self.server_port}"

    def get_request(self):
        request, client_address = super().get_request()
        request.settimeout(5)
        return request, client_address


class ControlRequestHandler(BaseHTTPRequestHandler):
    """Handle the minimal local setup page API."""

    server: LocalControlServer
    server_version = "ImpressRemoteCompanion"
    sys_version = ""

    def log_message(self, format: str, *args: object) -> None:
        # Request paths and headers can contain local session material.
        return

    def end_headers(self) -> None:
        for name, value in _SECURITY_HEADERS:
            self.send_header(name, value)
        super().end_headers()

    def do_GET(self) -> None:
        if not self._request_is_for_local_origin():
            return
        if self.path == "/":
            self._send_resource("index.html", "text/html; charset=utf-8")
        elif self.path == "/app.css":
            self._send_resource("app.css", "text/css; charset=utf-8")
        elif self.path == "/app.js":
            self._send_resource("app.js", "text/javascript; charset=utf-8")
        elif self.path == "/localizations/en.json":
            self._send_resource(
                "localizations/en.json",
                "application/json; charset=utf-8",
            )
        elif self.path == "/localizations/tr.json":
            self._send_resource(
                "localizations/tr.json",
                "application/json; charset=utf-8",
            )
        elif self.path == "/api/session":
            self._send_json({"shutdownToken": self.server.shutdown_token})
        else:
            self.send_error(HTTPStatus.NOT_FOUND)

    def do_POST(self) -> None:
        if not self._request_is_for_local_origin():
            return
        if self.path != "/api/shutdown":
            self.send_error(HTTPStatus.NOT_FOUND)
            return
        if not self._has_empty_request_body():
            self.send_error(HTTPStatus.BAD_REQUEST)
            return
        if self.headers.get("Origin") != self.server.origin:
            self.send_error(HTTPStatus.FORBIDDEN)
            return

        supplied_token = self.headers.get("X-Companion-Token", "")
        if not compare_digest(supplied_token, self.server.shutdown_token):
            self.send_error(HTTPStatus.FORBIDDEN)
            return

        self._send_json({"ok": True}, HTTPStatus.ACCEPTED)
        self.server.shutdown_requested = True

    def _request_is_for_local_origin(self) -> bool:
        expected_host = self.server.origin.removeprefix("http://")
        if self.headers.get("Host") == expected_host:
            return True
        self.send_error(HTTPStatus.MISDIRECTED_REQUEST)
        return False

    def _has_empty_request_body(self) -> bool:
        transfer_encoding = self.headers.get("Transfer-Encoding")
        content_length = self.headers.get("Content-Length", "0")
        return (
            transfer_encoding is None
            and content_length.isdecimal()
            and not content_length.strip("0")
        )

    def _send_resource(self, name: str, content_type: str) -> None:
        try:
            content = files("impress_remote_companion").joinpath("web", name).read_bytes()
        except OSError:
            self.send_error(HTTPStatus.INTERNAL_SERVER_ERROR)
            return
        self._send_bytes(content, content_type)

    def _send_json(
        self,
        value: dict[str, object],
        status: HTTPStatus = HTTPStatus.OK,
    ) -> None:
        content = json.dumps(value, separators=(",", ":")).encode("utf-8")
        self._send_bytes(content, "application/json; charset=utf-8", status)

    def _send_bytes(
        self,
        content: bytes,
        content_type: str,
        status: HTTPStatus = HTTPStatus.OK,
    ) -> None:
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(content)))
        self.end_headers()
        self.wfile.write(content)


def create_local_control_server() -> LocalControlServer:
    """Bind the control server to an OS-assigned port on IPv4 loopback only."""
    return LocalControlServer()
