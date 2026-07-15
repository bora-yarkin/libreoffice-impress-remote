# SPDX-FileCopyrightText: 2026 Bora Yarkın
# SPDX-License-Identifier: GPL-3.0-only

import importlib.util
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
COMPONENT_PATH = ROOT / "extension/python/impress_remote/component.py"
COMPONENT_DIR = str(COMPONENT_PATH.parent)
PYTHON_DIR = str(COMPONENT_PATH.parent.parent)


class ComponentBootstrapTests(unittest.TestCase):
    def test_component_loads_from_its_own_directory(self) -> None:
        original_path = list(sys.path)
        original_modules = {
            name: sys.modules.get(name)
            for name in ("component_under_test", "impress_remote", "impress_remote.local_server")
        }

        try:
            sys.path = [COMPONENT_DIR] + [entry for entry in sys.path if entry != PYTHON_DIR]
            for name in original_modules:
                sys.modules.pop(name, None)

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


if __name__ == "__main__":
    unittest.main()
