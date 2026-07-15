# SPDX-FileCopyrightText: 2026 Bora Yarkın
# SPDX-License-Identifier: GPL-3.0-only

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
        cast(Any, awt_module).XTextListener = type("XTextListener", (), {})

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
