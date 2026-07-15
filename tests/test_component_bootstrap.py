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
