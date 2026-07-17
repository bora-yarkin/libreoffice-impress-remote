# SPDX-FileCopyrightText: 2026 Bora Yarkın
# SPDX-License-Identifier: GPL-3.0-only

import importlib.util
import sys
import types
import unittest
from pathlib import Path
from typing import Any, cast


ROOT = Path(__file__).resolve().parents[1]
COMPONENT_PATH = ROOT / "extension/python/impress_remote/component.py"
COMPONENT_DIR = str(COMPONENT_PATH.parent)
PYTHON_DIR = str(COMPONENT_PATH.parent.parent)


def load_component_module():
    original_path = list(sys.path)
    original_modules = {
        name: sys.modules.get(name)
        for name in (
            "component_runtime_under_test",
            "unohelper",
            "com",
            "com.sun",
            "com.sun.star",
            "com.sun.star.frame",
            "com.sun.star.lang",
        )
    }

    try:
        sys.path = [COMPONENT_DIR] + [entry for entry in sys.path if entry != PYTHON_DIR]
        for name in original_modules:
            sys.modules.pop(name, None)
        _install_uno_stubs()

        spec = importlib.util.spec_from_file_location(
            "component_runtime_under_test",
            COMPONENT_PATH,
        )
        if spec is None or spec.loader is None:
            raise AssertionError("Could not create an import spec for component.py")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module, original_path, original_modules
    except Exception:
        sys.path = original_path
        for name, module in original_modules.items():
            if module is None:
                sys.modules.pop(name, None)
            else:
                sys.modules[name] = module
        raise


def restore_component_module(original_path, original_modules):
    sys.path = original_path
    for name, module in original_modules.items():
        if module is None:
            sys.modules.pop(name, None)
        else:
            sys.modules[name] = module


def _install_uno_stubs() -> None:
    unohelper = types.ModuleType("unohelper")
    cast(Any, unohelper).Base = type("Base", (), {})

    class ImplementationHelper:
        def __init__(self) -> None:
            self.entries = []

        def addImplementation(self, ctor, implementation_name, service_names) -> None:
            self.entries.append((ctor, implementation_name, tuple(service_names)))

    cast(Any, unohelper).ImplementationHelper = ImplementationHelper

    frame_module = types.ModuleType("com.sun.star.frame")
    cast(Any, frame_module).XDispatch = type("XDispatch", (), {})
    cast(Any, frame_module).XDispatchProvider = type("XDispatchProvider", (), {})
    cast(Any, frame_module).XTerminateListener = type("XTerminateListener", (), {})

    lang_module = types.ModuleType("com.sun.star.lang")
    cast(Any, lang_module).XServiceInfo = type("XServiceInfo", (), {})

    com_module = types.ModuleType("com")
    sun_module = types.ModuleType("com.sun")
    star_module = types.ModuleType("com.sun.star")
    cast(Any, com_module).sun = sun_module
    cast(Any, sun_module).star = star_module
    cast(Any, star_module).frame = frame_module
    cast(Any, star_module).lang = lang_module

    sys.modules["unohelper"] = unohelper
    sys.modules["com"] = com_module
    sys.modules["com.sun"] = sun_module
    sys.modules["com.sun.star"] = star_module
    sys.modules["com.sun.star.frame"] = frame_module
    sys.modules["com.sun.star.lang"] = lang_module


class FakeUrl:
    def __init__(self, path: str, protocol: str = "vnd.org.borayarkin.impressremote:"):
        self.Path = path
        self.Protocol = protocol


class FakeMergedConfig:
    def __init__(self, payload):
        self.payload = payload
        self.saved = False

    def save(self, ctx=None) -> None:
        self.saved = True


class FakeConfig:
    def __init__(self) -> None:
        self.merged_payload = None
        self.last_merged = None

    def merge(self, payload):
        self.merged_payload = payload
        self.last_merged = FakeMergedConfig(payload)
        return self.last_merged


class FakeServer:
    def __init__(self, running: bool = False) -> None:
        self.http_servers = [object()] if running else []
        self.config = FakeConfig()
        self.updated = None
        self.controller = types.SimpleNamespace(
            state=lambda: types.SimpleNamespace(
                running=False,
                active=False,
                paused=False,
                blanked=False,
                document_kind="none",
                status_message="Open an Impress presentation to use the remote.",
                current_slide=0,
                slide_count=0,
                current_title="",
                next_slide=None,
                next_title="",
                remaining_slides=0,
                at_end_of_deck=False,
                elapsed_seconds=0,
            )
        )

    def config_payload(self):
        return {
            "localPort": 17865,
            "enableLocalListener": True,
            "enableIpv6Direct": True,
            "enableRelay": False,
            "relayUrl": "",
            "preferredRoute": "auto",
            "restartRequired": False,
            "activeLocalPort": 17865,
        }

    def connection_info(self):
        return {
            "session": "demo123",
            "running": bool(self.http_servers),
            "localPort": 17865,
            "requestedLocalPort": 17865,
            "enableLocalListener": True,
            "enableIpv6Direct": True,
            "localUrls": ["http://127.0.0.1:17865/#s=demo123&k=pairsecret"],
            "directUrls": [],
            "listenerWarnings": [],
            "configPendingRestart": False,
            "relayEnabled": False,
            "relayConfigured": False,
            "relayUrl": "",
            "relayJoinUrl": "",
            "consoleUrl": "http://127.0.0.1:17865/#s=demo123&k=pairsecret",
            "settingsUrl": "http://127.0.0.1:17865/#s=demo123&k=pairsecret&view=settings",
            "pairingRouteRequested": "auto",
            "pairingRoute": "local",
            "pairingRouteLabel": "Local network",
            "pairingUrl": "http://127.0.0.1:17865/#s=demo123&k=pairsecret",
            "pairingHint": "Scan the QR code to pair over local network.",
            "routeLocalUrl": "http://127.0.0.1:17865/#s=demo123&k=pairsecret",
            "routeIpv6Url": "",
            "routeRelayUrl": "",
            "relayStatus": "disabled",
            "relayLastError": "",
            "clientConnected": False,
            "clientConnectionSource": "",
        }

    def update_config(self, updated, restart_runtime: bool) -> None:
        self.updated = (updated, restart_runtime)

    def pairing_target(self, route_mode=None):
        return {
            "requestedRoute": route_mode or "auto",
            "selectedRoute": "local",
            "selectedLabel": "Local network",
            "selectedUrl": "http://127.0.0.1:17865/#s=demo123&k=pairsecret",
            "hint": "Scan the QR code to pair over local network.",
        }

    def preview_pairing_target(self, _config, route_mode=None):
        return self.pairing_target(route_mode)

    def is_running(self) -> bool:
        return bool(self.http_servers)

    def start(self) -> None:
        self.http_servers = [object()]

    def stop(self) -> None:
        self.http_servers = []


class ComponentRuntimeTests(unittest.TestCase):
    def setUp(self) -> None:
        module, self.original_path, self.original_modules = load_component_module()
        self.component = module

    def tearDown(self) -> None:
        restore_component_module(self.original_path, self.original_modules)

    def test_dispatch_routes_new_menu_actions(self) -> None:
        handler = self.component.ImpressRemoteProtocolHandler(ctx=object())
        actions: list[str] = []

        handler.toggle_remote = lambda: actions.append("toggle")
        handler.start = lambda: actions.append("start")
        handler.stop = lambda: actions.append("stop")
        handler.open_console = lambda: actions.append("open")
        handler.show_settings = lambda: actions.append("settings")

        for path in ("toggle", "start", "open", "settings", "stop"):
            handler.dispatch(FakeUrl(path), ())

        self.assertEqual(actions, ["toggle", "start", "open", "settings", "stop"])

    def test_toggle_remote_shows_pairing_after_starting(self) -> None:
        handler = self.component.ImpressRemoteProtocolHandler(ctx=object())
        handler.server = FakeServer(running=False)
        paired: list[str] = []

        handler.show_pairing = lambda: paired.append("shown")

        handler.toggle_remote()

        server = handler.server
        self.assertIsNotNone(server)
        assert server is not None
        self.assertTrue(server.is_running())
        self.assertEqual(paired, ["shown"])

    def test_toggle_remote_stops_without_showing_pairing_when_running(self) -> None:
        handler = self.component.ImpressRemoteProtocolHandler(ctx=object())
        handler.server = FakeServer(running=True)
        paired: list[str] = []

        handler.show_pairing = lambda: paired.append("shown")

        handler.toggle_remote()

        server = handler.server
        self.assertIsNotNone(server)
        assert server is not None
        self.assertFalse(server.is_running())
        self.assertEqual(paired, [])

    def test_status_listener_receives_dynamic_menu_label(self) -> None:
        handler = self.component.ImpressRemoteProtocolHandler(ctx=object())
        handler.server = FakeServer(running=False)
        labels: list[str] = []

        class Listener:
            def statusChanged(self, event) -> None:
                labels.append(event.FeatureDescriptor)

        handler.addStatusListener(Listener(), FakeUrl("toggle"))
        handler.start()

        self.assertEqual(labels, ["Start Remote", "Stop Remote"])

    def test_runtime_snapshot_reports_when_remote_is_stopped(self) -> None:
        handler = self.component.ImpressRemoteProtocolHandler(ctx=object())
        handler.server = FakeServer(running=False)

        snapshot = handler.runtime_snapshot()

        self.assertFalse(snapshot["running"])
        self.assertEqual(snapshot["statusLine"], "Remote is stopped.")
        self.assertEqual(snapshot["connection"]["session"], "demo123")

    def test_apply_settings_merges_and_saves_config(self) -> None:
        handler = self.component.ImpressRemoteProtocolHandler(ctx=object())
        handler.server = FakeServer(running=True)

        snapshot = handler.apply_settings(
            {
                "localPort": 19001,
                "enableIpv6Direct": False,
                "enableRelay": True,
                "relayUrl": "https://relay.example.com",
            },
            restart_runtime=True,
        )

        self.assertEqual(snapshot["statusLine"], "Settings saved.")
        server = handler.server
        self.assertIsNotNone(server)
        assert server is not None
        merged_payload = server.config.merged_payload
        self.assertIsNotNone(merged_payload)
        assert merged_payload is not None
        self.assertEqual(merged_payload["localPort"], 19001)
        updated = server.updated
        self.assertIsNotNone(updated)
        assert updated is not None
        self.assertTrue(updated[0].saved)
        self.assertTrue(updated[1])


if __name__ == "__main__":
    unittest.main()
