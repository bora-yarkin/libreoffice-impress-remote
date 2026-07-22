# SPDX-FileCopyrightText: 2026 Bora Yarkın
# SPDX-License-Identifier: GPL-3.0-only

import importlib.util
import sys
import unittest
from unittest.mock import patch
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
MODULE_PATH = ROOT / "tools/download_sdk.py"


def load_module():
    spec = importlib.util.spec_from_file_location("download_sdk_under_test", MODULE_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError("Could not load tools/download_sdk.py")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


download_sdk = load_module()


class DownloadSdkTests(unittest.TestCase):
    def test_parse_archive_versions_filters_branch(self) -> None:
        html = """
        <a href="26.2.3.1/">26.2.3.1/</a>
        <a href="26.2.4.2/">26.2.4.2/</a>
        <a href="26.8.0.0/">26.8.0.0/</a>
        """
        versions = download_sdk.parse_archive_versions(html, "26.2")
        self.assertEqual(versions, ["26.2.3.1", "26.2.4.2"])

    def test_find_latest_compatible_version_uses_latest_in_branch(self) -> None:
        html = """
        <a href="26.2.1.1/">26.2.1.1/</a>
        <a href="26.2.4.2/">26.2.4.2/</a>
        <a href="26.8.0.0/">26.8.0.0/</a>
        """
        version = download_sdk.find_latest_compatible_version("26.2.0.0", html)
        self.assertEqual(version, "26.2.4.2")

    @patch.object(download_sdk.platform, "machine", return_value="arm64")
    @patch.object(download_sdk.platform, "system", return_value="Darwin")
    def test_detect_sdk_artifact_for_macos_arm64(self, *_mocks) -> None:
        artifact = download_sdk.detect_sdk_artifact("26.2.4.2")
        self.assertEqual(artifact.platform_name, "macos")
        self.assertEqual(artifact.archive_subdir, "mac/aarch64")
        self.assertEqual(artifact.filename, "LibreOffice_26.2.4.2_MacOS_aarch64_sdk.dmg")

    @patch.object(download_sdk.platform, "machine", return_value="x86_64")
    @patch.object(download_sdk.platform, "system", return_value="Linux")
    def test_sdk_url_matches_linux_archive_layout(self, *_mocks) -> None:
        artifact = download_sdk.detect_sdk_artifact("26.2.4.2")
        url = download_sdk.sdk_url("26.2.4.2", artifact)
        self.assertEqual(
            url,
            "https://downloadarchive.documentfoundation.org/libreoffice/old/"
            "26.2.4.2/rpm/x86_64/LibreOffice_26.2.4.2_Linux_x86-64_rpm_sdk.tar.gz",
        )

    @patch.object(download_sdk.platform, "machine", return_value="arm64")
    @patch.object(download_sdk.platform, "system", return_value="Darwin")
    def test_sdk_url_matches_macos_archive_layout(self, *_mocks) -> None:
        artifact = download_sdk.detect_sdk_artifact("26.2.4.2")
        url = download_sdk.sdk_url("26.2.4.2", artifact)
        self.assertEqual(
            url,
            "https://downloadarchive.documentfoundation.org/libreoffice/old/"
            "26.2.4.2/mac/aarch64/LibreOffice_26.2.4.2_MacOS_aarch64_sdk.dmg",
        )


if __name__ == "__main__":
    unittest.main()
