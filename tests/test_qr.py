# SPDX-FileCopyrightText: 2026 Bora Yarkın
# SPDX-License-Identifier: GPL-3.0-only

import unittest

from impress_remote.qr import export_qr_png_path


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


if __name__ == "__main__":
    unittest.main()
