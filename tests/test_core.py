# SPDX-FileCopyrightText: 2026 Bora Yarkın
# SPDX-License-Identifier: GPL-3.0-only
# ruff: noqa: E402,F811

from __future__ import annotations

from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from impress_remote.config import (
    RemoteConfig,
    normalize_relay_url,
    relay_health_url,
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

    def test_relay_health_url_targets_health_endpoint(self) -> None:
        self.assertEqual(
            relay_health_url("wss://relay.example.com/base/ws"),
            "https://relay.example.com/base/health",
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

    def test_remote_config_defaults_unknown_route_to_local(self) -> None:
        config = RemoteConfig.from_dict({"preferredRoute": "surprise"})

        self.assertEqual(config.preferred_route, "local")


import pytest

from impress_remote.crypto import (
    aes_gcm_decrypt,
    aes_gcm_encrypt,
    base64url_decode,
    base64url_encode,
    hkdf_sha256,
    p256_generate_private_key,
    p256_public_key,
    p256_shared_secret,
    random_token,
)


def test_random_token_is_urlsafe() -> None:
    token = random_token()
    assert token
    assert "=" not in token


def test_hkdf_is_deterministic() -> None:
    first = hkdf_sha256(b"secret", b"salt", b"info")
    second = hkdf_sha256(b"secret", b"salt", b"info")
    assert first == second
    assert len(first) == 32


def test_base64url_round_trip_preserves_binary_data() -> None:
    payload = bytes(range(32))

    encoded = base64url_encode(payload)

    assert base64url_decode(encoded) == payload


def test_p256_ecdh_shared_secret_matches_between_peers() -> None:
    left_private = p256_generate_private_key()
    right_private = p256_generate_private_key()
    left_public = p256_public_key(left_private)
    right_public = p256_public_key(right_private)

    assert left_public[0] == 0x04
    assert right_public[0] == 0x04
    assert len(left_public) == 65
    assert p256_shared_secret(left_private, right_public) == p256_shared_secret(
        right_private,
        left_public,
    )


def test_aes_gcm_matches_known_nist_vector() -> None:
    key = bytes.fromhex("00000000000000000000000000000000")
    nonce = bytes.fromhex("000000000000000000000000")
    plaintext = bytes.fromhex("00000000000000000000000000000000")

    ciphertext, tag = aes_gcm_encrypt(key, nonce, plaintext)

    assert ciphertext.hex() == "0388dace60b6a392f328c2b971b2fe78"
    assert tag.hex() == "ab6e47d42cec13bdf53a67b21257bddf"
    assert aes_gcm_decrypt(key, nonce, ciphertext, tag) == plaintext


def test_aes_gcm_rejects_tampered_tags() -> None:
    key = bytes.fromhex("00000000000000000000000000000000")
    nonce = bytes.fromhex("000000000000000000000000")
    ciphertext, tag = aes_gcm_encrypt(key, nonce, b"hello")

    tampered = bytearray(tag)
    tampered[-1] ^= 0x01

    with pytest.raises(ValueError):
        aes_gcm_decrypt(key, nonce, ciphertext, bytes(tampered))


from impress_remote.localization import (
    DEFAULT_LOCALE,
    available_locales,
    localization_manifest,
    load_catalog,
    normalize_locale,
    translate,
)
from impress_remote.config import route_label


def test_loads_english_catalog() -> None:
    catalog = load_catalog(DEFAULT_LOCALE)

    assert catalog["component.menu.startRemote"] == "Start Remote"


def test_translates_turkish_catalog_for_testing() -> None:
    assert translate("component.menu.startRemote", language="tr") == "Kumandayi Baslat"


def test_falls_back_to_english_for_missing_turkish_key() -> None:
    assert translate("missing.key", language="tr") == "missing.key"
    assert translate("component.menu.stopRemote", language="tr") == "Kumandayi Durdur"


def test_normalizes_locale_codes() -> None:
    assert normalize_locale("tr_TR.UTF-8") == "tr"
    assert normalize_locale("en-US") == "en"
    assert normalize_locale("de_DE.UTF-8") == ""


def test_reports_available_locales_for_manifest_driven_clients() -> None:
    locales = available_locales()
    manifest = localization_manifest()

    assert DEFAULT_LOCALE in locales
    assert "tr" in locales
    assert manifest["defaultLocale"] == DEFAULT_LOCALE
    manifest_locales = manifest["locales"]
    assert isinstance(manifest_locales, list)
    assert "tr" in manifest_locales


def test_formats_localized_message_values() -> None:
    assert (
        translate(
            "component.status.slideOf",
            language="en",
            message="Ready",
            current=2,
            total=9,
        )
        == "Ready. Slide 2 of 9."
    )


def test_non_local_route_labels_are_marked_experimental() -> None:
    assert route_label("local") == "Local network"
    for route in ("tunnel", "ipv6", "relay"):
        assert "Experimental" in route_label(route)


from io import BytesIO
import json

import pytest

from impress_remote import localtunnel_client
from impress_remote.localtunnel_client import (
    LocalTunnelClient,
    LocalTunnelInfo,
    _request_tunnel_info,
    normalize_tunnel_host,
)


class FakeResponse:
    status = 200

    def __init__(self, payload: dict[str, object]) -> None:
        self.payload = payload

    def __enter__(self):
        return self

    def __exit__(self, *_args) -> None:
        return None

    def read(self) -> bytes:
        return json.dumps(self.payload).encode("utf-8")


def test_normalize_tunnel_host_defaults_to_https() -> None:
    assert normalize_tunnel_host("localtunnel.me") == "https://localtunnel.me"


def test_normalize_tunnel_host_rejects_unsupported_scheme() -> None:
    with pytest.raises(ValueError):
        normalize_tunnel_host("ftp://localtunnel.me")


def test_request_tunnel_info_uses_random_endpoint(monkeypatch) -> None:
    requested_urls: list[str] = []

    def fake_urlopen(url: str, timeout: float):
        requested_urls.append(url)
        assert timeout > 0
        return FakeResponse(
            {
                "id": "demo-tunnel",
                "url": "https://demo-tunnel.localtunnel.me",
                "port": 43210,
                "max_conn_count": 2,
            }
        )

    monkeypatch.setattr(localtunnel_client, "urlopen", fake_urlopen)

    info = _request_tunnel_info("https://localtunnel.me")

    assert requested_urls == ["https://localtunnel.me/?new"]
    assert info.name == "demo-tunnel"
    assert info.url == "https://demo-tunnel.localtunnel.me"
    assert info.remote_host == "localtunnel.me"
    assert info.remote_port == 43210
    assert info.max_connections == 2


def test_request_tunnel_info_uses_requested_subdomain(monkeypatch) -> None:
    requested_urls: list[str] = []

    def fake_urlopen(url: str, timeout: float):
        requested_urls.append(url)
        assert timeout > 0
        return FakeResponse(
            {
                "id": "slides-demo",
                "url": "https://slides-demo.localtunnel.me",
                "port": 43210,
            }
        )

    monkeypatch.setattr(localtunnel_client, "urlopen", fake_urlopen)

    info = _request_tunnel_info("https://localtunnel.me", "Slides-Demo")

    assert requested_urls == ["https://localtunnel.me/slides-demo"]
    assert info.name == "slides-demo"


def test_request_tunnel_info_rejects_invalid_payload(monkeypatch) -> None:
    class InvalidResponse:
        status = 200

        def __enter__(self):
            return self

        def __exit__(self, *_args) -> None:
            return None

        def read(self) -> bytes:
            return BytesIO(b"[]").read()

    monkeypatch.setattr(localtunnel_client, "urlopen", lambda *_args, **_kwargs: InvalidResponse())

    with pytest.raises(ConnectionError):
        _request_tunnel_info("https://localtunnel.me")


def test_localtunnel_client_retries_until_tunnel_info_is_available(monkeypatch) -> None:
    attempts = 0
    wait_calls: list[float] = []

    def fake_request(_host: str, _subdomain: str = "") -> LocalTunnelInfo:
        nonlocal attempts
        attempts += 1
        if attempts == 1:
            raise ConnectionError("temporary outage")
        return LocalTunnelInfo(
            name="demo",
            url="https://demo.localtunnel.me",
            remote_host="127.0.0.1",
            remote_port=1,
        )

    def fake_connection_loop(self, _info: LocalTunnelInfo) -> None:
        self._stop_event.set()

    monkeypatch.setattr(localtunnel_client, "_request_tunnel_info", fake_request)
    monkeypatch.setattr(LocalTunnelClient, "_connection_loop", fake_connection_loop)

    client = LocalTunnelClient(local_host="127.0.0.1", local_port=17865)
    original_wait = client._stop_event.wait

    def fake_wait(timeout: float | None = None) -> bool:
        if timeout is not None:
            wait_calls.append(timeout)
        return original_wait(0)

    monkeypatch.setattr(client._stop_event, "wait", fake_wait)
    client._run()

    assert attempts == 2
    assert client.status()["state"] == "stopped"
    assert wait_calls == [2.0, 2.0]


import unittest

from impress_remote.network import _filter_unique_ipv4, _filter_unique_ipv6, format_http_url


class NetworkTests(unittest.TestCase):
    def test_format_http_url_wraps_ipv6_literals(self) -> None:
        self.assertEqual(
            format_http_url("2606:4700:4700::1111", 17865, "demo"),
            "http://[2606:4700:4700::1111]:17865/#s=demo",
        )

    def test_filter_unique_ipv4_keeps_private_non_loopback_addresses(self) -> None:
        self.assertEqual(
            _filter_unique_ipv4(["127.0.0.1", "192.168.1.22", "10.0.0.7", "192.168.1.22"]),
            ["192.168.1.22", "10.0.0.7"],
        )

    def test_filter_unique_ipv6_keeps_only_global_ipv6_addresses(self) -> None:
        self.assertEqual(
            _filter_unique_ipv6(
                [
                    "::1",
                    "fe80::1%en0",
                    "fd12:3456:789a::12",
                    "2606:4700:4700::1111",
                    "2606:4700:4700::1111",
                ]
            ),
            ["2606:4700:4700::1111"],
        )


import unittest
from pathlib import Path

from impress_remote.paths import module_file_path


class PathTests(unittest.TestCase):
    def test_module_file_path_accepts_filesystem_path(self) -> None:
        path = module_file_path("/tmp/example.py")
        self.assertEqual(path, Path("/tmp/example.py").resolve())

    def test_module_file_path_accepts_file_url(self) -> None:
        path = module_file_path("file:///tmp/example.py")
        self.assertEqual(path, Path("/tmp/example.py").resolve())


import json
import unittest

from impress_remote.protocol import (
    RelayProtocolFailure,
    SecureRelayCodec,
    decode_command_payload,
    decode_error_message,
    decode_hello_message,
    decode_command_message,
    encode_error_message,
    encode_hello_message,
    encode_command_message,
    encode_state_message,
)


class ProtocolTests(unittest.TestCase):
    def test_encode_state_message_wraps_state_payload(self) -> None:
        payload = json.loads(encode_state_message({"running": True, "slideCount": 3}))
        self.assertEqual(payload["type"], "state")
        self.assertTrue(payload["state"]["running"])

    def test_command_message_round_trip_preserves_index(self) -> None:
        command = decode_command_message(encode_command_message("goto_slide", 4))
        self.assertIsNotNone(command)
        assert command is not None
        self.assertEqual(command.command, "goto_slide")
        self.assertEqual(command.index, 4)

    def test_decode_command_message_rejects_other_message_types(self) -> None:
        self.assertIsNone(decode_command_message('{"type":"state"}'))

    def test_hello_message_round_trip_preserves_key_metadata(self) -> None:
        plugin = SecureRelayCodec(
            role="plugin",
            session_id="demo",
            pairing_secret="6o2T5h1XXg3YbqfQ9F0P9v38dGrBvM8UuB8jv3j1fKQ",
        )
        raw = encode_hello_message(plugin.rotate_send_key())

        decoded = decode_hello_message(raw)

        self.assertIsNotNone(decoded)
        assert decoded is not None
        self.assertEqual(decoded.session_id, "demo")
        self.assertEqual(decoded.sender_role, "plugin")
        self.assertTrue(decoded.key_id)
        self.assertTrue(decoded.plugin_nonce)
        self.assertTrue(decoded.public_key)

    def test_error_message_round_trip_preserves_code_and_text(self) -> None:
        decoded = decode_error_message(encode_error_message("bad-frame", "Nope", "demo"))

        self.assertIsNotNone(decoded)
        assert decoded is not None
        self.assertEqual(decoded.code, "bad-frame")
        self.assertEqual(decoded.message, "Nope")
        self.assertEqual(decoded.session_id, "demo")

    def test_secure_codec_encrypts_state_and_commands_between_phone_and_plugin(self) -> None:
        pairing_secret = "6o2T5h1XXg3YbqfQ9F0P9v38dGrBvM8UuB8jv3j1fKQ"
        plugin = SecureRelayCodec(role="plugin", session_id="demo", pairing_secret=pairing_secret)
        phone = SecureRelayCodec(role="phone", session_id="demo", pairing_secret=pairing_secret)

        hello = plugin.rotate_send_key()
        phone_hello = phone.apply_hello(hello)
        self.assertIsNotNone(phone_hello)
        assert phone_hello is not None
        plugin.apply_hello(phone_hello)

        encoded_state = plugin.encode_state_frame({"running": True, "slideCount": 7})
        decoded_state = phone.decode_frame(encoded_state)

        self.assertIsNotNone(decoded_state)
        assert decoded_state is not None
        self.assertEqual(decoded_state.kind, "state")
        self.assertTrue(decoded_state.payload["running"])
        self.assertEqual(decoded_state.payload["slideCount"], 7)

        encoded_command = phone.encode_command_frame("goto_slide", 4)
        decoded_command = plugin.decode_frame(encoded_command)

        self.assertIsNotNone(decoded_command)
        assert decoded_command is not None
        command = decode_command_payload(decoded_command.payload)
        self.assertIsNotNone(command)
        assert command is not None
        self.assertEqual(command.command, "goto_slide")
        self.assertEqual(command.index, 4)

    def test_secure_codec_encrypts_asset_frames_between_plugin_and_phone(self) -> None:
        pairing_secret = "6o2T5h1XXg3YbqfQ9F0P9v38dGrBvM8UuB8jv3j1fKQ"
        plugin = SecureRelayCodec(role="plugin", session_id="demo", pairing_secret=pairing_secret)
        phone = SecureRelayCodec(role="phone", session_id="demo", pairing_secret=pairing_secret)

        phone_hello = phone.apply_hello(plugin.rotate_send_key())
        assert phone_hello is not None
        plugin.apply_hello(phone_hello)
        encoded_asset = plugin.encode_asset_frame(
            {
                "contentType": "image/png",
                "encoding": "base64url",
                "data": "abcd",
                "slot": "current",
            }
        )

        decoded_asset = phone.decode_frame(encoded_asset)

        self.assertIsNotNone(decoded_asset)
        assert decoded_asset is not None
        self.assertEqual(decoded_asset.kind, "asset")
        self.assertEqual(decoded_asset.payload["contentType"], "image/png")
        self.assertEqual(decoded_asset.payload["slot"], "current")

    def test_secure_codec_rejects_replayed_frames(self) -> None:
        pairing_secret = "6o2T5h1XXg3YbqfQ9F0P9v38dGrBvM8UuB8jv3j1fKQ"
        plugin = SecureRelayCodec(role="plugin", session_id="demo", pairing_secret=pairing_secret)
        phone = SecureRelayCodec(role="phone", session_id="demo", pairing_secret=pairing_secret)

        phone_hello = phone.apply_hello(plugin.rotate_send_key())
        assert phone_hello is not None
        plugin.apply_hello(phone_hello)
        encoded_state = plugin.encode_state_frame({"running": True})
        self.assertIsNotNone(phone.decode_frame(encoded_state))

        with self.assertRaises(RelayProtocolFailure):
            phone.decode_frame(encoded_state)

    def test_plugin_keeps_previous_receive_keys_during_rotation(self) -> None:
        pairing_secret = "6o2T5h1XXg3YbqfQ9F0P9v38dGrBvM8UuB8jv3j1fKQ"
        plugin = SecureRelayCodec(role="plugin", session_id="demo", pairing_secret=pairing_secret)
        phone = SecureRelayCodec(role="phone", session_id="demo", pairing_secret=pairing_secret)

        first = plugin.rotate_send_key()
        first_phone_hello = phone.apply_hello(first)
        assert first_phone_hello is not None
        plugin.apply_hello(first_phone_hello)
        old_command = phone.encode_command_frame("next_slide")

        second = plugin.rotate_send_key()
        second_phone_hello = phone.apply_hello(second)
        assert second_phone_hello is not None
        plugin.apply_hello(second_phone_hello)

        decoded = plugin.decode_frame(old_command)

        self.assertIsNotNone(decoded)
        assert decoded is not None
        command = decode_command_payload(decoded.payload)
        self.assertIsNotNone(command)
        assert command is not None
        self.assertEqual(command.command, "next_slide")

    def test_plugin_cannot_encrypt_before_phone_ecdh_response(self) -> None:
        pairing_secret = "6o2T5h1XXg3YbqfQ9F0P9v38dGrBvM8UuB8jv3j1fKQ"
        plugin = SecureRelayCodec(role="plugin", session_id="demo", pairing_secret=pairing_secret)

        plugin.rotate_send_key()

        with self.assertRaises(RelayProtocolFailure):
            plugin.encode_state_frame({"running": True})


from pathlib import Path
import tomllib

from impress_remote import __version__ as extension_version
from relay import __version__ as relay_version
from tools.release import read_project_version

ROOT = Path(__file__).resolve().parents[1]


def test_python_runtime_versions_come_from_root_version_file() -> None:
    version = read_project_version()

    assert extension_version == version
    assert relay_version == version


def test_pyproject_versions_are_dynamic() -> None:
    for path in (ROOT / "pyproject.toml", ROOT / "relay" / "pyproject.toml"):
        with path.open("rb") as handle:
            data = tomllib.load(handle)
        assert data["project"]["dynamic"] == ["version"]
        assert "version" not in data["project"]
