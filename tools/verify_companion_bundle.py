# SPDX-FileCopyrightText: 2026 Bora Yarkın
# SPDX-License-Identifier: GPL-3.0-only

"""Launch and exercise the locally built companion bundle."""

from __future__ import annotations

import json
import os
from pathlib import Path
import re
import subprocess
import sys
from tempfile import TemporaryFile
from time import monotonic, sleep
from typing import BinaryIO
from http.client import HTTPResponse
from urllib.error import HTTPError, URLError
from urllib.request import ProxyHandler, Request, build_opener

ROOT = Path(__file__).resolve().parents[1]
APP_NAME = "impress-remote-companion"
STARTUP_TIMEOUT_SECONDS = 15
SHUTDOWN_TIMEOUT_SECONDS = 10
HTTP_TIMEOUT_SECONDS = 5
SETUP_URL_PATTERN = re.compile(r"Open the local setup page: (http://127\.0\.0\.1:\d+/)")
LOCAL_HTTP_OPENER = build_opener(ProxyHandler({}))


def _executable_path() -> Path:
    executable_name = f"{APP_NAME}.exe" if os.name == "nt" else APP_NAME
    return ROOT / "dist" / "companion" / APP_NAME / executable_name


def _wait_for_setup_url(process: subprocess.Popen[bytes], output: BinaryIO) -> str:
    deadline = monotonic() + STARTUP_TIMEOUT_SECONDS
    while monotonic() < deadline:
        output.seek(0)
        content = output.read().decode("utf-8", errors="replace")
        match = SETUP_URL_PATTERN.search(content)
        if match:
            return match.group(1)
        if process.poll() is not None:
            details = content.strip() or "The companion wrote no startup diagnostics."
            raise RuntimeError(
                f"Companion exited before startup (status {process.returncode}): {details}"
            )
        sleep(0.05)
    raise TimeoutError("Companion did not print its local setup address in time.")


def _request(
    url: str,
    *,
    method: str = "GET",
    headers: dict[str, str] | None = None,
) -> HTTPResponse | HTTPError:
    request = Request(
        url,
        data=b"" if method == "POST" else None,
        headers=headers or {},
        method=method,
    )
    try:
        return LOCAL_HTTP_OPENER.open(request, timeout=HTTP_TIMEOUT_SECONDS)
    except HTTPError as error:
        return error


def _verify_http_surface(origin: str) -> None:
    expected_resources = {
        "/": "text/html",
        "/app.css": "text/css",
        "/app.js": "text/javascript",
        "/localizations/en.json": "application/json",
        "/localizations/tr.json": "application/json",
    }
    for path, media_type in expected_resources.items():
        with _request(f"{origin}{path}") as response:
            content = response.read()
            if response.status != 200 or media_type not in response.headers.get("Content-Type", ""):
                raise RuntimeError(f"Packaged resource {path} returned an unexpected response.")
            if not content:
                raise RuntimeError(f"Packaged resource {path} is empty.")

    with _request(
        f"{origin}/api/session",
        headers={"Host": "localhost"},
    ) as wrong_host:
        if wrong_host.status != 421:
            raise RuntimeError("Companion accepted an unexpected Host header.")

    with _request(
        f"{origin}/api/session",
        headers={"Origin": "http://localhost"},
    ) as response:
        if response.headers.get("Access-Control-Allow-Origin") is not None:
            raise RuntimeError("Companion enabled cross-origin access to its local API.")
        session = json.loads(response.read())
    if not isinstance(session, dict):
        raise RuntimeError("Companion returned an invalid session response.")
    token = session.get("shutdownToken")
    if not isinstance(token, str) or not token:
        raise RuntimeError("Companion did not return a shutdown token.")

    common_headers = {"Origin": origin}
    with _request(
        f"{origin}/api/shutdown",
        method="POST",
        headers={**common_headers, "X-Companion-Token": "invalid-token"},
    ) as rejected:
        if rejected.status != 403:
            raise RuntimeError("Companion accepted an invalid shutdown token.")

    with _request(
        f"{origin}/api/shutdown",
        method="POST",
        headers={"Origin": "http://localhost", "X-Companion-Token": token},
    ) as wrong_origin:
        if wrong_origin.status != 403:
            raise RuntimeError("Companion accepted an unexpected Origin header.")

    with _request(
        f"{origin}/api/shutdown",
        method="POST",
        headers={**common_headers, "X-Companion-Token": token},
    ) as accepted:
        if accepted.status != 202:
            raise RuntimeError("Companion rejected the valid same-origin shutdown request.")


def main() -> int:
    executable = _executable_path()
    if not executable.is_file():
        print(f"Companion bundle executable not found: {executable}", file=sys.stderr)
        return 1

    with TemporaryFile(mode="w+b") as output:
        process = subprocess.Popen(
            [str(executable), "--no-browser"],
            cwd=ROOT,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=output,
        )
        try:
            setup_url = _wait_for_setup_url(process, output)
            _verify_http_surface(setup_url.rstrip("/"))
            status = process.wait(timeout=SHUTDOWN_TIMEOUT_SECONDS)
            if status != 0:
                raise RuntimeError(f"Companion exited with status {status} after shutdown.")
        except (OSError, TimeoutError, URLError, RuntimeError, json.JSONDecodeError) as error:
            print(f"Companion bundle verification failed: {error}", file=sys.stderr)
            return 1
        finally:
            if process.poll() is None:
                process.terminate()
                try:
                    process.wait(timeout=SHUTDOWN_TIMEOUT_SECONDS)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait()

    print(
        "Companion bundle started, served its packaged assets, "
        "rejected an invalid token, and shut down."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
