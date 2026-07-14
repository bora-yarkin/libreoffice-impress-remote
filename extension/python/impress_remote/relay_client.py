# SPDX-FileCopyrightText: 2026 Bora Yarkın
# SPDX-License-Identifier: GPL-3.0-only

from __future__ import annotations


class RelayClient:
    def __init__(self, relay_url: str, session_id: str):
        self.relay_url = relay_url
        self.session_id = session_id

    def start(self) -> None:
        raise NotImplementedError("Relay client transport is planned for the next milestone")
