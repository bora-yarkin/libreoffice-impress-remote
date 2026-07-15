# SPDX-FileCopyrightText: 2026 Bora Yarkın
# SPDX-License-Identifier: GPL-3.0-only

from __future__ import annotations

import json
import socket
import threading
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Dict, Optional
from urllib.parse import urlparse

from impress_remote.config import RemoteConfig
from impress_remote.controller import ImpressController
from impress_remote.crypto import random_token
from impress_remote.network import discover_direct_ipv6_urls, discover_local_urls

WEB_ROOT = Path(__file__).resolve().parents[2] / "web"


class IPv6ThreadingHTTPServer(ThreadingHTTPServer):
    address_family = socket.AF_INET6

    def server_bind(self) -> None:
        if hasattr(socket, "IPPROTO_IPV6") and hasattr(socket, "IPV6_V6ONLY"):
            self.socket.setsockopt(socket.IPPROTO_IPV6, socket.IPV6_V6ONLY, 1)
        super().server_bind()


class RemoteServer:
    def __init__(self, ctx, config: Optional[RemoteConfig] = None):
        self.ctx = ctx
        self.config = config or RemoteConfig()
        self.session_id = random_token(12)
        self.controller = ImpressController(ctx)
        self.http_servers: list[ThreadingHTTPServer] = []
        self.threads: list[threading.Thread] = []
        self.url = ""
        self.local_urls: list[str] = []
        self.direct_urls: list[str] = []

    def start(self) -> None:
        if self.http_servers:
            return
        parent = self

        class Handler(RemoteRequestHandler):
            server_ref = parent

        started_servers: list[ThreadingHTTPServer] = []
        try:
            ipv4_server = ThreadingHTTPServer((self.config.local_host, self.config.local_port), Handler)
            started_servers.append(ipv4_server)
        except OSError:
            ipv4_server = None

        if self.config.enable_ipv6_direct:
            try:
                ipv6_server = IPv6ThreadingHTTPServer(("::", self.config.local_port), Handler)
                started_servers.append(ipv6_server)
            except OSError:
                pass

        if not started_servers:
            raise RuntimeError(f"Could not start the remote server on port {self.config.local_port}")

        self.http_servers = started_servers
        self.threads = []
        for server in self.http_servers:
            thread = threading.Thread(target=server.serve_forever, daemon=True)
            thread.start()
            self.threads.append(thread)

        self.local_urls = (
            discover_local_urls(self.config.local_port, self.session_id)
            if any(server.address_family == socket.AF_INET for server in self.http_servers)
            else []
        )
        self.direct_urls = (
            discover_direct_ipv6_urls(self.config.local_port, self.session_id)
            if any(server.address_family == socket.AF_INET6 for server in self.http_servers)
            else []
        )
        if self.local_urls:
            self.url = self.local_urls[0]
        elif self.direct_urls:
            self.url = self.direct_urls[0]
        else:
            self.url = f"http://127.0.0.1:{self.config.local_port}/#s={self.session_id}"

    def stop(self) -> None:
        for server in self.http_servers:
            server.shutdown()
            server.server_close()
        for thread in self.threads:
            thread.join(timeout=1)
        self.http_servers = []
        self.threads = []
        self.local_urls = []
        self.direct_urls = []
        self.url = ""

    def connection_info(self) -> Dict[str, object]:
        return {
            "session": self.session_id,
            "localUrls": list(self.local_urls),
            "directUrls": list(self.direct_urls),
            "relayConfigured": self.config.enable_relay and bool(self.config.relay_url),
            "relayUrl": self.config.relay_url,
        }


class RemoteRequestHandler(BaseHTTPRequestHandler):
    server_ref: RemoteServer

    def log_message(self, format: str, *args) -> None:
        return

    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        if parsed.path in {"/", "/index.html"}:
            self._send_file(WEB_ROOT / "index.html", "text/html; charset=utf-8")
        elif parsed.path == "/app.css":
            self._send_file(WEB_ROOT / "app.css", "text/css; charset=utf-8")
        elif parsed.path == "/app.js":
            self._send_file(WEB_ROOT / "app.js", "application/javascript; charset=utf-8")
        elif parsed.path == "/api/state":
            self._json(self._state())
        else:
            self.send_error(HTTPStatus.NOT_FOUND)

    def do_POST(self) -> None:
        parsed = urlparse(self.path)
        if parsed.path != "/api/command":
            self.send_error(HTTPStatus.NOT_FOUND)
            return

        try:
            length = int(self.headers.get("Content-Length", "0"))
            payload = json.loads(self.rfile.read(length) or b"{}")
            index = payload.get("index")
            if index is not None:
                index = int(index)
        except (ValueError, json.JSONDecodeError):
            self.send_error(HTTPStatus.BAD_REQUEST)
            return

        self.server_ref.controller.command(payload.get("command", ""), index)
        self._json({"ok": True})

    def _state(self) -> Dict[str, object]:
        state = self.server_ref.controller.state()
        payload = {
            "running": state.running,
            "currentSlide": state.current_slide,
            "slideCount": state.slide_count,
            "currentTitle": state.current_title,
            "notes": state.notes,
            "nextSlide": state.next_slide,
            "nextTitle": state.next_title,
            "nextPreview": state.next_preview,
            "canGoPrevious": state.can_go_previous,
            "canGoNext": state.can_go_next,
        }
        payload.update(self.server_ref.connection_info())
        return payload

    def _json(self, payload: Dict[str, object]) -> None:
        data = json.dumps(payload).encode("utf-8")
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def _send_file(self, path: Path, content_type: str) -> None:
        data = path.read_bytes()
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", content_type)
        self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)
