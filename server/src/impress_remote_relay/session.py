# SPDX-FileCopyrightText: 2026 Bora Yarkın
# SPDX-License-Identifier: GPL-3.0-only

from collections import deque
from dataclasses import dataclass, field
import time
from typing import Any


@dataclass
class RelaySession:
    session_id: str
    admission_token: str = ""
    created_at: float = field(default_factory=time.time)
    last_seen: float = field(default_factory=time.time)
    plugin: Any | None = None
    phones: set[Any] = field(default_factory=set)
    latest_plugin_hello: str = ""
    cached_plugin_frames: deque[str] = field(default_factory=deque)
    connection_windows: dict[int, deque[float]] = field(default_factory=dict)
    last_plugin_disconnect_at: float = 0.0

    def touch(self) -> None:
        self.last_seen = time.time()

    def empty(self) -> bool:
        return self.plugin is None and not self.phones

    def phone_count(self) -> int:
        return len([phone for phone in self.phones if not getattr(phone, "closed", False)])

    def authorize(self, admission_token: str) -> bool:
        if not admission_token:
            return False
        if not self.admission_token:
            self.admission_token = admission_token
            return True
        return self.admission_token == admission_token

    def forget_connection(self, connection: Any) -> None:
        self.connection_windows.pop(id(connection), None)

    def allow_message(
        self,
        connection: Any,
        *,
        max_messages: int,
        window_seconds: float,
    ) -> bool:
        if max_messages <= 0:
            return True
        now = time.time()
        bucket = self.connection_windows.setdefault(id(connection), deque())
        bucket.append(now)
        threshold = now - window_seconds
        while bucket and bucket[0] < threshold:
            bucket.popleft()
        return len(bucket) <= max_messages

    def clear_cached_plugin_messages(self) -> None:
        self.latest_plugin_hello = ""
        self.cached_plugin_frames.clear()

    def cache_plugin_frame(self, raw_message: str, max_entries: int) -> None:
        if max_entries <= 0:
            return
        self.cached_plugin_frames.append(raw_message)
        while len(self.cached_plugin_frames) > max_entries:
            self.cached_plugin_frames.popleft()

    def replayable_plugin_frames(self) -> tuple[str, ...]:
        return tuple(self.cached_plugin_frames)

    def snapshot(self) -> dict[str, object]:
        plugin_connected = self.plugin is not None and not getattr(self.plugin, "closed", False)
        return {
            "session": self.session_id,
            "hasPlugin": plugin_connected,
            "phones": self.phone_count(),
            "ageSeconds": round(time.time() - self.created_at, 3),
            "hasHello": bool(self.latest_plugin_hello),
            "cachedPluginFrames": len(self.cached_plugin_frames),
            "ready": plugin_connected and bool(self.latest_plugin_hello),
            "waitingForPlugin": not plugin_connected,
            "admissionControlled": bool(self.admission_token),
            "secondsSincePluginDisconnect": (
                round(time.time() - self.last_plugin_disconnect_at, 3)
                if self.last_plugin_disconnect_at
                else None
            ),
        }
