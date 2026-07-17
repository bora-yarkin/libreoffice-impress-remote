# SPDX-FileCopyrightText: 2026 Bora Yarkın
# SPDX-License-Identifier: GPL-3.0-only

from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from impress_remote.config import (
    RemoteConfig,
    normalize_relay_url,
    relay_join_url,
    relay_session_status_url,
    relay_websocket_url,
)


class FakeOfficeConfigAccess:
    def __init__(self, values: dict[str, object]) -> None:
        self.values = values
        self.committed = False

    def getPropertyValue(self, name: str) -> object:
        if name not in self.values:
            raise KeyError(name)
        return self.values[name]

    def setPropertyValue(self, name: str, value: object) -> None:
        self.values[name] = value

    def commitChanges(self) -> None:
        self.committed = True


class FakeOfficeConfigProvider:
    def __init__(self) -> None:
        self.values: dict[str, object] = {}
        self.last_access: FakeOfficeConfigAccess | None = None
        self.last_update_access: FakeOfficeConfigAccess | None = None

    def createInstanceWithArguments(self, service_name: str, _arguments) -> FakeOfficeConfigAccess:
        self.last_access = FakeOfficeConfigAccess(self.values)
        if service_name == "com.sun.star.configuration.ConfigurationUpdateAccess":
            self.last_update_access = self.last_access
        return self.last_access


class FakeServiceManager:
    def __init__(self) -> None:
        self.provider = FakeOfficeConfigProvider()

    def createInstanceWithContext(self, service_name: str, _ctx):
        if service_name == "com.sun.star.configuration.ConfigurationProvider":
            return self.provider
        raise AssertionError(f"Unexpected service request: {service_name}")


class FakeComponentContext:
    def __init__(self) -> None:
        self.ServiceManager = FakeServiceManager()


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

    def test_relay_websocket_url_can_embed_admission_token(self) -> None:
        self.assertEqual(
            relay_websocket_url(
                "https://relay.example.com/base",
                "demo",
                role="phone",
                admission_token="join-token",
            ),
            "wss://relay.example.com/base/ws?role=phone&session=demo&a=join-token",
        )

    def test_relay_join_url_builds_a_shareable_phone_link(self) -> None:
        self.assertEqual(
            relay_join_url("wss://relay.example.com/base/ws", "demo"),
            "https://relay.example.com/base#mode=relay&s=demo",
        )

    def test_relay_join_url_can_embed_pairing_secret_in_fragment(self) -> None:
        self.assertEqual(
            relay_join_url("wss://relay.example.com/base/ws", "demo", "pairsecret"),
            "https://relay.example.com/base#mode=relay&s=demo&k=pairsecret",
        )

    def test_relay_join_url_can_embed_admission_token_in_fragment(self) -> None:
        self.assertEqual(
            relay_join_url(
                "wss://relay.example.com/base/ws",
                "demo",
                "pairsecret",
                "join-token",
            ),
            "https://relay.example.com/base#mode=relay&s=demo&k=pairsecret&a=join-token",
        )

    def test_relay_session_status_url_targets_api_endpoint(self) -> None:
        self.assertEqual(
            relay_session_status_url(
                "wss://relay.example.com/base/ws",
                "demo",
                "join-token",
            ),
            "https://relay.example.com/base/api/session?session=demo&a=join-token",
        )

    def test_remote_config_round_trips_to_disk(self) -> None:
        config = RemoteConfig(
            local_port=19001,
            relay_url="https://relay.example.com",
            enable_relay=True,
            enable_ipv6_direct=False,
            enable_local_listener=False,
            preferred_route="relay",
        )

        with TemporaryDirectory() as tmp:
            base_dir = Path(tmp)
            config.save(base_dir=base_dir)
            loaded = RemoteConfig.load(base_dir=base_dir)

        self.assertEqual(config, loaded)

    def test_remote_config_round_trips_to_libreoffice_configuration(self) -> None:
        ctx = FakeComponentContext()
        config = RemoteConfig(
            local_port=19001,
            relay_url="https://relay.example.com",
            enable_relay=True,
            enable_ipv6_direct=False,
            enable_local_listener=False,
            preferred_route="relay",
        )

        config.save(ctx=ctx)
        loaded = RemoteConfig.load(ctx=ctx)

        self.assertEqual(config, loaded)
        access = ctx.ServiceManager.provider.last_update_access
        self.assertIsNotNone(access)
        assert access is not None
        self.assertTrue(access.committed)

    def test_remote_config_defaults_unknown_route_to_auto(self) -> None:
        config = RemoteConfig.from_dict({"preferredRoute": "surprise"})

        self.assertEqual(config.preferred_route, "auto")
