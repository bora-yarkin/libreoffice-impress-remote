# SPDX-FileCopyrightText: 2026 Bora Yarkın
# SPDX-License-Identifier: GPL-3.0-only
# ruff: noqa: E402,F811

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


class ComponentBootstrapTests(unittest.TestCase):
    def test_component_loads_from_its_own_directory(self) -> None:
        original_path = list(sys.path)
        original_modules = {
            name: sys.modules.get(name)
            for name in (
                "component_under_test",
                "impress_remote",
                "impress_remote.local_server",
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
            self._install_uno_stubs()

            spec = importlib.util.spec_from_file_location("component_under_test", COMPONENT_PATH)
            if spec is None or spec.loader is None:
                raise AssertionError("Could not create an import spec for component.py")
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)

            self.assertEqual(
                module.IMPLEMENTATION_NAME,
                "org.borayarkin.libreoffice.impressremote.ProtocolHandler",
            )
        finally:
            sys.path = original_path
            for name, module in original_modules.items():
                if module is None:
                    sys.modules.pop(name, None)
                else:
                    sys.modules[name] = module

    def _install_uno_stubs(self) -> None:
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


if __name__ == "__main__":
    unittest.main()


import importlib.util
import sys
import types
import unittest
from pathlib import Path
from typing import Any, cast


ROOT = Path(__file__).resolve().parents[1]
OFFICE_UI_PATH = ROOT / "extension/python/impress_remote/office_ui.py"
PYTHON_DIR = str(OFFICE_UI_PATH.parent.parent)


class OfficeUiBootstrapTests(unittest.TestCase):
    def test_office_ui_imports_with_uno_stubs(self) -> None:
        original_path = list(sys.path)
        original_modules = {
            name: sys.modules.get(name)
            for name in (
                "office_ui_under_test",
                "unohelper",
                "com",
                "com.sun",
                "com.sun.star",
                "com.sun.star.awt",
            )
        }

        try:
            sys.path = [PYTHON_DIR] + [entry for entry in sys.path if entry != PYTHON_DIR]
            for name in original_modules:
                sys.modules.pop(name, None)
            self._install_uno_stubs()

            spec = importlib.util.spec_from_file_location("office_ui_under_test", OFFICE_UI_PATH)
            if spec is None or spec.loader is None:
                raise AssertionError("Could not create an import spec for office_ui.py")
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)

            self.assertTrue(hasattr(module, "show_remote_settings_dialog"))
            self.assertTrue(hasattr(module, "DialogButtonListener"))
            button_listener = module.DialogButtonListener(type("Dialog", (), {})())
            item_listener = module.DialogItemListener(type("Dialog", (), {})())
            self.assertEqual(
                button_listener.getTypes(),
                ("com.sun.star.awt.XActionListener",),
            )
            self.assertEqual(
                item_listener.getTypes(),
                ("com.sun.star.awt.XItemListener",),
            )
            self.assertEqual(button_listener.getImplementationId(), b"")
        finally:
            sys.path = original_path
            for name, module in original_modules.items():
                if module is None:
                    sys.modules.pop(name, None)
                else:
                    sys.modules[name] = module

    def _install_uno_stubs(self) -> None:
        unohelper = types.ModuleType("unohelper")
        cast(Any, unohelper).Base = type("Base", (), {})

        awt_module = types.ModuleType("com.sun.star.awt")
        cast(Any, awt_module).XActionListener = type("XActionListener", (), {})
        cast(Any, awt_module).XItemListener = type("XItemListener", (), {})

        com_module = types.ModuleType("com")
        sun_module = types.ModuleType("com.sun")
        star_module = types.ModuleType("com.sun.star")
        cast(Any, com_module).sun = sun_module
        cast(Any, sun_module).star = star_module
        cast(Any, star_module).awt = awt_module

        sys.modules["unohelper"] = unohelper
        sys.modules["com"] = com_module
        sys.modules["com.sun"] = sun_module
        sys.modules["com.sun.star"] = star_module
        sys.modules["com.sun.star.awt"] = awt_module


if __name__ == "__main__":
    unittest.main()


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
    def __init__(
        self,
        path: str,
        protocol: str = "vnd.org.borayarkin.impressremote:",
        complete: str | None = None,
    ):
        self.Path = path
        self.Protocol = protocol
        self.Complete = complete if complete is not None else f"{protocol}{path}"


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
            "preferredRoute": "local",
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
            "relaySessionStatusUrl": "",
            "consoleUrl": "http://127.0.0.1:17865/#s=demo123&k=pairsecret",
            "settingsUrl": "http://127.0.0.1:17865/#s=demo123&k=pairsecret&view=settings",
            "pairingRouteRequested": "local",
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
            "requestedRoute": route_mode or "local",
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
        handler.show_remote_menu = lambda: actions.append("menu")

        for path in ("menu", "toggle", "start", "open", "settings", "stop"):
            handler.dispatch(FakeUrl(path), ())

        self.assertEqual(actions, ["menu", "toggle", "start", "open", "settings", "stop"])

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

    def test_status_listener_uses_complete_url_when_path_is_missing(self) -> None:
        handler = self.component.ImpressRemoteProtocolHandler(ctx=object())
        handler.server = FakeServer(running=False)
        labels: list[str] = []

        class Listener:
            def statusChanged(self, event) -> None:
                labels.append(event.State)

        handler.addStatusListener(
            Listener(),
            FakeUrl("", complete="vnd.org.borayarkin.impressremote:toggle"),
        )
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


import unittest

from impress_remote.office_ui import RemotePairingDialog, export_qr_png_path


class QrTests(unittest.TestCase):
    def test_export_qr_png_path_creates_a_png_file(self) -> None:
        output_path = export_qr_png_path(None, "http://127.0.0.1:17865/#s=demo123")
        try:
            self.assertTrue(output_path.exists())
            self.assertEqual(output_path.read_bytes()[:8], b"\x89PNG\r\n\x1a\n")
        finally:
            output_path.unlink(missing_ok=True)

    def test_export_qr_png_path_requires_a_payload(self) -> None:
        with self.assertRaises(RuntimeError):
            export_qr_png_path(None, "")

    def test_pairing_dialog_reports_tunnel_errors(self) -> None:
        dialog = object.__new__(RemotePairingDialog)
        dialog.qr_error = ""

        message = dialog._pairing_error_text(
            {"selectedRoute": "tunnel", "selectedUrl": "", "hint": ""},
            {"tunnelLastError": "connection refused"},
        )

        self.assertIn("Tunnel", message)
        self.assertIn("connection refused", message)

    def test_pairing_dialog_treats_connecting_tunnel_as_loading_state(self) -> None:
        dialog = object.__new__(RemotePairingDialog)
        dialog.qr_error = ""

        message = dialog._pairing_error_text(
            {
                "selectedRoute": "tunnel",
                "selectedUrl": "",
                "hint": "Tunnel fallback is starting.",
            },
            {"tunnelStatus": "connecting", "tunnelLastError": ""},
        )
        status = dialog._pairing_status_text(
            {
                "selectedRoute": "tunnel",
                "selectedUrl": "",
                "hint": "LocalTunnel is starting.",
            },
            {"tunnelStatus": "connecting", "tunnelLastError": ""},
        )
        details = dialog._pairing_error_details(
            {"selectedRoute": "tunnel", "hint": ""},
            {
                "relayStatus": "disabled",
                "relayUrl": "https://relay.example.com",
                "tunnelStatus": "connecting",
                "tunnelUrl": "",
                "tunnelLastError": "",
            },
        )

        self.assertEqual(message, "")
        self.assertEqual(status, "LocalTunnel is starting.")
        self.assertIn("tunnelStatus: connecting", details)
        self.assertNotIn("relayUrl", details)

    def test_pairing_dialog_treats_retrying_tunnel_as_loading_state(self) -> None:
        dialog = object.__new__(RemotePairingDialog)
        dialog.qr_error = ""

        message = dialog._pairing_error_text(
            {
                "selectedRoute": "tunnel",
                "selectedUrl": "",
                "hint": "LocalTunnel is starting.",
            },
            {
                "tunnelStatus": "retrying",
                "tunnelLastError": "temporary outage",
            },
        )
        status = dialog._pairing_status_text(
            {
                "selectedRoute": "tunnel",
                "selectedUrl": "",
                "hint": "LocalTunnel is starting.",
            },
            {
                "tunnelStatus": "retrying",
                "tunnelLastError": "temporary outage",
            },
        )

        self.assertEqual(message, "")
        self.assertEqual(status, "LocalTunnel is starting.")

    def test_pairing_dialog_refresh_updates_tunnel_qr_when_url_becomes_ready(self) -> None:
        dialog = object.__new__(RemotePairingDialog)
        pairing_values = [
            {"selectedRoute": "tunnel", "selectedUrl": "", "hint": "starting"},
            {
                "selectedRoute": "tunnel",
                "selectedUrl": "https://demo.localtunnel.me/#mode=tunnel&s=demo&k=secret",
                "hint": "",
            },
        ]
        rendered_urls: list[str] = []

        class FakeHandler:
            def pairing_target(self):
                return pairing_values.pop(0)

        test_dialog = cast(Any, dialog)
        test_dialog.handler = FakeHandler()
        test_dialog.current_pairing_url = ""
        test_dialog.qr_error = ""
        test_dialog._empty_pairing_seen_at = 1.0
        test_dialog._last_pairing_error = ""
        test_dialog._set_qr_image = rendered_urls.append
        test_dialog._set_pairing_status = lambda _message: None
        test_dialog._show_pairing_error_if_needed = lambda *_args: None

        snapshot = {"connection": {"tunnelStatus": "connecting"}}
        dialog._refresh_pairing_from_snapshot(snapshot, show_pending=False)
        dialog._refresh_pairing_from_snapshot(snapshot, show_pending=False)

        self.assertEqual(
            rendered_urls,
            ["https://demo.localtunnel.me/#mode=tunnel&s=demo&k=secret"],
        )


if __name__ == "__main__":
    unittest.main()


from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile

import pytest

from impress_remote import __version__
from impress_remote.office_ui import (
    export_packaged_resource,
    read_packaged_user_guide,
    render_user_guide_html,
)


def _fake_module_file(root: Path) -> Path:
    module_file = root / "python" / "impress_remote" / "office_ui.py"
    module_file.parent.mkdir(parents=True)
    module_file.write_text("", encoding="utf-8")
    return module_file


def test_read_packaged_user_guide_uses_bundled_markdown(tmp_path: Path) -> None:
    module_file = _fake_module_file(tmp_path / "extension-root")
    guide_path = tmp_path / "extension-root" / "resources" / "user-guide.md"
    guide_path.parent.mkdir()
    guide_path.write_text(
        "<!-- SPDX-FileCopyrightText: 2026 Bora Yarkın -->\n"
        "<!-- SPDX-License-Identifier: GPL-3.0-only -->\n\n"
        "# User Guide\n\nInstall the OXT.\n",
        encoding="utf-8",
    )

    guide = read_packaged_user_guide(str(module_file))

    assert guide.startswith("# User Guide")
    assert "Install the OXT." in guide
    assert "SPDX" not in guide


def test_user_guide_markdown_renders_to_html() -> None:
    html = render_user_guide_html(
        "# User Guide\n\n"
        "Use **Local network** and `Start Remote`.\n\n"
        "1. Open Impress.\n"
        "2. Scan QR.\n\n"
        "| Mode | Status |\n"
        "| --- | --- |\n"
        "| Local network | Recommended |\n\n"
        "```bash\nmake oxt\n```\n"
    )

    assert "<h1>User Guide</h1>" in html
    assert "<strong>Local network</strong>" in html
    assert "<code>Start Remote</code>" in html
    assert "<ol>" in html
    assert "<table>" in html
    assert "<pre><code>make oxt</code></pre>" in html


def test_export_packaged_resource_wraps_flat_bundles_in_archive_named_folder(
    tmp_path: Path,
) -> None:
    module_file = _fake_module_file(tmp_path / "extension-root")
    archive_name = f"impress-remote-relay-python-{__version__}.zip"
    archive_path = tmp_path / "extension-root" / "resources" / archive_name
    archive_path.parent.mkdir()
    with ZipFile(archive_path, "w", ZIP_DEFLATED) as archive:
        archive.writestr("run-relay.py", "runner")
        archive.writestr("README.md", "relay docs")

    destination = tmp_path / "Downloads"
    result = export_packaged_resource("relay", destination, str(module_file))

    assert result.entries == 2
    export_root = destination / f"impress-remote-relay-python-{__version__}"
    assert (export_root / "run-relay.py").read_text(encoding="utf-8") == "runner"
    assert (export_root / "README.md").read_text(encoding="utf-8") == "relay docs"
    assert not (destination / "run-relay.py").exists()


def test_export_packaged_resource_rejects_unsafe_archive_members(tmp_path: Path) -> None:
    module_file = _fake_module_file(tmp_path / "extension-root")
    archive_name = f"impress-remote-relay-python-{__version__}.zip"
    archive_path = tmp_path / "extension-root" / "resources" / archive_name
    archive_path.parent.mkdir()
    with ZipFile(archive_path, "w", ZIP_DEFLATED) as archive:
        archive.writestr("../outside.txt", "nope")

    with pytest.raises(ValueError):
        export_packaged_resource("relay", tmp_path / "Downloads", str(module_file))
