# SPDX-FileCopyrightText: 2026 Bora Yarkın
# SPDX-License-Identifier: GPL-3.0-only

from __future__ import annotations

import os
import sys
import traceback
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from com.sun.star.frame import (  # pyright: ignore[reportMissingImports]
        XDispatch,
        XDispatchProvider,
        XTerminateListener,
    )
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
    if not TYPE_CHECKING:
        from com.sun.star.frame import XDispatch, XDispatchProvider
        try:
            from com.sun.star.frame import XTerminateListener
        except Exception:
            class XTerminateListener:
                def disposing(self, _event) -> None:
                    return None

                def queryTermination(self, _event) -> None:
                    return None

                def notifyTermination(self, _event) -> None:
                    return None
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


def _service_manager(ctx):
    if hasattr(ctx, "ServiceManager"):
        return ctx.ServiceManager
    return ctx.getServiceManager()


def _format_elapsed(seconds: int) -> str:
    total_seconds = max(int(seconds), 0)
    minutes, remaining_seconds = divmod(total_seconds, 60)
    hours, remaining_minutes = divmod(minutes, 60)
    if hours:
        return f"{hours:d}:{remaining_minutes:02d}:{remaining_seconds:02d}"
    return f"{remaining_minutes:02d}:{remaining_seconds:02d}"


def _coerce_int(value: object, default: int = 0) -> int:
    if isinstance(value, bool):
        return int(value)
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        return int(value)
    if isinstance(value, str):
        try:
            return int(value)
        except ValueError:
            return default
    return default


def _compose_status_line(remote_running: bool, presentation: dict[str, object]) -> str:
    if not remote_running:
        return "Remote is stopped."

    message = str(presentation.get("statusMessage", "")).strip().rstrip(".")
    if not message:
        message = "Remote is running"

    slide_count = _coerce_int(presentation.get("slideCount", 0))
    if presentation.get("documentKind") == "impress" and slide_count > 0:
        current_slide = _coerce_int(presentation.get("currentSlide", 0))
        status_line = f"{message}. Slide {current_slide + 1} of {slide_count}."
        if presentation.get("running"):
            timer = _format_elapsed(_coerce_int(presentation.get("elapsedSeconds", 0)))
            return f"{status_line} Timer {timer}."
        return status_line
    return f"{message}."


try:
    class ProtocolTerminateListener(unohelper.Base, XTerminateListener):
        def __init__(self, handler):
            self.handler = handler

        def disposing(self, _event):
            self.handler.shutdown()

        def queryTermination(self, _event):
            return None

        def notifyTermination(self, _event):
            self.handler.shutdown()

    class ImpressRemoteProtocolHandler(
        unohelper.Base,
        XServiceInfo,
        XDispatchProvider,
        XDispatch,
    ):
        def __init__(self, ctx):
            self.ctx = ctx
            self.server: RemoteServer | None = None
            self._last_error = ""
            self._terminate_listener = None
            self._register_terminate_listener()

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
            except Exception as exc:
                self.report_runtime_error(f"{command or 'remote action'} failed: {exc}")
                try:
                    _ensure_python_root()
                    from impress_remote.office_ui import show_error_message

                    show_error_message(
                        self.ctx,
                        f"{command or 'remote action'} failed: {exc}",
                    )
                except Exception:
                    pass
                traceback.print_exc()

        def addStatusListener(self, _listener, _url):
            return None

        def removeStatusListener(self, _listener, _url):
            return None

        def start(self):
            server = self._ensure_server()
            server.start()
            self.clear_runtime_error()
            print(f"LibreOffice Impress Remote started at {server.url}")

        def stop(self):
            if self.server is not None:
                self.server.stop()
            self.clear_runtime_error()

        def shutdown(self):
            if self.server is not None:
                self.server.stop()

        def open_console(self, view: str | None = None):
            server = self._ensure_server()
            server.start()
            _ensure_python_root()
            from impress_remote.office_ui import open_external_url

            target = server.settings_url() if view == "settings" else server.console_url()
            if not target:
                raise RuntimeError("No pairing route is available yet.")
            if not open_external_url(self.ctx, target):
                raise RuntimeError("LibreOffice could not open the remote preview.")
            self.clear_runtime_error()

        def show_settings(self):
            _ensure_python_root()
            from impress_remote.office_ui import show_remote_settings_dialog

            show_remote_settings_dialog(self.ctx, self)

        def runtime_snapshot(self) -> dict[str, object]:
            server = self._ensure_server()
            presentation_state = server.controller.state()
            presentation = {
                "running": presentation_state.running,
                "active": presentation_state.active,
                "paused": presentation_state.paused,
                "blanked": presentation_state.blanked,
                "documentKind": presentation_state.document_kind,
                "statusMessage": presentation_state.status_message,
                "currentSlide": presentation_state.current_slide,
                "slideCount": presentation_state.slide_count,
                "currentTitle": presentation_state.current_title,
                "nextSlide": presentation_state.next_slide,
                "nextTitle": presentation_state.next_title,
                "remainingSlides": presentation_state.remaining_slides,
                "atEndOfDeck": presentation_state.at_end_of_deck,
                "elapsedSeconds": presentation_state.elapsed_seconds,
            }
            snapshot = {
                "running": server.is_running(),
                "config": server.config_payload(),
                "connection": server.connection_info(),
                "presentation": presentation,
                "lastError": self._last_error,
            }
            snapshot["statusLine"] = _compose_status_line(snapshot["running"], presentation)
            return snapshot

        def apply_settings(
            self,
            payload: dict[str, object],
            restart_runtime: bool,
        ) -> dict[str, object]:
            server = self._ensure_server()
            updated = server.config.merge(payload)
            updated.save(ctx=self.ctx)
            server.update_config(updated, restart_runtime=restart_runtime)
            self.clear_runtime_error()
            snapshot = self.runtime_snapshot()
            snapshot["statusLine"] = "Settings saved."
            return snapshot

        def pairing_target(self, route_mode: str | None = None) -> dict[str, str]:
            server = self._ensure_server()
            return server.pairing_target(route_mode)

        def preview_pairing_target(
            self,
            payload: dict[str, object],
            route_mode: str | None = None,
        ) -> dict[str, str]:
            server = self._ensure_server()
            updated = server.config.merge(payload)
            return server.preview_pairing_target(updated, route_mode)

        def report_runtime_error(self, message: str) -> None:
            self._last_error = message

        def clear_runtime_error(self) -> None:
            self._last_error = ""

        def _ensure_server(self) -> RemoteServer:
            if self.server is None:
                _ensure_python_root()
                from impress_remote.local_server import RemoteServer

                self.server = RemoteServer(self.ctx)
            return self.server

        def _register_terminate_listener(self) -> None:
            try:
                desktop = _service_manager(self.ctx).createInstanceWithContext(
                    "com.sun.star.frame.Desktop",
                    self.ctx,
                )
                listener = ProtocolTerminateListener(self)
                desktop.addTerminateListener(listener)
                self._terminate_listener = listener
            except Exception:
                self._terminate_listener = None
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
