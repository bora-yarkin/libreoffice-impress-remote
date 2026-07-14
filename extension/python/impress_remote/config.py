# SPDX-FileCopyrightText: 2026 Bora Yarkın
# SPDX-License-Identifier: GPL-3.0-only

from dataclasses import dataclass


@dataclass(frozen=True)
class RemoteConfig:
    local_host: str = "0.0.0.0"
    local_port: int = 17865
    relay_url: str = ""
    enable_relay: bool = False
    enable_ipv6_direct: bool = True
