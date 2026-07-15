# SPDX-FileCopyrightText: 2026 Bora Yarkın
# SPDX-License-Identifier: GPL-3.0-only

import unittest
from typing import cast

from types import SimpleNamespace

from impress_remote.local_server import RemoteServer, _url_with_fragment_params


class PairingServerStub:
    route_urls = RemoteServer.route_urls
    preview_route_urls = RemoteServer.preview_route_urls
    pairing_target = RemoteServer.pairing_target
    preview_pairing_target = RemoteServer.preview_pairing_target
    console_url = RemoteServer.console_url
    _pairing_hint = RemoteServer._pairing_hint
    _network_settings = RemoteServer._network_settings

    def __init__(
        self,
        *,
        running: bool = True,
        local_urls: list[str] | None = None,
        direct_urls: list[str] | None = None,
        enable_relay: bool = False,
        relay_url: str = "",
        preferred_route: str = "auto",
        enable_local_listener: bool = True,
        enable_ipv6_direct: bool = True,
        local_port: int = 17865,
    ) -> None:
        self._running = running
        self.http_servers = [object()] if running else []
        self.local_urls = local_urls or []
        self.direct_urls = direct_urls or []
        self.session_id = "demo123"
        self.url = ""
        self.config = SimpleNamespace(
            local_port=local_port,
            enable_relay=enable_relay,
            relay_url=relay_url,
            preferred_route=preferred_route,
            enable_local_listener=enable_local_listener,
            enable_ipv6_direct=enable_ipv6_direct,
        )
        self._active_network_settings = (
            local_port,
            enable_local_listener,
            enable_ipv6_direct,
        )

    def is_running(self) -> bool:
        return self._running


class LocalServerTests(unittest.TestCase):
    def test_url_with_fragment_params_preserves_existing_fragment_values(self) -> None:
        self.assertEqual(
            _url_with_fragment_params(
                "http://127.0.0.1:17865/#s=demo123",
                view="settings",
            ),
            "http://127.0.0.1:17865/#s=demo123&view=settings",
        )

    def test_url_with_fragment_params_replaces_existing_values(self) -> None:
        self.assertEqual(
            _url_with_fragment_params(
                "http://127.0.0.1:17865/#s=demo123&view=console",
                view="settings",
            ),
            "http://127.0.0.1:17865/#s=demo123&view=settings",
        )

    def test_current_slide_image_url_is_empty_without_an_impress_slide(self) -> None:
        state = SimpleNamespace(document_kind="none", slide_count=0, current_render_token="")
        server = cast(RemoteServer, SimpleNamespace(controller=None))

        self.assertEqual(
            RemoteServer.current_slide_image_url(server, state),
            "",
        )

    def test_current_slide_image_url_uses_the_render_token(self) -> None:
        state = SimpleNamespace(
            document_kind="impress",
            slide_count=8,
            current_render_token="current123",
        )
        server = cast(RemoteServer, SimpleNamespace(controller=None))

        self.assertEqual(
            RemoteServer.current_slide_image_url(server, state),
            "/api/slide/current?rev=current123",
        )

    def test_next_slide_image_url_is_empty_without_a_next_slide(self) -> None:
        state = SimpleNamespace(next_slide=None, next_render_token="")
        server = cast(RemoteServer, SimpleNamespace(controller=None))

        self.assertEqual(
            RemoteServer.next_slide_image_url(server, state),
            "",
        )

    def test_next_slide_image_url_uses_the_render_token(self) -> None:
        state = SimpleNamespace(next_slide=3, next_render_token="next456")
        server = cast(RemoteServer, SimpleNamespace(controller=None))

        self.assertEqual(
            RemoteServer.next_slide_image_url(server, state),
            "/api/slide/next?rev=next456",
        )

    def test_pairing_target_prefers_local_route_for_auto_mode(self) -> None:
        server = PairingServerStub(
            local_urls=["http://192.168.1.20:17865/#s=demo123"],
            direct_urls=["http://[2001:db8::1]:17865/#s=demo123"],
            enable_relay=True,
            relay_url="https://relay.example.com",
        )

        pairing = server.pairing_target("auto")

        self.assertEqual(pairing["requestedRoute"], "auto")
        self.assertEqual(pairing["selectedRoute"], "local")
        self.assertEqual(pairing["selectedUrl"], "http://192.168.1.20:17865/#s=demo123")

    def test_pairing_target_falls_back_to_relay_in_auto_mode(self) -> None:
        server = PairingServerStub(
            local_urls=[],
            direct_urls=[],
            enable_relay=True,
            relay_url="https://relay.example.com/base",
        )

        pairing = server.pairing_target("auto")

        self.assertEqual(pairing["selectedRoute"], "relay")
        self.assertEqual(pairing["selectedUrl"], "https://relay.example.com/base#mode=relay&s=demo123")

    def test_pairing_target_hides_local_route_when_local_listener_is_disabled(self) -> None:
        server = PairingServerStub(
            local_urls=["http://192.168.1.20:17865/#s=demo123"],
            direct_urls=["http://[2001:db8::1]:17865/#s=demo123"],
            enable_relay=True,
            relay_url="https://relay.example.com/base",
            enable_local_listener=False,
        )

        pairing = server.pairing_target("local")

        self.assertEqual(pairing["selectedUrl"], "")
        self.assertIn("disabled", pairing["hint"])

    def test_console_url_falls_back_to_auto_when_manual_route_is_unavailable(self) -> None:
        server = PairingServerStub(
            local_urls=["http://192.168.1.20:17865/#s=demo123"],
            direct_urls=[],
            enable_relay=False,
            relay_url="",
            preferred_route="ipv6",
        )

        self.assertEqual(server.console_url(), "http://192.168.1.20:17865/#s=demo123")


if __name__ == "__main__":
    unittest.main()
