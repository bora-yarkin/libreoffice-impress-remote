# SPDX-FileCopyrightText: 2026 Bora Yarkın
# SPDX-License-Identifier: GPL-3.0-only

from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from typing import Any
from urllib.error import HTTPError
from urllib.parse import urlencode, urljoin
from urllib.request import urlopen


class RelayCompatibilityError(RuntimeError):
    pass


@dataclass(frozen=True)
class CheckResult:
    name: str
    ok: bool
    detail: str


def read_json(url: str) -> tuple[int, dict[str, Any]]:
    try:
        with urlopen(url, timeout=5) as response:
            status = response.status
            raw = response.read().decode("utf-8")
    except HTTPError as exc:
        status = exc.code
        raw = exc.read().decode("utf-8", errors="replace")
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError:
        payload = {}
    return status, payload if isinstance(payload, dict) else {}


def require(condition: bool, message: str) -> None:
    if not condition:
        raise RelayCompatibilityError(message)


def check_health(base_url: str) -> CheckResult:
    status, payload = read_json(urljoin(base_url, "/health"))
    require(status == 200, f"expected 200, got {status}")
    require(isinstance(payload.get("ok"), bool), "health payload must include boolean ok")
    return CheckResult("health", True, "health endpoint returned JSON status")


def check_asset_manifest(base_url: str) -> CheckResult:
    status, payload = read_json(urljoin(base_url, "/asset-manifest.json"))
    require(status == 200, f"expected 200, got {status}")
    files = payload.get("files")
    require(isinstance(files, dict), "asset manifest must include files object")
    if not isinstance(files, dict):
        raise AssertionError("unreachable: require() rejected non-dict files")
    for name in ("index.html", "app.js", "app.css", "localizations/manifest.json"):
        require(name in files, f"asset manifest missing {name}")
    return CheckResult("asset-manifest", True, "asset manifest exposes required web assets")


def check_localization_manifest(base_url: str) -> CheckResult:
    status, payload = read_json(urljoin(base_url, "/localizations/manifest.json"))
    require(status == 200, f"expected 200, got {status}")
    require(payload.get("defaultLocale") == "en", "defaultLocale must be en")
    locales = payload.get("locales")
    require(isinstance(locales, list) and "en" in locales, "locales must include en")
    return CheckResult("localization-manifest", True, "localization manifest is available")


def check_session_status_auth(base_url: str, session: str, admission_token: str) -> CheckResult:
    query = urlencode({"session": session, "a": admission_token})
    status, _payload = read_json(urljoin(base_url, f"/api/session?{query}"))
    require(status in {200, 403, 404}, f"expected 200/403/404, got {status}")
    return CheckResult(
        "session-status",
        True,
        "session-status endpoint exists and returns a protocol-compatible status",
    )


def run_checks(base_url: str, *, session: str, admission_token: str) -> tuple[CheckResult, ...]:
    normalized = base_url.rstrip("/") + "/"
    checks = (
        lambda: check_health(normalized),
        lambda: check_asset_manifest(normalized),
        lambda: check_localization_manifest(normalized),
        lambda: check_session_status_auth(normalized, session, admission_token),
    )
    results: list[CheckResult] = []
    for check in checks:
        results.append(check())
    return tuple(results)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Validate a relay server against the public Impress Remote relay contract.",
    )
    parser.add_argument("relay_url", help="Relay base URL, for example https://relay.example.com")
    parser.add_argument("--session", default="compatcheck", help="Session id probe value.")
    parser.add_argument("--admission-token", default="invalid", help="Admission token probe value.")
    args = parser.parse_args()

    try:
        for result in run_checks(
            args.relay_url,
            session=args.session,
            admission_token=args.admission_token,
        ):
            print(f"ok {result.name}: {result.detail}")
    except RelayCompatibilityError as exc:
        raise SystemExit(f"relay compatibility failed: {exc}") from exc


if __name__ == "__main__":
    main()
