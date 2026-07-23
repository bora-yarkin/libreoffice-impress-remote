# SPDX-FileCopyrightText: 2026 Bora Yarkın
# SPDX-License-Identifier: GPL-3.0-only

from pathlib import Path
from io import BytesIO
import sys
import xml.etree.ElementTree as ET
from zipfile import ZipFile

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.build_oxt import DIST, build_oxt, project_version  # noqa: E402

DESCRIPTION_NS = "{http://openoffice.org/extensions/description/2006}"


def test_build_oxt_packages_shared_webui_assets(tmp_path) -> None:
    output = tmp_path / "libreoffice-impress-remote.oxt"

    build_oxt(output)
    version = project_version()
    docs_archive_name = f"resources/impress-remote-docs-{version}.zip"
    relay_archive_name = f"resources/impress-remote-relay-python-{version}.zip"

    with ZipFile(output) as package:
        names = set(package.namelist())

        assert "web/index.html" in names
        assert "web/app.css" in names
        assert "web/app.js" in names
        assert "web/manifest.webmanifest" not in names
        assert "web/sw.js" not in names
        assert "web/icons/remote.svg" not in names
        assert "web/localizations/en.json" in names
        assert "web/localizations/tr.json" in names
        assert "web/localizations/manifest.json" in names
        assert "icons/icon.svg" in names
        assert "descriptions/description-en.txt" in names
        assert "descriptions/description-tr.txt" in names
        assert not any(".DS_Store" in name for name in names)
        index_html = package.read("web/index.html").decode("utf-8")
        asset_manifest = package.read("web/asset-manifest.json").decode("utf-8")
        build_features = package.read("python/impress_remote/BUILD_FEATURES.json").decode("utf-8")
        assert relay_archive_name in names
        assert docs_archive_name in names
        assert not any("impress-remote-relay-cloudflare" in name for name in names)

        relay_data = package.read(relay_archive_name)
        docs_data = package.read(docs_archive_name)
        description_data = package.read("description.xml")

    with ZipFile(BytesIO(relay_data)) as relay_archive:
        assert f"impress-remote-relay-python-{version}/run-relay.py" in relay_archive.namelist()
    with ZipFile(BytesIO(docs_data)) as docs_archive:
        assert f"impress-remote-docs-{version}/README.md" in docs_archive.namelist()

    description = ET.fromstring(description_data)
    version_node = description.find(f"{DESCRIPTION_NS}version")
    assert version_node is not None
    assert version_node.attrib["value"] == version
    assert 'href="/app.css" integrity="sha256-' in index_html
    assert 'src="/app.js" integrity="sha256-' in index_html
    assert "localizations/manifest.json" in asset_manifest
    assert '"localtunnel": true' in build_features
    assert '"relay": true' in build_features


def test_build_oxt_defaults_to_versioned_filename_and_cleans_intermediates() -> None:
    version = project_version()
    output_name = f"libreoffice-impress-remote-{version}.oxt"
    DIST.mkdir(parents=True, exist_ok=True)
    if DIST.exists():
        (DIST / output_name).unlink(missing_ok=True)
        for leftover in (
            DIST / f"impress-remote-relay-python-{version}.zip",
            DIST / f"impress-remote-relay-cloudflare-{version}.zip",
            DIST / f"impress-remote-docs-{version}.zip",
        ):
            leftover.write_text("leftover", encoding="utf-8")
        for leftover_dir in (
            DIST / f"impress-remote-relay-python-{version}",
            DIST / f"impress-remote-relay-cloudflare-{version}",
        ):
            leftover_dir.mkdir(parents=True, exist_ok=True)
            (leftover_dir / "leftover.txt").write_text("leftover", encoding="utf-8")
    before = {path.relative_to(DIST) for path in DIST.rglob("*")} if DIST.exists() else set()

    output = build_oxt()

    try:
        assert output.name == output_name
        assert output.exists()
        after = {path.relative_to(DIST) for path in DIST.rglob("*")} if DIST.exists() else set()
        removed = before - after
        assert Path(f"impress-remote-relay-python-{version}.zip") in removed
        assert Path(f"impress-remote-relay-cloudflare-{version}.zip") in removed
        assert Path(f"impress-remote-docs-{version}.zip") in removed
        assert after - before == {Path(output.name)}
    finally:
        output.unlink(missing_ok=True)
