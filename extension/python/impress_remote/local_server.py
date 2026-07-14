# SPDX-FileCopyrightText: 2026 Bora Yarkın
# SPDX-License-Identifier: GPL-3.0-only

from __future__ import annotations

import json
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from impress_remote.config import RemoteConfig
from impress_remote.controller import ImpressController
from impress_remote.crypto import random_token

WEB_ROOT = Path(__file__).resolve().parents[2] / "web"


class RemoteServer:
    def __init__(self, ctx, config: RemoteConfig | None = None):
        self.ctx = ctx
        self.config = config or RemoteConfig()
        self.session_id = random_token(12)
        self.controller = ImpressController(ctx)
        self.httpd: ThreadingHTTPServer | None = None
        self.thread: threading.Thread | None = None
        self.url = f"http://127.0.0.1:{self.config.local_port}/#s={self.session_id}"

    def start(self) -> None:
        if self.httpd is not None:
            return
        parent = self

        class Handler(RemoteRequestHandler):
            server_ref = parent

        self.httpd = ThreadingHTTPServer((self.config.local_host, self.config.local_port), Handler)
        self.thread = threading.Thread(target=self.httpd.serve_forever, daemon=True)
        self.thread.start()

    def stop(self) -> None:
        if self.httpd is not None:
            self.httpd.shutdown()
            self.httpd.server_close()
            self.httpd = None


class RemoteRequestHandler(BaseHTTPRequestHandler):
    server_ref: RemoteServer

    def log_message(self, fmt: str, *args) -> None:
        return

    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        if parsed.path in {"/", "/index.html"}:
            self._send_file(WEB_ROOT / "index.html", "text/html")
        elif parsed.path == "/app.css":
            self._send_file(WEB_ROOT / "app.css", "text/css")
        elif parsed.path == "/app.js":
            self._send_file(WEB_ROOT / "app.js", "application/javascript")
        elif parsed.path == "/api/state":
            self._json(self._state())
        else:
            self.send_error(404)

    def do_POST(self) -> None:
        parsed = urlparse(self.path)
        if parsed.path != "/api/command":
            self.send_error(404)
            return
        length = int(self.headers.get("Content-Length", "0"))
        payload = json.loads(self.rfile.read(length) or b"{}")
        self.server_ref.controller.command(payload.get("command", ""), payload.get("index"))
        self._json({"ok": True})

    def _state(self) -> dict[str, object]:
        state = self.server_ref.controller.state()
        return {
            "running": state.running,
            "currentSlide": state.current_slide,
            "slideCount": state.slide_count,
            "notes": state.notes,
            "session": self.server_ref.session_id,
        }

    def _json(self, payload: dict[str, object]) -> None:
        data = json.dumps(payload).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def _send_file(self, path: Path, content_type: str) -> None:
        data = path.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)
