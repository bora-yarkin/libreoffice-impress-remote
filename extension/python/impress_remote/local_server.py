# SPDX-FileCopyrightText: 2026 Bora Yarkın
# SPDX-License-Identifier: GPL-3.0-only

from __future__ import annotations

import json
import socket
import threading
import time
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qsl, urlencode, urlparse, urlunparse

from impress_remote.config import (
    RemoteConfig,
    normalize_preferred_route,
    relay_join_url,
    route_label,
)
from impress_remote.controller import ImpressController
from impress_remote.crypto import random_token
from impress_remote.network import discover_direct_ipv6_urls, discover_local_urls
from impress_remote.paths import module_file_path
from impress_remote.relay_client import RelayClient

WEB_ROOT = module_file_path(__file__).parents[2] / "web"
AUTO_ROUTE_PRIORITY = ("local", "ipv6", "relay")


def _url_with_fragment_params(url: str, **params: str) -> str:
    parsed = urlparse(url)
    values = dict(parse_qsl(parsed.fragment, keep_blank_values=True))
    for key, value in params.items():
        values[key] = value
    fragment = urlencode(values)
    return urlunparse(parsed._replace(fragment=fragment))


class IPv6ThreadingHTTPServer(ThreadingHTTPServer):
    address_family = socket.AF_INET6

    def server_bind(self) -> None:
        if hasattr(socket, "IPPROTO_IPV6") and hasattr(socket, "IPV6_V6ONLY"):
            self.socket.setsockopt(socket.IPPROTO_IPV6, socket.IPV6_V6ONLY, 1)
        super().server_bind()


class RemoteServer:
    def __init__(self, ctx, config: RemoteConfig | None = None):
        self.ctx = ctx
        self.config = config or RemoteConfig.load()
        self.session_id = random_token(12)
        self.controller = ImpressController(ctx)
        self.http_servers: list[ThreadingHTTPServer] = []
        self.threads: list[threading.Thread] = []
        self.url = ""
        self.local_urls: list[str] = []
        self.direct_urls: list[str] = []
        self.listener_warnings: list[str] = []
        self.bound_port = self.config.local_port
        self._active_network_settings = (
            self.config.local_port,
            self.config.enable_ipv6_direct,
        )
        self.pending_restart = False
        self.relay_client: RelayClient | None = None

    def start(self) -> None:
        if self.http_servers:
            return
        parent = self

        class Handler(RemoteRequestHandler):
            server_ref = parent

        self.listener_warnings = []
        started_servers = self._start_http_servers(Handler)
        self.http_servers = started_servers
        self.bound_port = self.http_servers[0].server_address[1]
        self._active_network_settings = (
            self.config.local_port,
            self.config.enable_ipv6_direct,
        )
        self.pending_restart = False

        self.threads = []
        for server in self.http_servers:
            thread = threading.Thread(target=server.serve_forever, daemon=True)
            thread.start()
            self.threads.append(thread)

        self._refresh_urls()
        self._sync_relay_client()

    def stop(self) -> None:
        self._stop_relay_client()
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

    def state_payload(self) -> dict[str, object]:
        state = self.controller.state()
        payload = {
            "running": state.running,
            "documentKind": state.document_kind,
            "statusMessage": state.status_message,
            "currentSlide": state.current_slide,
            "slideCount": state.slide_count,
            "currentTitle": state.current_title,
            "notes": state.notes,
            "nextSlide": state.next_slide,
            "nextTitle": state.next_title,
            "nextPreview": state.next_preview,
            "canGoPrevious": state.can_go_previous,
            "canGoNext": state.can_go_next,
            "currentSlideImageUrl": self.current_slide_image_url(state),
        }
        payload.update(self.connection_info())
        return payload

    def current_slide_image_url(self, state=None) -> str:
        if state is None:
            state = self.controller.state()
        if state.document_kind != "impress" or state.slide_count <= 0:
            return ""
        revision = "-".join(
            (
                str(state.current_slide),
                str(state.slide_count),
                str(int(state.running)),
                str(len(state.current_title)),
                str(len(state.notes)),
            )
        )
        return f"/api/slide/current?rev={revision}"

    def console_url(self) -> str:
        preferred = self.pairing_target(self.config.preferred_route)
        if preferred["selectedUrl"]:
            return preferred["selectedUrl"]
        fallback = self.pairing_target("auto")
        if fallback["selectedUrl"]:
            return fallback["selectedUrl"]
        return self.url

    def settings_url(self) -> str:
        console_url = self.console_url()
        if not console_url:
            return ""
        return _url_with_fragment_params(console_url, view="settings")

    def connection_info(self) -> dict[str, object]:
        relay_status = {"state": "disabled", "lastError": ""}
        if self.relay_client is not None:
            relay_status = self.relay_client.status()
        pairing = self.pairing_target(self.config.preferred_route)
        route_urls = self.route_urls()
        join_url = route_urls["relay"]
        return {
            "session": self.session_id,
            "localPort": self.bound_port,
            "requestedLocalPort": self.config.local_port,
            "enableIpv6Direct": self.config.enable_ipv6_direct,
            "localUrls": list(self.local_urls),
            "directUrls": list(self.direct_urls),
            "listenerWarnings": list(self.listener_warnings),
            "configPendingRestart": self.pending_restart,
            "relayEnabled": self.config.enable_relay,
            "relayConfigured": bool(self.config.relay_url),
            "relayUrl": self.config.relay_url,
            "relayJoinUrl": join_url,
            "consoleUrl": self.console_url(),
            "settingsUrl": self.settings_url(),
            "pairingRouteRequested": pairing["requestedRoute"],
            "pairingRoute": pairing["selectedRoute"],
            "pairingRouteLabel": pairing["selectedLabel"],
            "pairingUrl": pairing["selectedUrl"],
            "pairingHint": pairing["hint"],
            "routeLocalUrl": route_urls["local"],
            "routeIpv6Url": route_urls["ipv6"],
            "routeRelayUrl": route_urls["relay"],
            "relayStatus": relay_status["state"],
            "relayLastError": relay_status["lastError"],
        }

    def config_payload(self) -> dict[str, object]:
        payload = self.config.to_dict()
        payload["restartRequired"] = self.pending_restart
        payload["activeLocalPort"] = self.bound_port
        return payload

    def apply_config(self, payload: dict[str, object]) -> dict[str, object]:
        updated = self.config.merge(payload)
        updated.save()
        self.update_config(updated, restart_runtime=False)
        return {
            "ok": True,
            "config": self.config_payload(),
            "connection": self.connection_info(),
        }

    def route_urls(self) -> dict[str, str]:
        if not self.http_servers:
            return {"local": "", "ipv6": "", "relay": ""}
        relay_url = ""
        if self.config.enable_relay and self.config.relay_url:
            relay_url = relay_join_url(self.config.relay_url, self.session_id)
        return {
            "local": self.local_urls[0] if self.local_urls else "",
            "ipv6": self.direct_urls[0] if self.direct_urls else "",
            "relay": relay_url,
        }

    def pairing_target(self, route_mode: str | None = None) -> dict[str, str]:
        requested = normalize_preferred_route(route_mode or self.config.preferred_route)
        route_urls = self.route_urls()
        selected = requested
        if requested == "auto":
            selected = ""
            for candidate in AUTO_ROUTE_PRIORITY:
                if route_urls[candidate]:
                    selected = candidate
                    break
        selected_url = route_urls.get(selected, "") if selected else ""
        return {
            "requestedRoute": requested,
            "selectedRoute": selected,
            "selectedLabel": route_label(selected) if selected else "",
            "selectedUrl": selected_url,
            "hint": self._pairing_hint(requested, selected, route_urls),
        }

    def update_config(self, updated: RemoteConfig, restart_runtime: bool) -> None:
        network_changed = (
            updated.local_port,
            updated.enable_ipv6_direct,
        ) != self._active_network_settings
        self.config = updated

        if restart_runtime and self.http_servers and network_changed:
            self.stop()
            self.start()
            self.pending_restart = False
            return

        self.pending_restart = bool(self.http_servers) and network_changed
        self._sync_relay_client()

    def _refresh_urls(self) -> None:
        self.local_urls = (
            discover_local_urls(self.bound_port, self.session_id)
            if any(server.address_family == socket.AF_INET for server in self.http_servers)
            else []
        )
        self.direct_urls = (
            discover_direct_ipv6_urls(self.bound_port, self.session_id)
            if any(server.address_family == socket.AF_INET6 for server in self.http_servers)
            else []
        )
        if self.local_urls:
            self.url = self.local_urls[0]
        elif self.direct_urls:
            self.url = self.direct_urls[0]
        else:
            self.url = f"http://127.0.0.1:{self.bound_port}/#s={self.session_id}"

    def _pairing_hint(
        self,
        requested_route: str,
        selected_route: str,
        route_urls: dict[str, str],
    ) -> str:
        if not self.http_servers:
            return "Start the remote from LibreOffice to generate a QR code."
        if selected_route and route_urls.get(selected_route):
            if requested_route == "auto" and selected_route != "local":
                return f"Auto selected {route_label(selected_route).lower()}."
            return f"Scan the QR code to pair over {route_label(selected_route).lower()}."
        if requested_route == "relay":
            return "Enable relay mode and set a relay server address to pair over the relay."
        if requested_route == "ipv6":
            return "Direct IPv6 is unavailable on this network right now."
        if requested_route == "local":
            return "A local network address is not available right now."
        return "No pairing route is currently available."

    def _start_http_servers(self, handler_cls) -> list[ThreadingHTTPServer]:
        ipv4_server = self._bind_ipv4_server(handler_cls)
        started_servers = [ipv4_server]
        if self.config.enable_ipv6_direct:
            try:
                started_servers.append(
                    IPv6ThreadingHTTPServer(("::", ipv4_server.server_address[1]), handler_cls)
                )
            except OSError as exc:
                self.listener_warnings.append(f"Direct IPv6 listener is unavailable: {exc}")
        return started_servers

    def _bind_ipv4_server(self, handler_cls) -> ThreadingHTTPServer:
        for candidate_port in range(self.config.local_port, self.config.local_port + 10):
            try:
                server = ThreadingHTTPServer((self.config.local_host, candidate_port), handler_cls)
            except OSError:
                continue
            if candidate_port != self.config.local_port:
                self.listener_warnings.append(
                    f"Port {self.config.local_port} was busy. Using {candidate_port} instead."
                )
            return server
        raise RuntimeError(
            f"Could not start the remote server on ports {self.config.local_port}-"
            f"{self.config.local_port + 9}"
        )

    def _sync_relay_client(self) -> None:
        relay_is_enabled = self.config.enable_relay and bool(self.config.relay_url)
        if not relay_is_enabled:
            self._stop_relay_client()
            return

        desired_url = self.config.relay_url
        current = self.relay_client
        if current is not None and current.relay_url == desired_url:
            return

        self._stop_relay_client()
        self.relay_client = RelayClient(
            relay_url=desired_url,
            session_id=self.session_id,
            state_provider=self.state_payload,
            command_handler=self.controller.command,
        )
        self.relay_client.start()

    def _stop_relay_client(self) -> None:
        if self.relay_client is not None:
            self.relay_client.stop()
            self.relay_client = None


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
            self._json(self.server_ref.state_payload())
        elif parsed.path == "/api/config":
            self._json(self.server_ref.config_payload())
        elif parsed.path == "/api/events":
            self._event_stream()
        elif parsed.path == "/api/slide/current":
            self._current_slide_image()
        else:
            self.send_error(HTTPStatus.NOT_FOUND)

    def do_POST(self) -> None:
        parsed = urlparse(self.path)
        if parsed.path == "/api/command":
            self._handle_command()
            return
        if parsed.path == "/api/config":
            self._handle_config_update()
            return
        self.send_error(HTTPStatus.NOT_FOUND)

    def _handle_command(self) -> None:
        try:
            payload = self._read_json()
            index = self._command_index(payload)
            command = self._command_name(payload)
        except (ValueError, json.JSONDecodeError):
            self.send_error(HTTPStatus.BAD_REQUEST)
            return

        self.server_ref.controller.command(command, index)
        self._json({"ok": True})

    def _handle_config_update(self) -> None:
        try:
            payload = self._read_json()
        except json.JSONDecodeError:
            self._json(
                {"ok": False, "error": "Configuration payload must be valid JSON."},
                HTTPStatus.BAD_REQUEST,
            )
            return

        try:
            response = self.server_ref.apply_config(payload)
        except ValueError as exc:
            self._json({"ok": False, "error": str(exc)}, HTTPStatus.BAD_REQUEST)
            return
        self._json(response)

    def _read_json(self) -> dict[str, object]:
        length = int(self.headers.get("Content-Length", "0"))
        raw = self.rfile.read(length) or b"{}"
        payload = json.loads(raw)
        if not isinstance(payload, dict):
            raise ValueError("Payload must be a JSON object.")
        return payload

    def _command_index(self, payload: dict[str, object]) -> int | None:
        index_value = payload.get("index")
        if index_value is None:
            return None
        if isinstance(index_value, bool):
            return int(index_value)
        if isinstance(index_value, int):
            return index_value
        if isinstance(index_value, str):
            return int(index_value)
        raise ValueError("Command index must be an integer.")

    def _command_name(self, payload: dict[str, object]) -> str:
        command = payload.get("command", "")
        if not isinstance(command, str):
            raise ValueError("Command name must be a string.")
        return command

    def _event_stream(self) -> None:
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", "text/event-stream; charset=utf-8")
        self.send_header("Cache-Control", "no-store")
        self.send_header("Connection", "keep-alive")
        self.send_header("X-Accel-Buffering", "no")
        self.end_headers()

        last_payload = ""
        last_heartbeat = time.monotonic()
        try:
            while True:
                payload = json.dumps(self.server_ref.state_payload(), separators=(",", ":"))
                now = time.monotonic()
                if payload != last_payload:
                    self.wfile.write(b"event: state\n")
                    self.wfile.write(f"data: {payload}\n\n".encode())
                    self.wfile.flush()
                    last_payload = payload
                    last_heartbeat = now
                elif now - last_heartbeat >= 10:
                    self.wfile.write(b": keepalive\n\n")
                    self.wfile.flush()
                    last_heartbeat = now
                time.sleep(0.35)
        except (BrokenPipeError, ConnectionResetError, OSError):
            return

    def _current_slide_image(self) -> None:
        try:
            data = self.server_ref.controller.current_slide_png_bytes()
        except RuntimeError as exc:
            self._json({"ok": False, "error": str(exc)}, HTTPStatus.NOT_FOUND)
            return
        except Exception as exc:
            self._json({"ok": False, "error": str(exc)}, HTTPStatus.INTERNAL_SERVER_ERROR)
            return

        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", "image/png")
        self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def _json(self, payload: dict[str, object], status: HTTPStatus = HTTPStatus.OK) -> None:
        data = json.dumps(payload).encode("utf-8")
        self.send_response(status)
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
