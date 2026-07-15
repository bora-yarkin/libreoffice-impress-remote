# SPDX-FileCopyrightText: 2026 Bora Yarkın
# SPDX-License-Identifier: GPL-3.0-only

from __future__ import annotations

import os
import sys
import traceback
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from impress_remote.local_server import RemoteServer

BOOTSTRAP_LOG_PATH = os.path.join(
    os.environ.get("TMPDIR", "/tmp"),
    "impress-remote-bootstrap.log",
)


def _write_bootstrap_log(summary):
    try:
        with open(BOOTSTRAP_LOG_PATH, "w", encoding="utf-8") as log_file:
            log_file.write(summary)
    except Exception:
        pass


try:
    import unohelper
    from com.sun.star.frame import XDispatch, XDispatchProvider
    from com.sun.star.lang import XServiceInfo
except Exception:
    _write_bootstrap_log(traceback.format_exc())
    raise


IMPLEMENTATION_NAME = "org.borayarkin.libreoffice.impressremote.ProtocolHandler"
SERVICE_NAMES = ("com.sun.star.frame.ProtocolHandler",)


def _ensure_python_root():
    python_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    if python_root not in sys.path:
        sys.path.insert(0, python_root)


try:
    class ImpressRemoteProtocolHandler(
        unohelper.Base,
        XServiceInfo,
        XDispatchProvider,
        XDispatch,
    ):
        def __init__(self, ctx):
            self.ctx = ctx
            self.server: RemoteServer | None = None

        def getImplementationName(self):
            return IMPLEMENTATION_NAME

        def supportsService(self, name):
            return name in SERVICE_NAMES

        def getSupportedServiceNames(self):
            return SERVICE_NAMES

        def queryDispatch(self, url, _target_frame_name, _search_flags):
            if getattr(url, "Protocol", "") == "vnd.org.borayarkin.impressremote:":
                return self
            return None

        def queryDispatches(self, requests):
            return tuple(
                self.queryDispatch(item.FeatureURL, item.FrameName, item.SearchFlags)
                for item in requests
            )

        def dispatch(self, url, _args):
            command = getattr(url, "Path", "")
            try:
                if command == "start":
                    self.start()
                elif command == "open":
                    self.open_console()
                elif command == "settings":
                    self.show_settings()
                elif command == "stop":
                    self.stop()
            except Exception:
                traceback.print_exc()

        def addStatusListener(self, _listener, _url):
            return None

        def removeStatusListener(self, _listener, _url):
            return None

        def start(self):
            server = self._ensure_server()
            server.start()
            print(f"LibreOffice Impress Remote started at {server.url}")

        def stop(self):
            if self.server is not None:
                self.server.stop()
                self.server = None

        def open_console(self, view: str | None = None):
            server = self._ensure_server()
            server.start()
            _ensure_python_root()
            from impress_remote.office_ui import open_external_url

            target = server.settings_url() if view == "settings" else server.console_url()
            open_external_url(self.ctx, target)

        def show_settings(self):
            _ensure_python_root()
            from impress_remote.office_ui import show_remote_settings_dialog

            show_remote_settings_dialog(self.ctx, self)

        def runtime_snapshot(self) -> dict[str, object]:
            server = self._ensure_server()
            snapshot = {
                "running": bool(server.http_servers),
                "config": server.config_payload(),
                "connection": server.connection_info(),
            }
            snapshot["statusLine"] = (
                "Remote is running." if snapshot["running"] else "Remote is stopped."
            )
            return snapshot

        def apply_settings(
            self,
            payload: dict[str, object],
            restart_runtime: bool,
        ) -> dict[str, object]:
            server = self._ensure_server()
            updated = server.config.merge(payload)
            updated.save()
            server.update_config(updated, restart_runtime=restart_runtime)
            snapshot = self.runtime_snapshot()
            snapshot["statusLine"] = "Settings saved."
            return snapshot

        def pairing_target(self, route_mode: str | None = None) -> dict[str, str]:
            server = self._ensure_server()
            return server.pairing_target(route_mode)

        def _ensure_server(self) -> RemoteServer:
            if self.server is None:
                _ensure_python_root()
                from impress_remote.local_server import RemoteServer

                self.server = RemoteServer(self.ctx)
            return self.server
except Exception:
    _write_bootstrap_log(traceback.format_exc())
    raise


def create(ctx):
    return ImpressRemoteProtocolHandler(ctx)


try:
    g_ImplementationHelper = unohelper.ImplementationHelper()
    g_ImplementationHelper.addImplementation(
        create,
        IMPLEMENTATION_NAME,
        SERVICE_NAMES,
    )
except Exception:
    _write_bootstrap_log(traceback.format_exc())
    raise
