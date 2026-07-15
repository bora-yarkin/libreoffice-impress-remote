# SPDX-FileCopyrightText: 2026 Bora Yarkın
# SPDX-License-Identifier: GPL-3.0-only

from __future__ import annotations

import sys
import traceback
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from unohelper import Base as UnoBase
    import unohelper
    from com.sun.star.frame import XDispatch, XDispatchProvider
    from com.sun.star.lang import XServiceInfo
else:
    try:
        import unohelper
        from com.sun.star.frame import XDispatch, XDispatchProvider
        from com.sun.star.lang import XServiceInfo

        UnoBase = unohelper.Base
    except Exception:
        unohelper = None

        class UnoBase:
            pass

        class XDispatch:
            pass

        class XDispatchProvider:
            pass

        class XServiceInfo:
            pass

PACKAGE_ROOT = Path(__file__).resolve().parent
PYTHON_ROOT = PACKAGE_ROOT.parent
if str(PYTHON_ROOT) not in sys.path:
    sys.path.insert(0, str(PYTHON_ROOT))

from impress_remote.local_server import RemoteServer

IMPLEMENTATION_NAME = "org.borayarkin.libreoffice.impressremote.ProtocolHandler"
SERVICE_NAMES = ("com.sun.star.frame.ProtocolHandler",)


class ImpressRemoteProtocolHandler(
    UnoBase,
    XServiceInfo,
    XDispatchProvider,
    XDispatch,
):
    def __init__(self, ctx):
        self.ctx = ctx
        self.server = None

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
            elif command == "stop":
                self.stop()
        except Exception:
            traceback.print_exc()

    def addStatusListener(self, _listener, _url):
        return None

    def removeStatusListener(self, _listener, _url):
        return None

    def start(self):
        if self.server is None:
            self.server = RemoteServer(self.ctx)
            self.server.start()
        print(f"LibreOffice Impress Remote started at {self.server.url}")

    def stop(self):
        if self.server is not None:
            self.server.stop()
            self.server = None


def create(ctx):
    return ImpressRemoteProtocolHandler(ctx)


if unohelper is not None:
    g_ImplementationHelper = unohelper.ImplementationHelper()
    g_ImplementationHelper.addImplementation(
        create,
        IMPLEMENTATION_NAME,
        SERVICE_NAMES,
    )
