# SPDX-FileCopyrightText: 2026 Bora Yarkın
# SPDX-License-Identifier: GPL-3.0-only

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
