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
    relay_session_status_url,
    route_label,
)
from impress_remote.controller import ImpressController
from impress_remote.crypto import base64url_encode, random_token
from impress_remote.network import (
    discover_direct_ipv6_addresses,
    discover_local_urls,
    format_http_url,
    probe_ipv6_listener,
)
from impress_remote.localization import localization_root, translate
from impress_remote.paths import resolve_packaged_or_shared_dir
from impress_remote.protocol import (
    RELAY_KIND_COMMAND,
    RelayProtocolFailure,
    SecureRelayCodec,
    decode_command_payload,
    encode_hello_message,
)
from impress_remote.relay_client import RelayClient

WEB_ROOT = resolve_packaged_or_shared_dir(
    __file__,
    ("web",),
    ("shared", "webui"),
)
LOCALIZATION_ROOT = localization_root()
AUTO_ROUTE_PRIORITY = ("local", "ipv6", "relay")


def _url_with_fragment_params(url: str, **params: str) -> str:
    parsed = urlparse(url)
    values = dict(parse_qsl(parsed.fragment, keep_blank_values=True))
    for key, value in params.items():
        values[key] = value
    fragment = urlencode(values)
    return urlunparse(parsed._replace(fragment=fragment))


def _json_object(raw: str) -> dict[str, object]:
    payload = json.loads(raw)
    if not isinstance(payload, dict):
        raise ValueError(translate("error.configJson"))
    return payload


class SecureDirectSession:
    def __init__(self, session_id: str, pairing_secret: str):
        self.session_id = session_id
        self._lock = threading.Lock()
        self._codec = SecureRelayCodec(
            role="plugin",
            session_id=session_id,
            pairing_secret=pairing_secret,
        )
        self._hello = self._codec.rotate_send_key()

    def current_hello_payload(self) -> dict[str, object]:
        with self._lock:
            return _json_object(encode_hello_message(self._hello))

    def state_response(self, payload: dict[str, object]) -> dict[str, object]:
        with self._lock:
            hello = self._rotate_if_needed()
            frame = _json_object(self._codec.encode_state_frame(payload))
        return {"hello": hello, "frame": frame}

    def asset_response(
        self,
        *,
        content_type: str,
        data: bytes,
        slot: str,
        revision: str = "",
    ) -> dict[str, object]:
        asset_payload: dict[str, object] = {
            "contentType": content_type,
            "encoding": "base64url",
            "data": base64url_encode(data),
            "slot": slot,
        }
        if revision:
            asset_payload["revision"] = revision
        with self._lock:
            hello = self._rotate_if_needed()
            frame = _json_object(self._codec.encode_asset_frame(asset_payload))
        return {"hello": hello, "frame": frame}

    def decode_command(self, payload: dict[str, object]):
        with self._lock:
            frame = self._codec.decode_frame(json.dumps(payload, separators=(",", ":")))
        if frame is None or frame.kind != RELAY_KIND_COMMAND:
            raise RelayProtocolFailure(
                "invalid-command",
                translate("error.directCommandFrame"),
            )
        command = decode_command_payload(frame.payload)
        if command is None:
            raise RelayProtocolFailure(
                "invalid-command",
                translate("error.directCommandMissing"),
            )
        return command

    def _rotate_if_needed(self) -> dict[str, object] | None:
        if not self._codec.should_rotate_send_key():
            return None
        self._hello = self._codec.rotate_send_key()
        return _json_object(encode_hello_message(self._hello))


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
        self.pairing_secret = random_token(32)
        self.relay_admission_token = random_token(24)
        self.direct_session = SecureDirectSession(self.session_id, self.pairing_secret)
        self.controller = ImpressController(ctx)
        self.http_servers: list[ThreadingHTTPServer] = []
        self.threads: list[threading.Thread] = []
        self.url = ""
        self.local_urls: list[str] = []
        self.direct_urls: list[str] = []
        self.direct_ipv6_addresses: list[str] = []
        self.direct_ipv6_ready_addresses: list[str] = []
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
        self.direct_ipv6_addresses = []
        self.direct_ipv6_ready_addresses = []
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
                raise RuntimeError(translate("error.remoteRouteRequired"))
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
        self.direct_ipv6_addresses = []
        self.direct_ipv6_ready_addresses = []
        self.url = ""
        self.pending_restart = False
        self.bound_port = self.config.local_port
        self.client_connected = False
        self.client_connection_source = ""
        self.last_client_seen_at = 0.0

    def state_payload(self) -> dict[str, object]:
        state = self.controller.state()
        payload = self._state_payload(
            state,
            current_slide_image_url=self.current_slide_image_url(state),
            next_slide_image_url=self.next_slide_image_url(state),
        )
        payload.update(self.connection_info())
        return payload

    def relay_state_payload(self) -> dict[str, object]:
        state = self.controller.state()
        payload = self._state_payload(
            state,
            current_slide_image_url="",
            next_slide_image_url="",
        )
        payload.update(self.connection_info())
        return payload

    def _state_payload(
        self,
        state,
        *,
        current_slide_image_url: str,
        next_slide_image_url: str,
    ) -> dict[str, object]:
        return {
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
            "currentSlideImageRevision": getattr(state, "current_render_token", ""),
            "nextSlideImageRevision": getattr(state, "next_render_token", ""),
            "currentSlideImageUrl": current_slide_image_url,
            "nextSlideImageUrl": next_slide_image_url,
        }

    def current_slide_image_url(self, state=None) -> str:
        if state is None:
            state = self.controller.state()
        if (
            state.document_kind != "impress"
            or state.slide_count <= 0
            or not state.current_render_token
        ):
            return ""
        return f"/api/direct/slide/current?rev={state.current_render_token}"

    def next_slide_image_url(self, state=None) -> str:
        if state is None:
            state = self.controller.state()
        if state.next_slide is None or not state.next_render_token:
            return ""
        return f"/api/direct/slide/next?rev={state.next_render_token}"

    def secure_current_slide_image_url(self, state=None) -> str:
        if state is None:
            state = self.controller.state()
        if (
            state.document_kind != "impress"
            or state.slide_count <= 0
            or not state.current_render_token
        ):
            return ""
        return f"/api/direct/slide/current?rev={state.current_render_token}"

    def secure_next_slide_image_url(self, state=None) -> str:
        if state is None:
            state = self.controller.state()
        if state.next_slide is None or not state.next_render_token:
            return ""
        return f"/api/direct/slide/next?rev={state.next_render_token}"

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

    def secure_direct_state_payload(self) -> dict[str, object]:
        state = self.controller.state()
        payload = self._state_payload(
            state,
            current_slide_image_url=self.secure_current_slide_image_url(state),
            next_slide_image_url=self.secure_next_slide_image_url(state),
        )
        payload.update(self.connection_info())
        return payload

    def local_fallback_current_slide_image_url(self, state=None) -> str:
        if state is None:
            state = self.controller.state()
        if (
            state.document_kind != "impress"
            or state.slide_count <= 0
            or not state.current_render_token
        ):
            return ""
        return f"/api/local/slide/current?rev={state.current_render_token}"

    def local_fallback_next_slide_image_url(self, state=None) -> str:
        if state is None:
            state = self.controller.state()
        if state.next_slide is None or not state.next_render_token:
            return ""
        return f"/api/local/slide/next?rev={state.next_render_token}"

    def local_fallback_state_payload(self) -> dict[str, object]:
        state = self.controller.state()
        payload = self._state_payload(
            state,
            current_slide_image_url=self.local_fallback_current_slide_image_url(state),
            next_slide_image_url=self.local_fallback_next_slide_image_url(state),
        )
        payload.update(self.connection_info())
        payload["transportSecurity"] = "local-authenticated-plaintext"
        return payload

    def secure_direct_state_response(self) -> dict[str, object]:
        return self.direct_session.state_response(self.secure_direct_state_payload())

    def secure_direct_command(self, payload: dict[str, object]) -> tuple[str, int | None]:
        command = self.direct_session.decode_command(payload)
        return command.command, command.index

    def secure_direct_slide_response(
        self,
        *,
        slot: str,
        revision: str = "",
    ) -> dict[str, object]:
        if slot == "current":
            data = self.controller.current_slide_png_bytes()
        else:
            data = self.controller.next_slide_png_bytes()
        return self.direct_session.asset_response(
            content_type="image/png",
            data=data,
            slot=slot,
            revision=revision,
        )

    def relay_asset_payload(self, slot: str, revision: str) -> dict[str, object] | None:
        expected_revision = str(revision).strip()
        if not expected_revision:
            return None

        before = self.controller.state()
        if slot == "current":
            if (
                before.document_kind != "impress"
                or before.slide_count <= 0
                or before.current_render_token != expected_revision
            ):
                return None
            data = self.controller.current_slide_png_bytes()
            after = self.controller.state()
            if after.current_render_token != expected_revision:
                return None
        elif slot == "next":
            if before.next_slide is None or before.next_render_token != expected_revision:
                return None
            data = self.controller.next_slide_png_bytes()
            after = self.controller.state()
            if after.next_render_token != expected_revision:
                return None
        else:
            return None

        return {
            "contentType": "image/png",
            "encoding": "base64url",
            "data": base64url_encode(data),
            "slot": slot,
            "revision": expected_revision,
        }

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
            "ipv6GlobalAddresses": list(self.direct_ipv6_addresses),
            "ipv6ReachableAddresses": list(self.direct_ipv6_ready_addresses),
            "ipv6Status": self._direct_ipv6_status(),
            "ipv6Hint": self._direct_ipv6_hint(),
            "listenerWarnings": list(self.listener_warnings),
            "configPendingRestart": self.pending_restart,
            "relayEnabled": self.config.enable_relay,
            "relayConfigured": bool(self.config.relay_url),
            "relayUrl": self.config.relay_url,
            "relayJoinUrl": join_url,
            "relaySessionStatusUrl": (
                relay_session_status_url(
                    self.config.relay_url,
                    self.session_id,
                    self.relay_admission_token,
                )
                if self.config.relay_url
                else ""
            ),
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
            relay_url = relay_join_url(
                config.relay_url,
                self.session_id,
                self.pairing_secret,
                self.relay_admission_token,
            )
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
            [
                _url_with_fragment_params(url, mode="local", k=self.pairing_secret)
                for url in discover_local_urls(self.bound_port, self.session_id)
            ]
            if any(server.address_family == socket.AF_INET for server in self.http_servers)
            else []
        )
        self._refresh_direct_ipv6_status()
        self.direct_urls = (
            [
                _url_with_fragment_params(
                    format_http_url(address, self.bound_port, self.session_id),
                    mode="ipv6",
                    k=self.pairing_secret,
                )
                for address in self.direct_ipv6_ready_addresses
            ]
            if self.direct_ipv6_ready_addresses
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
            self.url = _url_with_fragment_params(
                f"http://127.0.0.1:{self.bound_port}/#s={self.session_id}",
                mode="local",
                k=self.pairing_secret,
            )
        else:
            self.url = ""

    def _refresh_direct_ipv6_status(self) -> None:
        has_ipv6_listener = any(
            server.address_family == socket.AF_INET6 for server in self.http_servers
        )
        if not has_ipv6_listener:
            self.direct_ipv6_addresses = []
            self.direct_ipv6_ready_addresses = []
            return
        self.direct_ipv6_addresses = discover_direct_ipv6_addresses()
        self.direct_ipv6_ready_addresses = [
            address
            for address in self.direct_ipv6_addresses
            if probe_ipv6_listener(address, self.bound_port)
        ]

    def mark_client_activity(self, source: str, client_host: str | None = None) -> None:
        if client_host is not None and client_host in {"127.0.0.1", "::1", "localhost"}:
            return
        first_client_connection = not self.client_connected
        self.client_connected = True
        self.client_connection_source = source
        self.last_client_seen_at = time.monotonic()
        if first_client_connection:
            self._start_presentation_for_client()

    def _start_presentation_for_client(self) -> None:
        state = self.controller.state()
        if state.document_kind != "impress" or state.running or state.slide_count <= 0:
            return
        try:
            self.controller.command("start_presentation_from_first_slide")
        except Exception:
            return

    def _pairing_hint(
        self,
        requested_route: str,
        selected_route: str,
        route_urls: dict[str, str],
        config: RemoteConfig,
    ) -> str:
        if not self.is_running():
            return translate("localServer.hint.start")
        if selected_route and route_urls.get(selected_route):
            if selected_route == "ipv6":
                return translate("localServer.hint.directIPv6")
            if requested_route == "auto" and selected_route != "local":
                return translate(
                    "localServer.hint.autoSelected",
                    route=route_label(selected_route).lower(),
                )
            return translate("localServer.hint.route", route=route_label(selected_route).lower())
        if self._network_settings(config) != self._active_network_settings:
            return translate("localServer.hint.restart")
        if requested_route == "relay":
            if not config.enable_relay:
                return translate("localServer.hint.relayDisabled")
            return translate("localServer.hint.relayMissing")
        if requested_route == "ipv6":
            if not config.enable_ipv6_direct:
                return translate("localServer.directIPv6.disabled")
            return self._direct_ipv6_hint(config)
        if requested_route == "local":
            if not config.enable_local_listener:
                return translate("localServer.hint.localDisabled")
            return translate("localServer.hint.localUnavailable")
        return translate("localServer.hint.noRoute")

    def _direct_ipv6_status(self, config: RemoteConfig | None = None) -> str:
        candidate = config or self.config
        if not candidate.enable_ipv6_direct:
            return "disabled"
        if not any(server.address_family == socket.AF_INET6 for server in self.http_servers):
            return "listener-unavailable"
        if not self.direct_ipv6_addresses:
            return "no-global-address"
        if not self.direct_ipv6_ready_addresses:
            return "self-test-failed"
        return "ready"

    def _direct_ipv6_hint(self, config: RemoteConfig | None = None) -> str:
        status = self._direct_ipv6_status(config)
        if status == "disabled":
            return translate("localServer.directIPv6.disabled")
        if status == "listener-unavailable":
            return translate("localServer.directIPv6.listenerUnavailable")
        if status == "no-global-address":
            return translate("localServer.directIPv6.noGlobalAddress")
        if status == "self-test-failed":
            return translate("localServer.directIPv6.selfTestFailed", port=self.bound_port)
        return translate("localServer.directIPv6.ready")

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
                self.listener_warnings.append(
                    translate("localServer.listener.ipv6Unavailable", error=exc)
                )
        return started_servers

    def _bind_ipv4_server(self, handler_cls) -> ThreadingHTTPServer:
        for candidate_port in range(self.config.local_port, self.config.local_port + 10):
            try:
                server = ThreadingHTTPServer((self.config.local_host, candidate_port), handler_cls)
            except OSError:
                continue
            if candidate_port != self.config.local_port:
                self.listener_warnings.append(
                    translate(
                        "localServer.listener.portBusy",
                        requested=self.config.local_port,
                        actual=candidate_port,
                    )
                )
            return server
        raise RuntimeError(
            translate(
                "localServer.listener.startFailed",
                start=self.config.local_port,
                end=self.config.local_port + 9,
            )
        )

    def _bind_ipv6_server(self, handler_cls) -> ThreadingHTTPServer:
        for candidate_port in range(self.config.local_port, self.config.local_port + 10):
            try:
                server = IPv6ThreadingHTTPServer(("::", candidate_port), handler_cls)
            except OSError:
                continue
            if candidate_port != self.config.local_port:
                self.listener_warnings.append(
                    translate(
                        "localServer.listener.portBusy",
                        requested=self.config.local_port,
                        actual=candidate_port,
                    )
                )
            return server
        raise RuntimeError(
            translate(
                "localServer.listener.startFailed",
                start=self.config.local_port,
                end=self.config.local_port + 9,
            )
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
            pairing_secret=self.pairing_secret,
            admission_token=self.relay_admission_token,
            state_provider=self.relay_state_payload,
            asset_provider=self.relay_asset_payload,
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
        elif parsed.path == "/manifest.webmanifest":
            self._send_file(WEB_ROOT / "manifest.webmanifest", "application/manifest+json")
        elif parsed.path == "/sw.js":
            self._send_file(WEB_ROOT / "sw.js", "application/javascript; charset=utf-8")
        elif parsed.path == "/icons/remote.svg":
            self._send_file(WEB_ROOT / "icons" / "remote.svg", "image/svg+xml")
        elif parsed.path.startswith("/localizations/"):
            self._localization_file(parsed.path)
        elif parsed.path == "/api/direct/handshake":
            self._json(self.server_ref.direct_session.current_hello_payload())
        elif parsed.path == "/api/direct/state":
            self._json(self.server_ref.secure_direct_state_response())
        elif parsed.path == "/api/direct/events":
            self._event_stream_secure()
        elif parsed.path == "/api/direct/slide/current":
            self._current_slide_image_secure(parsed)
        elif parsed.path == "/api/direct/slide/next":
            self._next_slide_image_secure(parsed)
        elif parsed.path == "/api/local/state":
            if self._authorize_local_fallback():
                self._json(self.server_ref.local_fallback_state_payload())
        elif parsed.path == "/api/local/slide/current":
            if self._authorize_local_fallback():
                self._current_slide_image_plain(slot="current")
        elif parsed.path == "/api/local/slide/next":
            if self._authorize_local_fallback():
                self._current_slide_image_plain(slot="next")
        else:
            self.send_error(HTTPStatus.NOT_FOUND)

    def do_POST(self) -> None:
        parsed = urlparse(self.path)
        self._track_client_activity(parsed.path)
        if parsed.path == "/api/direct/command":
            self._handle_direct_command()
            return
        if parsed.path == "/api/local/command":
            if self._authorize_local_fallback():
                self._handle_local_command()
            return
        self.send_error(HTTPStatus.NOT_FOUND)

    def _handle_direct_command(self) -> None:
        try:
            payload = self._read_json()
            command, index = self.server_ref.secure_direct_command(payload)
        except RelayProtocolFailure as exc:
            self._json({"ok": False, "error": exc.message}, HTTPStatus.BAD_REQUEST)
            return
        except (ValueError, json.JSONDecodeError):
            self.send_error(HTTPStatus.BAD_REQUEST)
            return

        self.server_ref.controller.command(command, index)
        self._json({"ok": True})

    def _handle_local_command(self) -> None:
        try:
            payload = self._read_json()
        except (ValueError, json.JSONDecodeError):
            self.send_error(HTTPStatus.BAD_REQUEST)
            return
        command = decode_command_payload(payload)
        if command is None:
            self._json(
                {"ok": False, "error": translate("error.directCommandMissing")},
                HTTPStatus.BAD_REQUEST,
            )
            return
        self.server_ref.controller.command(command.command, command.index)
        self._json({"ok": True})

    def _track_client_activity(self, path: str) -> None:
        if path not in {
            "/",
            "/index.html",
            "/app.css",
            "/app.js",
            "/manifest.webmanifest",
            "/sw.js",
            "/icons/remote.svg",
            "/localizations/en.json",
            "/localizations/tr.json",
            "/api/direct/handshake",
            "/api/direct/state",
            "/api/direct/events",
            "/api/direct/command",
            "/api/direct/slide/current",
            "/api/direct/slide/next",
            "/api/local/state",
            "/api/local/command",
            "/api/local/slide/current",
            "/api/local/slide/next",
        }:
            return
        client_host = self.client_address[0] if self.client_address else None
        source = "ipv6" if client_host and ":" in client_host else "local"
        self.server_ref.mark_client_activity(source, client_host)

    def _authorize_local_fallback(self) -> bool:
        if (
            self.headers.get("X-Impress-Remote-Session") == self.server_ref.session_id
            and self.headers.get("X-Impress-Remote-Secret") == self.server_ref.pairing_secret
        ):
            return True
        self._json(
            {"ok": False, "error": translate("error.localFallbackUnauthorized")},
            HTTPStatus.FORBIDDEN,
        )
        return False

    def _localization_file(self, path: str) -> None:
        name = Path(path).name
        if name not in {"en.json", "tr.json"}:
            self.send_error(HTTPStatus.NOT_FOUND)
            return
        self._send_file(
            LOCALIZATION_ROOT / name,
            "application/json; charset=utf-8",
        )

    def _read_json(self) -> dict[str, object]:
        length = int(self.headers.get("Content-Length", "0"))
        raw = self.rfile.read(length) or b"{}"
        payload = json.loads(raw)
        if not isinstance(payload, dict):
            raise ValueError(translate("error.payloadJson"))
        return payload

    def _event_stream_secure(self) -> None:
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", "text/event-stream; charset=utf-8")
        self.send_header("Cache-Control", "no-store")
        self.send_header("Connection", "keep-alive")
        self.send_header("X-Accel-Buffering", "no")
        self.end_headers()

        last_payload = ""
        last_heartbeat = time.monotonic()
        hello_payload = json.dumps(
            self.server_ref.direct_session.current_hello_payload(),
            separators=(",", ":"),
        )
        try:
            self.wfile.write(b"event: hello\n")
            self.wfile.write(f"data: {hello_payload}\n\n".encode())
            self.wfile.flush()
            while True:
                plain_state = self.server_ref.secure_direct_state_payload()
                state_fingerprint = json.dumps(plain_state, separators=(",", ":"))
                now = time.monotonic()
                if state_fingerprint != last_payload:
                    secure_payload = self.server_ref.direct_session.state_response(plain_state)
                    next_hello = secure_payload.get("hello")
                    if isinstance(next_hello, dict):
                        self.wfile.write(b"event: hello\n")
                        self.wfile.write(
                            f"data: {json.dumps(next_hello, separators=(',', ':'))}\n\n".encode()
                        )
                        self.wfile.flush()

                    frame_payload = json.dumps(secure_payload["frame"], separators=(",", ":"))
                    self.wfile.write(b"event: state\n")
                    self.wfile.write(f"data: {frame_payload}\n\n".encode())
                    self.wfile.flush()
                    last_payload = state_fingerprint
                    last_heartbeat = now
                elif now - last_heartbeat >= 10:
                    self.wfile.write(b": keepalive\n\n")
                    self.wfile.flush()
                    last_heartbeat = now
                time.sleep(0.35)
        except (BrokenPipeError, ConnectionResetError, OSError):
            return

    def _current_slide_image_secure(self, parsed) -> None:
        revision = dict(parse_qsl(parsed.query, keep_blank_values=True)).get("rev", "")
        try:
            payload = self.server_ref.secure_direct_slide_response(
                slot="current",
                revision=revision,
            )
        except RuntimeError as exc:
            self._json({"ok": False, "error": str(exc)}, HTTPStatus.NOT_FOUND)
            return
        except Exception as exc:
            self._json({"ok": False, "error": str(exc)}, HTTPStatus.INTERNAL_SERVER_ERROR)
            return
        self._json(payload)

    def _next_slide_image_secure(self, parsed) -> None:
        revision = dict(parse_qsl(parsed.query, keep_blank_values=True)).get("rev", "")
        try:
            payload = self.server_ref.secure_direct_slide_response(
                slot="next",
                revision=revision,
            )
        except RuntimeError as exc:
            self._json({"ok": False, "error": str(exc)}, HTTPStatus.NOT_FOUND)
            return
        except Exception as exc:
            self._json({"ok": False, "error": str(exc)}, HTTPStatus.INTERNAL_SERVER_ERROR)
            return
        self._json(payload)

    def _current_slide_image_plain(self, *, slot: str) -> None:
        try:
            if slot == "current":
                data = self.server_ref.controller.current_slide_png_bytes()
            else:
                data = self.server_ref.controller.next_slide_png_bytes()
        except RuntimeError as exc:
            self._json({"ok": False, "error": str(exc)}, HTTPStatus.NOT_FOUND)
            return
        except Exception as exc:
            self._json({"ok": False, "error": str(exc)}, HTTPStatus.INTERNAL_SERVER_ERROR)
            return
        self._bytes(data, "image/png")

    def _json(self, payload: dict[str, object], status: HTTPStatus = HTTPStatus.OK) -> None:
        data = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def _bytes(self, data: bytes, content_type: str, status: HTTPStatus = HTTPStatus.OK) -> None:
        self.send_response(status)
        self.send_header("Content-Type", content_type)
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
