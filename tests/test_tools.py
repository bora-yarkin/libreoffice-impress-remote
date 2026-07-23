# SPDX-FileCopyrightText: 2026 Bora Yarkın
# SPDX-License-Identifier: GPL-3.0-only
# ruff: noqa: E402,F811

from pathlib import Path
from io import BytesIO
import sys
import xml.etree.ElementTree as ET
from zipfile import ZipFile

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.release import DIST, build_oxt, build_bundle, project_version  # noqa: E402

DESCRIPTION_NS = "{http://openoffice.org/extensions/description/2006}"


def test_build_oxt_packages_shared_webui_assets(tmp_path) -> None:
    output = tmp_path / "libreoffice-impress-remote.oxt"

    build_oxt(output)
    version = project_version()
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
        assert "resources/user-guide.md" in names
        assert not any(".DS_Store" in name for name in names)
        index_html = package.read("web/index.html").decode("utf-8")
        asset_manifest = package.read("web/asset-manifest.json").decode("utf-8")
        build_features = package.read("python/impress_remote/BUILD_FEATURES.json").decode("utf-8")
        user_guide = package.read("resources/user-guide.md").decode("utf-8")
        assert relay_archive_name in names
        resource_archives = [
            name for name in names if name.startswith("resources/") and name.endswith(".zip")
        ]
        assert resource_archives == [relay_archive_name]
        assert all(
            not name.startswith("resources/impress-remote-relay-")
            or name == relay_archive_name
            for name in names
        )

        relay_data = package.read(relay_archive_name)
        description_data = package.read("description.xml")

    with ZipFile(BytesIO(relay_data)) as relay_archive:
        relay_names = set(relay_archive.namelist())
        bundle_root = f"impress-remote-relay-python-{version}/"
        root_files = {
            name.removeprefix(bundle_root)
            for name in relay_names
            if name.startswith(bundle_root)
            and "/" not in name.removeprefix(bundle_root).strip("/")
        }
        assert root_files == {"configure.sh", "configure.ps1"}
        assert f"{bundle_root}relay-runtime/run-relay.py" in relay_names

    description = ET.fromstring(description_data)
    version_node = description.find(f"{DESCRIPTION_NS}version")
    assert version_node is not None
    assert version_node.attrib["value"] == version
    assert 'href="/app.css" integrity="sha256-' in index_html
    assert 'src="/app.js" integrity="sha256-' in index_html
    assert "localizations/manifest.json" in asset_manifest
    assert '"localtunnel": true' in build_features
    assert '"relay": true' in build_features
    assert "# User Guide" in user_guide


def test_build_oxt_defaults_to_versioned_filename_and_cleans_intermediates() -> None:
    version = project_version()
    output_name = f"libreoffice-impress-remote-{version}.oxt"
    DIST.mkdir(parents=True, exist_ok=True)
    if DIST.exists():
        (DIST / output_name).unlink(missing_ok=True)
        leftover = DIST / f"impress-remote-relay-python-{version}.zip"
        leftover.write_text("leftover", encoding="utf-8")
        for leftover_dir in (DIST / f"impress-remote-relay-python-{version}",):
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
        assert after - before == {Path(output.name)}
    finally:
        output.unlink(missing_ok=True)


from pathlib import Path
import sys
from zipfile import ZipFile

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def test_build_release_bundle_contains_only_relay_runtime_assets(tmp_path) -> None:
    dist_dir = ROOT / "dist"
    if dist_dir.exists():
        before = {path.relative_to(dist_dir) for path in dist_dir.rglob("*")}
    else:
        before = set()

    try:
        bundle_dir, archive_path = build_bundle()
        bundle_name = bundle_dir.name
        with ZipFile(archive_path) as archive:
            names = set(archive.namelist())
        root_files = {
            name.removeprefix(f"{bundle_name}/")
            for name in names
            if name.startswith(f"{bundle_name}/")
            and "/" not in name.removeprefix(f"{bundle_name}/").strip("/")
        }
        assert root_files == {"configure.sh", "configure.ps1"}
        assert f"{bundle_name}/relay-runtime/LICENSE" in names
        assert f"{bundle_name}/relay-runtime/run-relay.py" in names
        assert f"{bundle_name}/relay-runtime/install-linux-service.sh" not in names
        assert f"{bundle_name}/relay-runtime/install-windows-service.ps1" not in names
        assert f"{bundle_name}/relay-runtime/uninstall-linux-service.sh" not in names
        assert f"{bundle_name}/relay-runtime/uninstall-windows-service.ps1" not in names
        assert f"{bundle_name}/relay-runtime/run-relay.sh" not in names
        assert f"{bundle_name}/relay-runtime/run-relay.ps1" not in names
        assert f"{bundle_name}/relay-runtime/relay/web/index.html" in names
        assert f"{bundle_name}/relay-runtime/relay/web/app.js" in names
        assert f"{bundle_name}/relay-runtime/relay/web/manifest.webmanifest" not in names
        assert f"{bundle_name}/relay-runtime/relay/web/sw.js" not in names
        assert f"{bundle_name}/relay-runtime/relay/web/icons/remote.svg" not in names
        assert f"{bundle_name}/relay-runtime/relay/web/localizations/en.json" in names
        assert f"{bundle_name}/relay-runtime/relay/web/localizations/tr.json" in names
        assert all(not name.endswith(".oxt") for name in names)
        assert all("/shared/" not in name for name in names)
        assert all("__pycache__/" not in name for name in names)
        assert all(not name.endswith((".pyc", ".pyo")) for name in names)
    finally:
        if dist_dir.exists():
            for path in sorted(dist_dir.rglob("*"), reverse=True):
                relative = path.relative_to(dist_dir)
                if relative not in before:
                    if path.is_file():
                        path.unlink()
                    elif path.is_dir():
                        path.rmdir()


import json

import pytest

from tools.import_localizations import (
    LocalizationImportError,
    import_translation,
    normalize_locale_tag,
)


def test_normalizes_locale_tags_for_imported_catalogs() -> None:
    assert normalize_locale_tag("pt_br") == "pt-BR"
    assert normalize_locale_tag("tr") == "tr"


def test_import_translation_writes_validated_catalog(tmp_path) -> None:
    source = {
        "hello": "Hello {name}",
        "bye": "Bye",
    }
    translation = tmp_path / "de.json"
    translation.write_text(
        json.dumps({"hello": "Hallo {name}", "bye": "Tschuss"}),
        encoding="utf-8",
    )

    output = import_translation(translation, source_catalog=source, output_dir=tmp_path / "out")

    assert output.name == "de.json"
    assert json.loads(output.read_text(encoding="utf-8"))["hello"] == "Hallo {name}"


def test_import_translation_rejects_placeholder_mismatches(tmp_path) -> None:
    translation = tmp_path / "es.json"
    translation.write_text(json.dumps({"hello": "Hola {nombre}"}), encoding="utf-8")

    with pytest.raises(LocalizationImportError):
        import_translation(
            translation,
            source_catalog={"hello": "Hello {name}"},
            output_dir=tmp_path / "out",
        )


from pathlib import Path
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
OOR = "{http://openoffice.org/2001/registry}"


def _node_xpath(name: str) -> str:
    return f"node[@{OOR}name='{name}']"


def test_extension_manifest_files_exist() -> None:
    required = [
        "extension/META-INF/manifest.xml",
        "extension/description.xml",
        "extension/Addons.xcu",
        "extension/ProtocolHandler.xcu",
        "extension/Settings.xcs",
        "extension/Settings.xcu",
        "extension/icons/icon.svg",
        "extension/descriptions/description-en.txt",
        "extension/descriptions/description-tr.txt",
        "extension/python/impress_remote/component.py",
        "shared/webui/index.html",
        "shared/localizations/en.json",
        "shared/localizations/tr.json",
        "docs/user-guide.md",
        "docs/technical-reference.md",
    ]
    missing = [path for path in required if not (ROOT / path).exists()]
    assert not missing


def test_libreoffice_settings_exposes_only_python_relay_export_and_user_guide_help() -> None:
    office_ui = (ROOT / "extension/python/impress_remote/office_ui.py").read_text(
        encoding="utf-8"
    )
    english = (ROOT / "shared/localizations/en.json").read_text(encoding="utf-8")
    turkish = (ROOT / "shared/localizations/tr.json").read_text(encoding="utf-8")

    assert "export_relay_button" in office_ui
    assert "read_packaged_user_guide" in office_ui
    assert "render_user_guide_html" in office_ui
    assert "open_rendered_user_guide" in office_ui
    assert "deploy_" not in office_ui
    for content in (english, turkish):
        assert "office.button.exportRelay" in content


def test_python_component_manifest_entry_uses_python_component_media_type() -> None:
    manifest = (ROOT / "extension/META-INF/manifest.xml").read_text(encoding="utf-8")
    assert 'application/vnd.sun.star.uno-component;type=Python' in manifest


def test_extension_manifest_includes_settings_schema_and_data() -> None:
    manifest = (ROOT / "extension/META-INF/manifest.xml").read_text(encoding="utf-8")
    assert 'application/vnd.sun.star.configuration-schema' in manifest
    assert 'manifest:full-path="Settings.xcs"' in manifest
    assert 'manifest:full-path="Settings.xcu"' in manifest


def test_extension_description_has_install_metadata() -> None:
    description = (ROOT / "extension/description.xml").read_text(encoding="utf-8")

    assert "<display-name>" in description
    assert "<publisher>" in description
    assert '<default xlink:href="icons/icon.svg"/>' in description
    assert 'xlink:href="descriptions/description-en.txt"' in description
    assert 'xlink:href="descriptions/description-tr.txt"' in description


def test_packaged_resource_map_includes_only_relay_bundle() -> None:
    resources = (ROOT / "extension/python/impress_remote/office_ui.py").read_text(
        encoding="utf-8"
    )

    assert '"relay": f"impress-remote-relay-python-' in resources
    assert resources.count("RESOURCE_ARCHIVES = {") == 1


def test_addons_merge_into_impress_slideshow_menu_and_toolbars() -> None:
    addons = ET.parse(ROOT / "extension/Addons.xcu")
    root = addons.getroot()
    addon_ui = root.find(f".//{_node_xpath('AddonUI')}")
    assert addon_ui is not None

    assert addon_ui.find(_node_xpath("OfficeMenuBar")) is None
    assert addon_ui.find(_node_xpath("OfficeMenuBarMerging")) is not None
    assert addon_ui.find(_node_xpath("OfficeToolbarMerging")) is not None

    xml = (ROOT / "extension/Addons.xcu").read_text(encoding="utf-8")
    assert ".uno:SlideShowMenu\\.uno:PresentationCurrentSlide" in xml
    assert "standardbar" in xml
    assert "singlemode" in xml
    assert "notebookbarshortcuts" in xml
    assert xml.count("com.sun.star.presentation.PresentationDocument") >= 8
    assert xml.count("private:separator") >= 2
    assert "separator_before_remote" in xml
    assert "separator_after_remote" in xml
    assert "vnd.org.borayarkin.impressremote:toggle" in xml
    assert "vnd.org.borayarkin.impressremote:settings" in xml


def test_shared_phone_ui_does_not_call_plaintext_local_control_endpoints() -> None:
    app_js = (ROOT / "shared/webui/app.js").read_text(encoding="utf-8")

    for endpoint in (
        "/api/state",
        "/api/events",
        "/api/command",
        "/api/slide/current",
        "/api/slide/next",
    ):
        assert endpoint not in app_js


def test_shared_phone_ui_has_authenticated_local_compatibility_fallback() -> None:
    app_js = (ROOT / "shared/webui/app.js").read_text(encoding="utf-8")

    assert "/api/local/state" in app_js
    assert "/api/local/command" in app_js
    assert "X-Impress-Remote-Session" in app_js
    assert "X-Impress-Remote-Secret" in app_js
    assert "isLocalFallbackMode()" in app_js
    assert "(isLocalMode() || routeMode === 'ipv6') && !hasWebCrypto()" in app_js


def test_shared_phone_ui_loads_dynamic_localization_manifest() -> None:
    app_js = (ROOT / "shared/webui/app.js").read_text(encoding="utf-8")

    assert "/localizations/manifest.json" in app_js
    assert "let supportedLocales = new Set([DEFAULT_LOCALE])" in app_js
    assert "SUPPORTED_LOCALES" not in app_js


def test_shared_phone_ui_is_not_installable_pwa_shell() -> None:
    index_html = (ROOT / "shared/webui/index.html").read_text(encoding="utf-8")
    app_js = (ROOT / "shared/webui/app.js").read_text(encoding="utf-8")

    assert 'rel="manifest"' not in index_html
    assert "apple-mobile-web-app" not in index_html
    assert "serviceWorker" not in app_js
    assert not (ROOT / "shared/webui/manifest.webmanifest").exists()
    assert not (ROOT / "shared/webui/sw.js").exists()


def test_shared_phone_ui_exposes_presentation_controls_without_settings() -> None:
    index_html = (ROOT / "shared/webui/index.html").read_text(encoding="utf-8")
    app_js = (ROOT / "shared/webui/app.js").read_text(encoding="utf-8")

    for command in ("goto_first_slide", "goto_last_slide"):
        assert command in index_html
    for removed_command in (
        "start_presentation_from_first_slide",
        "previous_effect",
        "next_effect",
        "blank-button",
        "blank_screen",
        "resume_presentation",
        "end_presentation",
    ):
        assert removed_command not in index_html
        assert removed_command not in app_js
    assert "fullscreen-button" in index_html
    assert "side-controls-left" in index_html
    assert "side-controls-right" in index_html
    assert "timer-toggle-button" in index_html
    assert "goto-input" in index_html
    assert "total-timer-chip" in index_html
    assert "slide-timer-chip" in index_html
    assert "goto_slide" in app_js
    assert "currentTimerValues" in app_js
    assert "slideTimerBaseMs" in app_js
    assert "totalTimerRunning" in app_js
    assert "if(!totalTimerRunning)" in app_js
    assert "totalTimerBaseSeconds = Number(state.elapsedSeconds" not in app_js
    assert "requestFullscreenMode" in app_js
    assert "screen.orientation.lock('landscape')" in app_js
    assert "presentation-fullscreen" in app_js
    assert "relayState.connectTimeoutTimer" in app_js
    assert "web.relayConnectionTimeout" in app_js
    assert "/api/config" not in app_js


def test_shared_phone_ui_binds_direct_requests_to_pairing_session() -> None:
    app_js = (ROOT / "shared/webui/app.js").read_text(encoding="utf-8")

    assert "function directSessionUrl(path)" in app_js
    assert "url.searchParams.set('s', routeSession)" in app_js
    assert "directSessionUrl('/api/direct/state')" in app_js
    assert "directSessionUrl('/api/direct/events')" in app_js
    assert "directSessionUrl('/api/direct/command')" in app_js


def test_shared_phone_ui_uses_ecdh_bootstrap_for_encrypted_transport() -> None:
    app_js = (ROOT / "shared/webui/app.js").read_text(encoding="utf-8")

    assert "{name: 'ECDH', namedCurve: 'P-256'}" in app_js
    assert "role: 'phone'" in app_js
    assert "pub: bytesToBase64Url(phonePublicKey)" in app_js
    assert "ECDH-P256+HKDF-SHA256+AES-256-GCM" in app_js
    assert "fetchJson(directSessionUrl('/api/direct/handshake'), {" in app_js


def test_product_ci_uploads_the_versioned_oxt_artifact() -> None:
    workflow = (ROOT / ".github/workflows/ci.yml").read_text(encoding="utf-8")

    assert "dist/libreoffice-impress-remote-*.oxt" in workflow
    assert "dist/libreoffice-impress-remote.oxt" not in workflow


def test_product_ci_runs_release_readiness_checks() -> None:
    workflow = (ROOT / ".github/workflows/ci.yml").read_text(encoding="utf-8")

    for expected in (
        "python -m ruff check extension/python relay tests tools",
        "python -m pytest tests",
        "python -m tools.release oxt",
    ):
        assert expected in workflow

    for removed in ("dist/impress-remote-relay-python-*.zip",):
        assert removed not in workflow


def test_release_workflow_publishes_versioned_oxt_after_gates() -> None:
    workflow = (ROOT / ".github/workflows/release.yml").read_text(encoding="utf-8")

    for expected in (
        "python -m ruff check extension/python relay tests tools",
        "python -m pytest tests",
        "python -m tools.release oxt",
        "sha256sum \"libreoffice-impress-remote-${version}.oxt\" > SHA256SUMS",
        "gh release create",
        "gh release upload",
        "dist/libreoffice-impress-remote-${version}.oxt",
    ):
        assert expected in workflow

    assert "contents: write" in workflow
    assert "Release tag ${tag} does not match VERSION ${version}" in workflow


def test_documentation_links_are_direct_and_release_gate_is_inline() -> None:
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    technical_reference = (ROOT / "docs/technical-reference.md").read_text(
        encoding="utf-8"
    )

    assert "docs/user-guide.md" in readme
    assert "docs/technical-reference.md" in readme
    assert "test-before-release.md" not in readme
    assert "test-before-release.md" not in technical_reference
    assert "## Contents" in technical_reference
    for expected_line in (
        "run `make clean`, `make venv`, `make lint`, `make test`, and `make oxt`",
        "install the generated OXT in LibreOffice Impress",
        "test local same-Wi-Fi or hotspot pairing with a real phone",
        "update `CHANGELOG.md`",
    ):
        assert expected_line in technical_reference


from pathlib import Path
import runpy

ROOT = Path(__file__).resolve().parents[1]


def test_tool_scripts_can_be_loaded_like_direct_entrypoints() -> None:
    for script in (
        "tools/release.py",
        "tools/import_localizations.py",
        "tools/validate_relay_compat.py",
    ):
        runpy.run_path(str(ROOT / script), run_name="not_main")


from tools.validate_relay_compat import check_asset_manifest


def test_asset_manifest_compatibility_check_accepts_required_files(monkeypatch) -> None:
    def fake_read_json(_url: str):
        return 200, {
            "files": {
                "index.html": {},
                "app.js": {},
                "app.css": {},
                "localizations/manifest.json": {},
            }
        }

    monkeypatch.setattr("tools.validate_relay_compat.read_json", fake_read_json)

    result = check_asset_manifest("https://relay.example/")

    assert result.ok
    assert result.name == "asset-manifest"
