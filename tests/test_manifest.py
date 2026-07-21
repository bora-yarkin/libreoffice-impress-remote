# SPDX-FileCopyrightText: 2026 Bora Yarkın
# SPDX-License-Identifier: GPL-3.0-only

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
        "extension/python/impress_remote/component.py",
        "shared/webui/index.html",
        "localizations/en.json",
        "localizations/tr.json",
        "docs/test-before-release.md",
    ]
    missing = [path for path in required if not (ROOT / path).exists()]
    assert not missing


def test_python_component_manifest_entry_uses_python_component_media_type() -> None:
    manifest = (ROOT / "extension/META-INF/manifest.xml").read_text(encoding="utf-8")
    assert 'application/vnd.sun.star.uno-component;type=Python' in manifest


def test_extension_manifest_includes_settings_schema_and_data() -> None:
    manifest = (ROOT / "extension/META-INF/manifest.xml").read_text(encoding="utf-8")
    assert 'application/vnd.sun.star.configuration-schema' in manifest
    assert 'manifest:full-path="Settings.xcs"' in manifest
    assert 'manifest:full-path="Settings.xcu"' in manifest


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
        "python -m ruff check extension/python server/src server/tests tests tools",
        "python -m pytest tests server/tests",
        "python tools/build_oxt.py",
        "python tools/build_release_bundle.py",
        "python tools/build_cloudflare_bundle.py",
        "dist/impress-remote-relay-python-*.zip",
        "dist/impress-remote-relay-cloudflare-*.zip",
    ):
        assert expected in workflow


def test_release_testing_checklist_is_linked_and_route_complete() -> None:
    docs_index = (ROOT / "docs/README.md").read_text(encoding="utf-8")
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    release_readiness = (ROOT / "docs/release-readiness.md").read_text(encoding="utf-8")
    checklist = (ROOT / "docs/test-before-release.md").read_text(encoding="utf-8")

    assert "test-before-release.md" in docs_index
    assert "docs/test-before-release.md" in readme
    assert "test-before-release.md" in release_readiness
    for expected_section in (
        "## Local Same-Wi-Fi Mode",
        "## Hotspot Local Mode",
        "## Safari Local Compatibility",
        "## Direct IPv6 Mode",
        "## Python Relay Mode",
        "## Cloudflare Relay Mode",
        "## Localization",
        "## Security And Protocol",
    ):
        assert expected_section in checklist
