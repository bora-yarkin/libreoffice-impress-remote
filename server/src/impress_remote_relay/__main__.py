# SPDX-FileCopyrightText: 2026 Bora Yarkın
# SPDX-License-Identifier: GPL-3.0-only

from __future__ import annotations

import argparse
import asyncio

from aiohttp import web

from impress_remote_relay.relay import RelayState, create_app


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(prog="impress-remote-relay")
    parser.add_argument("--host-v4", default="0.0.0.0")
    parser.add_argument("--host-v6", default="::")
    parser.add_argument("--port", type=int, default=8080)
    parser.add_argument("--session-ttl", type=int, default=3600)
    return parser.parse_args()


async def run() -> None:
    args = parse_args()
    app = create_app(RelayState(session_ttl=args.session_ttl))
    runner = web.AppRunner(app)
    await runner.setup()
    sites = []
    for host in (args.host_v4, args.host_v6):
        if not host:
            continue
        site = web.TCPSite(runner, host=host, port=args.port)
        try:
            await site.start()
        except OSError as exc:
            print(f"Could not bind {host}:{args.port}: {exc}")
            continue
        sites.append(site)
        print(f"Listening on {host}:{args.port}")
    if not sites:
        raise SystemExit("No listen sockets could be opened")
    await asyncio.Event().wait()


def main() -> None:
    try:
        asyncio.run(run())
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
