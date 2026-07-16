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
        self.config = config or RemoteConfig.load(ctx=ctx)
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
            self.config.enable_local_listener,
            self.config.enable_ipv6_direct,
        )
        self.pending_restart = False
        self.relay_client: RelayClient | None = None
        self._runtime_requested = False
        self.client_connected = False
        self.client_connection_source = ""
        self.last_client_seen_at = 0.0

    def is_running(self) -> bool:
        relay_running = self.relay_client is not None and self.relay_client.is_running()
        return bool(self.http_servers) or relay_running

    def start(self) -> None:
        if self.is_running():
            return
        parent = self

        class Handler(RemoteRequestHandler):
            server_ref = parent

        self.listener_warnings = []
        self.http_servers = []
        self.threads = []
        self._runtime_requested = True
        try:
            self.http_servers = self._start_http_servers(Handler)
            self.bound_port = (
                self.http_servers[0].server_address[1]
                if self.http_servers
                else self.config.local_port
            )
            self._active_network_settings = self._network_settings(self.config)
            self.pending_restart = False

            for server in self.http_servers:
                thread = threading.Thread(target=server.serve_forever, daemon=True)
                thread.start()
                self.threads.append(thread)

            self._sync_relay_client()
            self._refresh_urls()
            if not self.is_running():
                raise RuntimeError("Enable at least one pairing route before starting the remote.")
        except Exception:
            self.stop()
            raise

    def stop(self) -> None:
        self._runtime_requested = False
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
        self.pending_restart = False
        self.bound_port = self.config.local_port
        self.client_connected = False
        self.client_connection_source = ""
        self.last_client_seen_at = 0.0

    def state_payload(self) -> dict[str, object]:
        state = self.controller.state()
        payload = {
            "running": state.running,
            "presentationActive": state.active,
            "presentationPaused": state.paused,
            "presentationBlanked": state.blanked,
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
            "remainingSlides": state.remaining_slides,
            "atEndOfDeck": state.at_end_of_deck,
            "elapsedSeconds": state.elapsed_seconds,
            "currentSlideImageUrl": self.current_slide_image_url(state),
            "nextSlideImageUrl": self.next_slide_image_url(state),
        }
        payload.update(self.connection_info())
        return payload

    def current_slide_image_url(self, state=None) -> str:
        if state is None:
            state = self.controller.state()
        if (
            state.document_kind != "impress"
            or state.slide_count <= 0
            or not state.current_render_token
        ):
            return ""
        return f"/api/slide/current?rev={state.current_render_token}"

    def next_slide_image_url(self, state=None) -> str:
        if state is None:
            state = self.controller.state()
        if state.next_slide is None or not state.next_render_token:
            return ""
        return f"/api/slide/next?rev={state.next_render_token}"

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
            "running": self.is_running(),
            "localPort": self.bound_port,
            "requestedLocalPort": self.config.local_port,
            "enableLocalListener": self.config.enable_local_listener,
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
            "clientConnected": self.client_connected,
            "clientConnectionSource": self.client_connection_source,
        }

    def config_payload(self) -> dict[str, object]:
        payload = self.config.to_dict()
        payload["restartRequired"] = self.pending_restart
        payload["activeLocalPort"] = self.bound_port
        return payload

    def apply_config(self, payload: dict[str, object]) -> dict[str, object]:
        updated = self.config.merge(payload)
        updated.save(ctx=self.ctx)
        self.update_config(updated, restart_runtime=False)
        return {
            "ok": True,
            "config": self.config_payload(),
            "connection": self.connection_info(),
        }

    def route_urls(self) -> dict[str, str]:
        return self.preview_route_urls(self.config)

    def preview_route_urls(self, config: RemoteConfig) -> dict[str, str]:
        if not self.is_running():
            return {"local": "", "ipv6": "", "relay": ""}
        listeners_match = self._network_settings(config) == self._active_network_settings
        relay_url = ""
        if config.enable_relay and config.relay_url:
            relay_url = relay_join_url(config.relay_url, self.session_id)
        return {
            "local": (
                self.local_urls[0]
                if listeners_match and config.enable_local_listener and self.local_urls
                else ""
            ),
            "ipv6": (
                self.direct_urls[0]
                if listeners_match and config.enable_ipv6_direct and self.direct_urls
                else ""
            ),
            "relay": relay_url,
        }

    def pairing_target(self, route_mode: str | None = None) -> dict[str, str]:
        return self.preview_pairing_target(self.config, route_mode)

    def preview_pairing_target(
        self,
        config: RemoteConfig,
        route_mode: str | None = None,
    ) -> dict[str, str]:
        requested = normalize_preferred_route(route_mode or config.preferred_route)
        route_urls = self.preview_route_urls(config)
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
            "hint": self._pairing_hint(requested, selected, route_urls, config),
        }

    def update_config(self, updated: RemoteConfig, restart_runtime: bool) -> None:
        network_changed = self._network_settings(updated) != self._active_network_settings
        self.config = updated

        if restart_runtime and self.is_running() and network_changed:
            self.stop()
            self.start()
            self.pending_restart = False
            return

        self.pending_restart = self.is_running() and network_changed
        self._sync_relay_client()
        self._refresh_urls()

    def _network_settings(self, config: RemoteConfig) -> tuple[int, bool, bool]:
        return (
            config.local_port,
            config.enable_local_listener,
            config.enable_ipv6_direct,
        )

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
        route_urls = self.route_urls()
        if route_urls["local"]:
            self.url = route_urls["local"]
        elif route_urls["ipv6"]:
            self.url = route_urls["ipv6"]
        elif route_urls["relay"]:
            self.url = route_urls["relay"]
        elif self.http_servers:
            self.url = f"http://127.0.0.1:{self.bound_port}/#s={self.session_id}"
        else:
            self.url = ""

    def mark_client_activity(self, source: str, client_host: str | None = None) -> None:
        if client_host is not None and client_host in {"127.0.0.1", "::1", "localhost"}:
            return
        self.client_connected = True
        self.client_connection_source = source
        self.last_client_seen_at = time.monotonic()

    def _pairing_hint(
        self,
        requested_route: str,
        selected_route: str,
        route_urls: dict[str, str],
        config: RemoteConfig,
    ) -> str:
        if not self.is_running():
            return "Start the remote from LibreOffice to generate a QR code."
        if selected_route and route_urls.get(selected_route):
            if requested_route == "auto" and selected_route != "local":
                return f"Auto selected {route_label(selected_route).lower()}."
            return f"Scan the QR code to pair over {route_label(selected_route).lower()}."
        if self._network_settings(config) != self._active_network_settings:
            return "Save and restart the remote to apply the new listener settings."
        if requested_route == "relay":
            if not config.enable_relay:
                return "Relay pairing is disabled in LibreOffice settings."
            return "Set a relay server address to pair over the relay."
        if requested_route == "ipv6":
            if not config.enable_ipv6_direct:
                return "Direct IPv6 pairing is disabled in LibreOffice settings."
            return "Direct IPv6 is unavailable on this network right now."
        if requested_route == "local":
            if not config.enable_local_listener:
                return "Local network pairing is disabled in LibreOffice settings."
            return "A local network address is not available right now."
        return "No pairing route is currently available."

    def _start_http_servers(self, handler_cls) -> list[ThreadingHTTPServer]:
        started_servers: list[ThreadingHTTPServer] = []
        if self.config.enable_local_listener:
            ipv4_server = self._bind_ipv4_server(handler_cls)
            started_servers.append(ipv4_server)
        elif self.config.enable_ipv6_direct:
            started_servers.append(self._bind_ipv6_server(handler_cls))

        if self.config.enable_local_listener and self.config.enable_ipv6_direct and started_servers:
            try:
                started_servers.append(
                    IPv6ThreadingHTTPServer(
                        ("::", started_servers[0].server_address[1]),
                        handler_cls,
                    )
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

    def _bind_ipv6_server(self, handler_cls) -> ThreadingHTTPServer:
        for candidate_port in range(self.config.local_port, self.config.local_port + 10):
            try:
                server = IPv6ThreadingHTTPServer(("::", candidate_port), handler_cls)
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
        if not self._runtime_requested:
            self._stop_relay_client()
            return
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
            activity_callback=self.mark_client_activity,
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
        self._track_client_activity(parsed.path)
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
        elif parsed.path == "/api/slide/next":
            self._next_slide_image()
        else:
            self.send_error(HTTPStatus.NOT_FOUND)

    def do_POST(self) -> None:
        parsed = urlparse(self.path)
        self._track_client_activity(parsed.path)
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

    def _track_client_activity(self, path: str) -> None:
        if path not in {
            "/",
            "/index.html",
            "/app.css",
            "/app.js",
            "/api/state",
            "/api/events",
            "/api/command",
            "/api/slide/current",
            "/api/slide/next",
        }:
            return
        client_host = self.client_address[0] if self.client_address else None
        self.server_ref.mark_client_activity("local", client_host)

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

    def _next_slide_image(self) -> None:
        try:
            data = self.server_ref.controller.next_slide_png_bytes()
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
