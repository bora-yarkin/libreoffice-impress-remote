#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Bora Yarkın
# SPDX-License-Identifier: GPL-3.0-only

from __future__ import annotations

import argparse
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parent
for candidate in (ROOT, ROOT.parent, ROOT.parent.parent):
    if (candidate / "relay" / "__init__.py").exists() and str(candidate) not in sys.path:
        sys.path.insert(0, str(candidate))

from relay.__main__ import main as relay_main  # noqa: E402
from relay.runtime import ensure_runtime_config, load_runtime_config  # noqa: E402


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(prog="run-relay.py")
    parser.add_argument("--config", default=str(ROOT / "data" / "service.json"))
    parser.add_argument("--host-v4")
    parser.add_argument("--host-v6")
    parser.add_argument("--port", type=int)
    parser.add_argument("--session-ttl", type=int)
    parser.add_argument("--ensure-config-only", action="store_true")
    parser.add_argument("--print-port", action="store_true")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    config_path = Path(args.config).resolve()
    config = ensure_runtime_config(
        config_path,
        host_v4=args.host_v4,
        host_v6=args.host_v6,
        port=args.port,
        session_ttl=args.session_ttl,
    )
    if args.ensure_config_only:
        print(config_path)
        print(config.port)
        return
    if args.print_port:
        print(load_runtime_config(config_path).port)
        return

    relay_args = ["--config", str(config_path)]
    if args.host_v4 is not None:
        relay_args.extend(["--host-v4", args.host_v4])
    if args.host_v6 is not None:
        relay_args.extend(["--host-v6", args.host_v6])
    if args.port is not None:
        relay_args.extend(["--port", str(args.port)])
    if args.session_ttl is not None:
        relay_args.extend(["--session-ttl", str(args.session_ttl)])
    relay_main(relay_args)


if __name__ == "__main__":
    main()
