# SPDX-FileCopyrightText: 2026 Bora Yarkın
# SPDX-License-Identifier: GPL-3.0-only

from __future__ import annotations

import argparse
import asyncio
import logging
from pathlib import Path

from aiohttp import web

from impress_remote_relay.localization import translate
from impress_remote_relay.relay import RelayState, create_app
from impress_remote_relay.runtime import (
    DEFAULT_HOST_V4,
    DEFAULT_HOST_V6,
    DEFAULT_SESSION_TTL,
    RelayRuntimeConfig,
    load_runtime_config,
)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(prog="impress-remote-relay")
    parser.add_argument("--config")
    parser.add_argument("--host-v4")
    parser.add_argument("--host-v6")
    parser.add_argument("--port", type=int)
    parser.add_argument("--session-ttl", type=int)
    parser.add_argument("--log-level", default="INFO")
    return parser.parse_args(argv)


def runtime_config_from_args(args: argparse.Namespace) -> RelayRuntimeConfig:
    config = RelayRuntimeConfig(
        host_v4=DEFAULT_HOST_V4,
        host_v6=DEFAULT_HOST_V6,
        port=8080,
        session_ttl=DEFAULT_SESSION_TTL,
    )
    if args.config:
        config = load_runtime_config(Path(args.config))
    return RelayRuntimeConfig(
        host_v4=args.host_v4 if args.host_v4 is not None else config.host_v4,
        host_v6=args.host_v6 if args.host_v6 is not None else config.host_v6,
        port=args.port if args.port is not None else config.port,
        session_ttl=(
            args.session_ttl if args.session_ttl is not None else config.session_ttl
        ),
    )


async def run(argv: list[str] | None = None) -> None:
    args = parse_args(argv)
    logging.basicConfig(
        level=getattr(logging, str(args.log_level).upper(), logging.INFO),
        format="%(message)s",
    )
    config = runtime_config_from_args(args)
    app = create_app(RelayState(session_ttl=config.session_ttl))
    runner = web.AppRunner(app)
    await runner.setup()
    sites = []
    for host in (config.host_v4, config.host_v6):
        if not host:
            continue
        site = web.TCPSite(runner, host=host, port=config.port)
        try:
            await site.start()
        except OSError as exc:
            print(translate("relay.cli.bindFailed", host=host, port=config.port, error=exc))
            continue
        sites.append(site)
        print(translate("relay.cli.listening", host=host, port=config.port))
    if not sites:
        raise SystemExit(translate("relay.error.noListenSockets"))
    await asyncio.Event().wait()


def main(argv: list[str] | None = None) -> None:
    try:
        asyncio.run(run(argv))
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
