# SPDX-FileCopyrightText: 2026 Bora Yarkın
# SPDX-License-Identifier: GPL-3.0-only

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

    def touch(self) -> None:
        self.last_seen = time.time()

    def empty(self) -> bool:
        return self.plugin is None and not self.phones
