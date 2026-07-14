# SPDX-FileCopyrightText: 2026 Bora Yarkın
# SPDX-License-Identifier: GPL-3.0-only

from __future__ import annotations

import traceback

try:
    import unohelper
    from com.sun.star.frame import XDispatch, XDispatchProvider
    from com.sun.star.lang import XServiceInfo
except Exception:
    unohelper = None
    XDispatch = object
    XDispatchProvider = object
    XServiceInfo = object

from impress_remote.local_server import RemoteServer

IMPLEMENTATION_NAME = "org.borayarkin.libreoffice.impressremote.ProtocolHandler"
SERVICE_NAMES = ("com.sun.star.frame.ProtocolHandler",)


class ImpressRemoteProtocolHandler(unohelper.Base, XServiceInfo, XDispatchProvider, XDispatch):
    def __init__(self, ctx):
        self.ctx = ctx
        self.server = None

    def getImplementationName(self):
        return IMPLEMENTATION_NAME

    def supportsService(self, name):
        return name in SERVICE_NAMES

    def getSupportedServiceNames(self):
        return SERVICE_NAMES

    def queryDispatch(self, url, target_frame_name, search_flags):
        if getattr(url, "Protocol", "") == "vnd.org.borayarkin.impressremote:":
            return self
        return None

    def queryDispatches(self, requests):
        return tuple(self.queryDispatch(item.FeatureURL, item.FrameName, item.SearchFlags) for item in requests)

    def dispatch(self, url, args):
        command = getattr(url, "Path", "")
        try:
            if command == "start":
                self.start()
            elif command == "stop":
                self.stop()
        except Exception:
            traceback.print_exc()

    def addStatusListener(self, listener, url):
        return None

    def removeStatusListener(self, listener, url):
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


g_ImplementationHelper = unohelper.ImplementationHelper()
g_ImplementationHelper.addImplementation(create, IMPLEMENTATION_NAME, SERVICE_NAMES)
