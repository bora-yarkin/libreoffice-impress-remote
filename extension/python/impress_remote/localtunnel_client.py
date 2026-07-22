# SPDX-FileCopyrightText: 2026 Bora Yarkın
# SPDX-License-Identifier: GPL-3.0-only

from __future__ import annotations

from dataclasses import dataclass
from collections.abc import Callable
import json
import socket
import threading
import time
from urllib.error import HTTPError, URLError
from urllib.parse import urlparse
from urllib.request import urlopen

from impress_remote.localization import translate

DEFAULT_TUNNEL_HOST = "https://localtunnel.me"
CONNECT_TIMEOUT_SECONDS = 10.0
BUFFER_SIZE = 64 * 1024


@dataclass(frozen=True)
class LocalTunnelInfo:
    name: str
    url: str
    remote_host: str
    remote_port: int
    remote_ip: str = ""
    max_connections: int = 1


def normalize_tunnel_host(value: str) -> str:
    text = value.strip() or DEFAULT_TUNNEL_HOST
    parsed = urlparse(text if "://" in text else f"https://{text}")
    if parsed.scheme not in {"http", "https"}:
        raise ValueError(translate("localtunnel.error.hostScheme", scheme=parsed.scheme))
    if not parsed.netloc:
        raise ValueError(translate("localtunnel.error.hostMissing"))
    path = parsed.path.rstrip("/")
    return f"{parsed.scheme}://{parsed.netloc}{path}"


def _request_tunnel_info(host: str, subdomain: str = "") -> LocalTunnelInfo:
    normalized_host = normalize_tunnel_host(host)
    parsed_host = urlparse(normalized_host)
    endpoint = f"{normalized_host}/"
    requested_name = subdomain.strip().lower()
    endpoint += requested_name if requested_name else "?new"

    try:
        with urlopen(endpoint, timeout=CONNECT_TIMEOUT_SECONDS) as response:
            raw_status = getattr(response, "status", None)
            if raw_status is None:
                raw_status = response.getcode()
            status = int(raw_status)
            raw = response.read().decode("utf-8")
    except HTTPError as exc:
        raw = exc.read().decode("utf-8", errors="replace")
        raise ConnectionError(
            translate("localtunnel.error.requestFailed", status=exc.code, message=raw)
        ) from exc
    except URLError as exc:
        raise ConnectionError(translate("localtunnel.error.unreachable", error=exc)) from exc

    try:
        payload = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise ConnectionError(translate("localtunnel.error.invalidResponse")) from exc
    if status != 200 or not isinstance(payload, dict):
        raise ConnectionError(
            translate("localtunnel.error.requestFailed", status=status, message=raw)
        )

    remote_port = payload.get("port")
    tunnel_url = str(payload.get("url", "")).strip()
    tunnel_name = str(payload.get("id", "")).strip()
    if not tunnel_url or not tunnel_name or not isinstance(remote_port, int):
        raise ConnectionError(translate("localtunnel.error.invalidResponse"))

    max_connections = payload.get("max_conn_count", 1)
    if not isinstance(max_connections, int) or max_connections < 1:
        max_connections = 1

    return LocalTunnelInfo(
        name=tunnel_name,
        url=tunnel_url,
        remote_host=parsed_host.hostname or parsed_host.netloc,
        remote_port=remote_port,
        remote_ip=str(payload.get("ip", "")).strip(),
        max_connections=max_connections,
    )


class LocalTunnelClient:
    def __init__(
        self,
        *,
        local_host: str,
        local_port: int,
        tunnel_host: str = DEFAULT_TUNNEL_HOST,
        subdomain: str = "",
        activity_callback: Callable[[str], None] | None = None,
    ) -> None:
        self.local_host = local_host
        self.local_port = local_port
        self.tunnel_host = tunnel_host
        self.subdomain = subdomain
        self.activity_callback = activity_callback
        self.url = ""
        self._state = "stopped"
        self._last_error = ""
        self._stop_event = threading.Event()
        self._thread: threading.Thread | None = None
        self._lock = threading.Lock()
        self._sockets: list[socket.socket] = []

    def start(self) -> None:
        if self.is_running():
            return
        self._stop_event.clear()
        self._thread = threading.Thread(target=self._run, daemon=True, name="localtunnel-client")
        self._thread.start()

    def stop(self) -> None:
        self._stop_event.set()
        with self._lock:
            sockets = list(self._sockets)
            self._sockets = []
        for sock in sockets:
            try:
                sock.shutdown(socket.SHUT_RDWR)
            except OSError:
                pass
            try:
                sock.close()
            except OSError:
                pass
        if self._thread is not None:
            self._thread.join(timeout=2)
            self._thread = None
        self._set_status("stopped", "")
        self.url = ""

    def is_running(self) -> bool:
        return self._thread is not None and self._thread.is_alive()

    def status(self) -> dict[str, str]:
        with self._lock:
            return {"state": self._state, "lastError": self._last_error, "url": self.url}

    def _run(self) -> None:
        try:
            self._set_status("connecting", "")
            info = _request_tunnel_info(self.tunnel_host, self.subdomain)
            self.url = info.url
            self._set_status("ready", "")
            connection_count = min(max(info.max_connections, 1), 8)
            workers = [
                threading.Thread(
                    target=self._connection_loop,
                    args=(info,),
                    daemon=True,
                    name=f"localtunnel-socket-{index}",
                )
                for index in range(connection_count)
            ]
            for worker in workers:
                worker.start()
            while not self._stop_event.is_set():
                if not any(worker.is_alive() for worker in workers):
                    break
                time.sleep(0.2)
        except Exception as exc:
            self._set_status("error", str(exc))
        finally:
            if not self._stop_event.is_set() and self._state != "error":
                self._set_status("closed", "")

    def _connection_loop(self, info: LocalTunnelInfo) -> None:
        remote_host = info.remote_ip or info.remote_host
        while not self._stop_event.is_set():
            remote: socket.socket | None = None
            local: socket.socket | None = None
            try:
                remote = socket.create_connection(
                    (remote_host, info.remote_port),
                    timeout=CONNECT_TIMEOUT_SECONDS,
                )
                remote.settimeout(None)
                self._track_socket(remote)
                local = socket.create_connection(
                    (self.local_host, self.local_port),
                    timeout=CONNECT_TIMEOUT_SECONDS,
                )
                local.settimeout(None)
                self._track_socket(local)
                self._pipe_pair(remote, local)
            except OSError as exc:
                if not self._stop_event.is_set():
                    self._set_status("error", str(exc))
                    time.sleep(1.0)
            finally:
                for sock in (remote, local):
                    if sock is not None:
                        self._untrack_socket(sock)
                        try:
                            sock.close()
                        except OSError:
                            pass

    def _pipe_pair(self, remote: socket.socket, local: socket.socket) -> None:
        done = threading.Event()
        threads = (
            threading.Thread(
                target=self._pipe,
                args=(remote, local, done, True),
                daemon=True,
            ),
            threading.Thread(
                target=self._pipe,
                args=(local, remote, done, False),
                daemon=True,
            ),
        )
        for thread in threads:
            thread.start()
        while not self._stop_event.is_set() and not done.is_set():
            time.sleep(0.1)

    def _pipe(
        self,
        source: socket.socket,
        destination: socket.socket,
        done: threading.Event,
        mark_activity: bool,
    ) -> None:
        activity_reported = False
        try:
            while not self._stop_event.is_set():
                data = source.recv(BUFFER_SIZE)
                if not data:
                    break
                if mark_activity and not activity_reported and self.activity_callback is not None:
                    self.activity_callback("tunnel")
                    activity_reported = True
                destination.sendall(data)
        except OSError:
            pass
        finally:
            done.set()
            try:
                destination.shutdown(socket.SHUT_RDWR)
            except OSError:
                pass

    def _track_socket(self, sock: socket.socket) -> None:
        with self._lock:
            self._sockets.append(sock)

    def _untrack_socket(self, sock: socket.socket) -> None:
        with self._lock:
            try:
                self._sockets.remove(sock)
            except ValueError:
                pass

    def _set_status(self, state: str, last_error: str) -> None:
        with self._lock:
            self._state = state
            self._last_error = last_error
