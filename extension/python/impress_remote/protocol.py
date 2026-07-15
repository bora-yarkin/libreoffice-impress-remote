# SPDX-FileCopyrightText: 2026 Bora Yarkın
# SPDX-License-Identifier: GPL-3.0-only

from __future__ import annotations

from dataclasses import dataclass
import json
from typing import Any


@dataclass(frozen=True)
class RelayCommand:
    command: str
    index: int | None = None


def encode_state_message(state: dict[str, object]) -> str:
    return json.dumps({"type": "state", "state": state}, separators=(",", ":"))


def encode_command_message(command: str, index: int | None = None) -> str:
    payload: dict[str, Any] = {"type": "command", "command": command}
    if index is not None:
        payload["index"] = index
    return json.dumps(payload, separators=(",", ":"))


def decode_command_message(raw: str) -> RelayCommand | None:
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError:
        return None

    if payload.get("type") != "command":
        return None

    command = payload.get("command")
    if not isinstance(command, str) or not command:
        return None

    index = payload.get("index")
    if index is not None:
        try:
            index = int(index)
        except (TypeError, ValueError):
            index = None
    return RelayCommand(command=command, index=index)
