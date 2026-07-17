# SPDX-FileCopyrightText: 2026 Bora Yarkın
# SPDX-License-Identifier: GPL-3.0-only

from collections import deque
from dataclasses import dataclass, field
import time
from typing import Any


@dataclass
class RelaySession:
    session_id: str
    created_at: float = field(default_factory=time.time)
    last_seen: float = field(default_factory=time.time)
    plugin: Any | None = None
    phones: set[Any] = field(default_factory=set)
    latest_plugin_hello: str = ""
    cached_plugin_frames: deque[str] = field(default_factory=deque)

    def touch(self) -> None:
        self.last_seen = time.time()

    def empty(self) -> bool:
        return self.plugin is None and not self.phones

    def phone_count(self) -> int:
        return len([phone for phone in self.phones if not getattr(phone, "closed", False)])

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
        return {
            "session": self.session_id,
            "hasPlugin": self.plugin is not None and not getattr(self.plugin, "closed", False),
            "phones": self.phone_count(),
            "ageSeconds": round(time.time() - self.created_at, 3),
            "hasHello": bool(self.latest_plugin_hello),
            "cachedPluginFrames": len(self.cached_plugin_frames),
        }
