# SPDX-FileCopyrightText: 2026 Bora Yarkın
# SPDX-License-Identifier: GPL-3.0-only

from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from impress_remote.config import (
    RemoteConfig,
    normalize_relay_url,
    relay_join_url,
    relay_websocket_url,
)


class ConfigTests(unittest.TestCase):
    def test_normalize_relay_url_defaults_to_https_for_public_hosts(self) -> None:
        self.assertEqual(
            normalize_relay_url("relay.example.com"),
            "https://relay.example.com",
        )

    def test_normalize_relay_url_defaults_to_http_for_local_hosts(self) -> None:
        self.assertEqual(
            normalize_relay_url("127.0.0.1:8080"),
            "http://127.0.0.1:8080",
        )

    def test_relay_websocket_url_appends_ws_and_query(self) -> None:
        self.assertEqual(
            relay_websocket_url("https://relay.example.com/base", "demo"),
            "wss://relay.example.com/base/ws?role=plugin&session=demo",
        )

    def test_relay_join_url_builds_a_shareable_phone_link(self) -> None:
        self.assertEqual(
            relay_join_url("wss://relay.example.com/base/ws", "demo"),
            "https://relay.example.com/base#mode=relay&s=demo",
        )

    def test_remote_config_round_trips_to_disk(self) -> None:
        config = RemoteConfig(
            local_port=19001,
            relay_url="https://relay.example.com",
            enable_relay=True,
            enable_ipv6_direct=False,
            preferred_route="relay",
        )

        with TemporaryDirectory() as tmp:
            base_dir = Path(tmp)
            config.save(base_dir=base_dir)
            loaded = RemoteConfig.load(base_dir=base_dir)

        self.assertEqual(config, loaded)

    def test_remote_config_defaults_unknown_route_to_auto(self) -> None:
        config = RemoteConfig.from_dict({"preferredRoute": "surprise"})

        self.assertEqual(config.preferred_route, "auto")
