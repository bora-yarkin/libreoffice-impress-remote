#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Bora Yarkın
# SPDX-License-Identifier: GPL-3.0-only

from __future__ import annotations

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parent
for candidate in (ROOT, ROOT.parent, ROOT.parent.parent):
    if (candidate / "relay" / "__init__.py").exists() and str(candidate) not in sys.path:
        sys.path.insert(0, str(candidate))

from relay.runtime import ensure_runtime_config  # noqa: E402
from relay.windows_service import create_windows_service_class  # noqa: E402


def main() -> None:
    import win32serviceutil

    config_path = ROOT / "data" / "service.json"
    ensure_runtime_config(config_path)
    service_class = create_windows_service_class(
        config_path=config_path,
        service_name="ImpressRemoteRelay",
        display_name="Impress Remote Relay",
        description="Encrypted relay server for LibreOffice Impress Remote.",
    )
    win32serviceutil.HandleCommandLine(service_class)


if __name__ == "__main__":
    main()
