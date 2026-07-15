# SPDX-FileCopyrightText: 2026 Bora Yarkın
# SPDX-License-Identifier: GPL-3.0-only

import unittest
from pathlib import Path

from impress_remote.paths import module_file_path


class PathTests(unittest.TestCase):
    def test_module_file_path_accepts_filesystem_path(self) -> None:
        path = module_file_path("/tmp/example.py")
        self.assertEqual(path, Path("/tmp/example.py").resolve())

    def test_module_file_path_accepts_file_url(self) -> None:
        path = module_file_path("file:///tmp/example.py")
        self.assertEqual(path, Path("/tmp/example.py").resolve())
