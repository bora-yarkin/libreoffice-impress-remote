# SPDX-FileCopyrightText: 2026 Bora Yarkın
# SPDX-License-Identifier: GPL-3.0-only

"""Start the local control page and wait for a clean shutdown request."""

from __future__ import annotations

import argparse
import sys
import webbrowser
from collections.abc import Sequence

from .control_server import LocalControlServer, create_local_control_server


def _open_setup_page(url: str) -> bool:
    try:
        return webbrowser.open(url, new=2)
    except (OSError, webbrowser.Error):
        return False


def run(server: LocalControlServer, *, open_browser: bool = True) -> int:
    """Serve requests until the page requests shutdown or the user interrupts."""
    interrupted = False
    try:
        print("Impress Remote Companion is running.", file=sys.stderr)
        setup_url = f"{server.origin}/"
        if not open_browser or not _open_setup_page(setup_url):
            print(f"Open the local setup page: {setup_url}", file=sys.stderr)
        while not server.shutdown_requested:
            server.handle_request()
    except KeyboardInterrupt:
        interrupted = True
    except OSError as exc:
        print(f"The companion stopped unexpectedly: {exc}", file=sys.stderr)
        return 1
    finally:
        server.server_close()

    return 130 if interrupted else 0


def main(argv: Sequence[str] | None = None) -> int:
    """Create the loopback service and open its local setup page."""
    parser = argparse.ArgumentParser(description="Run the Impress Remote companion.")
    parser.add_argument(
        "--no-browser",
        action="store_true",
        help="print the local setup page address without opening a browser",
    )
    args = parser.parse_args(argv)

    try:
        server = create_local_control_server()
    except OSError as exc:
        print(f"Unable to start the companion: {exc}", file=sys.stderr)
        return 1
    return run(server, open_browser=not args.no_browser)
