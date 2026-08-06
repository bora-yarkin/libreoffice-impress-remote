# SPDX-FileCopyrightText: 2026 Bora Yarkın
# SPDX-License-Identifier: GPL-3.0-only

"""Discover usable local and public IPv6 addresses for pairing links.

Only addresses that can plausibly be reached by the phone are returned:
loopback, unspecified, multicast, and non-private IPv4 addresses are
discarded, while direct IPv6 requires a global address.
"""

from __future__ import annotations

from collections.abc import Iterable
import ipaddress
import socket


def format_http_url(host: str, port: int, session_id: str) -> str:
    """Format a session URL, bracket-quoting IPv6 literals when necessary."""
    literal = host
    if ":" in host and not host.startswith("["):
        literal = f"[{host}]"
    return f"http://{literal}:{port}/#s={session_id}"


def discover_local_urls(port: int, session_id: str) -> list[str]:
    """Return pairing URLs for reachable private IPv4 addresses."""
    addresses = _discover_ipv4_addresses()
    if not addresses:
        addresses = ["127.0.0.1"]
    return [format_http_url(address, port, session_id) for address in addresses]


def discover_direct_ipv6_addresses() -> list[str]:
    """Return globally routable IPv6 addresses suitable for direct pairing."""
    return _discover_ipv6_addresses()


def _discover_ipv4_addresses() -> list[str]:
    """Collect and filter candidate IPv4 addresses from routes and hostnames."""
    discovered = _preferred_source_addresses(socket.AF_INET, ("192.0.2.1", 80))
    discovered.extend(_hostname_addresses(socket.AF_INET))
    return _filter_unique_ipv4(discovered)


def _discover_ipv6_addresses() -> list[str]:
    """Collect and filter candidate IPv6 addresses from routes and hostnames."""
    discovered = _preferred_source_addresses(socket.AF_INET6, ("2001:db8::1", 80, 0, 0))
    discovered.extend(_hostname_addresses(socket.AF_INET6))
    return _filter_unique_ipv6(discovered)


def probe_ipv6_listener(address: str, port: int, timeout: float = 0.35) -> bool:
    """Probe whether an IPv6 listener accepts connections at *address* and *port*."""
    target = _normalize_ipv6(address)
    try:
        with socket.create_connection((target, port), timeout=timeout):
            return True
    except OSError:
        return False


def _preferred_source_addresses(family: int, remote) -> list[str]:
    """Discover the local source address selected for a route to *remote*."""
    try:
        with socket.socket(family, socket.SOCK_DGRAM) as sock:
            sock.connect(remote)
            address = sock.getsockname()[0]
            return [address]
    except OSError:
        return []


def _hostname_addresses(family: int) -> list[str]:
    """Resolve local hostnames into candidate addresses for one address family."""
    names = [socket.gethostname(), socket.getfqdn(), "localhost"]
    addresses: list[str] = []
    for name in names:
        try:
            infos = socket.getaddrinfo(name, None, family, socket.SOCK_STREAM)
        except OSError:
            continue
        for info in infos:
            if not info[4]:
                continue
            host = info[4][0]
            if isinstance(host, str):
                addresses.append(host)
    return addresses


def _normalize_ipv6(address: str) -> str:
    """Remove a zone identifier from an IPv6 link-local notation."""
    return address.split("%", 1)[0]


def _filter_unique_ipv4(addresses: Iterable[str]) -> list[str]:
    """Keep unique private IPv4 addresses that a phone may reach."""
    filtered: list[str] = []
    seen = set()
    for address in addresses:
        try:
            parsed = ipaddress.ip_address(address)
        except ValueError:
            continue
        if (
            parsed.version != 4
            or parsed.is_loopback
            or parsed.is_unspecified
            or parsed.is_multicast
            or not parsed.is_private
        ):
            continue
        value = str(parsed)
        if value not in seen:
            seen.add(value)
            filtered.append(value)
    return filtered


def _filter_unique_ipv6(addresses: Iterable[str]) -> list[str]:
    """Keep unique global IPv6 addresses suitable for direct pairing."""
    filtered: list[str] = []
    seen = set()
    for address in addresses:
        normalized = _normalize_ipv6(address)
        try:
            parsed = ipaddress.ip_address(normalized)
        except ValueError:
            continue
        if (
            parsed.version != 6
            or parsed.is_loopback
            or parsed.is_unspecified
            or parsed.is_multicast
            or parsed.is_link_local
            or not parsed.is_global
        ):
            continue
        value = str(parsed)
        if value not in seen:
            seen.add(value)
            filtered.append(value)
    return filtered
