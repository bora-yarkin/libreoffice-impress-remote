# SPDX-FileCopyrightText: 2026 Bora Yarkın
# SPDX-License-Identifier: GPL-3.0-only

from __future__ import annotations

import asyncio
from pathlib import Path

from aiohttp import web

from relay.localization import translate
from relay.relay import RelayState, create_app
from relay.runtime import ensure_runtime_config


def create_windows_service_class(
    *,
    config_path: Path,
    service_name: str,
    display_name: str,
    description: str,
):
    import servicemanager
    import win32event
    import win32service
    import win32serviceutil

    class RelayWindowsService(win32serviceutil.ServiceFramework):
        _svc_name_ = service_name
        _svc_display_name_ = display_name
        _svc_description_ = description

        def __init__(self, args):
            super().__init__(args)
            self._stop_handle = win32event.CreateEvent(None, 0, 0, None)
            self._shutdown_event: asyncio.Event | None = None
            self._loop: asyncio.AbstractEventLoop | None = None

        def SvcStop(self) -> None:
            self.ReportServiceStatus(win32service.SERVICE_STOP_PENDING)
            if self._loop is not None and self._shutdown_event is not None:
                self._loop.call_soon_threadsafe(self._shutdown_event.set)
            win32event.SetEvent(self._stop_handle)

        def SvcDoRun(self) -> None:
            servicemanager.LogInfoMsg(f"{service_name} starting")
            try:
                self._loop = asyncio.new_event_loop()
                asyncio.set_event_loop(self._loop)
                self._loop.run_until_complete(self._serve())
            except Exception as exc:
                servicemanager.LogErrorMsg(f"{service_name} failed: {exc}")
                raise
            finally:
                if self._loop is not None:
                    self._loop.close()
                    self._loop = None
            servicemanager.LogInfoMsg(f"{service_name} stopped")

        async def _serve(self) -> None:
            config = ensure_runtime_config(config_path)
            app = create_app(RelayState(session_ttl=config.session_ttl))
            runner = web.AppRunner(app)
            await runner.setup()
            self._shutdown_event = asyncio.Event()
            try:
                sites = []
                for host in (config.host_v4, config.host_v6):
                    if not host:
                        continue
                    site = web.TCPSite(runner, host=host, port=config.port)
                    await site.start()
                    sites.append(site)
                if not sites:
                    raise RuntimeError(translate("relay.error.noListenSockets"))
                await self._shutdown_event.wait()
            finally:
                await runner.cleanup()

    return RelayWindowsService
