# SPDX-FileCopyrightText: 2026 Bora Yarkın
# SPDX-License-Identifier: GPL-3.0-only

from pathlib import Path
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[2]
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
        "docs/test-before-release.md",
        "deploy/cloudflare/package.json",
        "deploy/cloudflare/scripts/sync-shared-webui.mjs",
        "deploy/cloudflare/dashboard-worker.mjs",
        "tools/build_cloudflare_dashboard_worker.py",
    ]
    missing = [path for path in required if not (ROOT / path).exists()]
    assert not missing


def test_libreoffice_settings_exposes_cloudflare_deploy_button_not_bundle_export() -> None:
    office_ui = (ROOT / "extension/python/impress_remote/office_ui.py").read_text(
        encoding="utf-8"
    )
    english = (ROOT / "shared/localizations/en.json").read_text(encoding="utf-8")
    turkish = (ROOT / "shared/localizations/tr.json").read_text(encoding="utf-8")

    assert "CLOUDFLARE_DEPLOY_URL" in office_ui
    assert "deploy_cloudflare_button" in office_ui
    assert "open_external_url(self.ctx, CLOUDFLARE_DEPLOY_URL)" in office_ui
    assert "#cloudflare-dashboard-deploy" in office_ui
    assert "deploy.workers.cloudflare.com" not in office_ui
    assert "export_cloudflare_button" not in office_ui
    assert '"office.button.deployCloudflare": "Deploy to Cloudflare"' in english
    assert '"office.button.deployCloudflare": "Cloudflare' in turkish
    assert "office.button.exportCloudflare" not in english
    assert "office.button.exportCloudflare" not in turkish


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
        "python -m ruff check extension/python server/src tests tools",
        "python -m pytest tests",
        "python tools/build_oxt.py",
    ):
        assert expected in workflow

    for removed in (
        "python tools/build_oxt.py --relay-enabled",
        "python tools/build_release_bundle.py",
        "python tools/build_cloudflare_bundle.py",
        "dist/impress-remote-relay-python-*.zip",
        "dist/impress-remote-relay-cloudflare-*.zip",
    ):
        assert removed not in workflow


def test_release_workflow_publishes_versioned_oxt_after_gates() -> None:
    workflow = (ROOT / ".github/workflows/release.yml").read_text(encoding="utf-8")

    for expected in (
        "python -m ruff check extension/python server/src tests tools",
        "python -m pytest tests",
        "python tools/build_oxt.py",
        "sha256sum \"libreoffice-impress-remote-${version}.oxt\" > SHA256SUMS",
        "gh release create",
        "gh release upload",
        "dist/libreoffice-impress-remote-${version}.oxt",
    ):
        assert expected in workflow

    assert "contents: write" in workflow
    assert "Release tag ${tag} does not match VERSION ${version}" in workflow


def test_cloudflare_relay_has_account_only_dashboard_deploy_without_duplicate_webui() -> None:
    from tools.build_cloudflare_dashboard_worker import build_dashboard_worker_text

    package = (ROOT / "deploy/cloudflare/package.json").read_text(encoding="utf-8")
    sync_script = (ROOT / "deploy/cloudflare/scripts/sync-shared-webui.mjs").read_text(
        encoding="utf-8"
    )
    dashboard_worker = (ROOT / "deploy/cloudflare/dashboard-worker.mjs").read_text(
        encoding="utf-8"
    )
    readme = (ROOT / "deploy/cloudflare/README.md").read_text(encoding="utf-8")
    docs = (ROOT / "docs/relay.md").read_text(encoding="utf-8")
    product_readme = (ROOT / "README.md").read_text(encoding="utf-8")
    user_guide = (ROOT / "docs/user-guide.md").read_text(encoding="utf-8")

    assert dashboard_worker == build_dashboard_worker_text()
    for expected in (
        '"build": "node scripts/sync-shared-webui.mjs"',
        '"predeploy": "npm run build"',
        '"deploy": "wrangler deploy"',
    ):
        assert expected in package
    for expected in (
        "raw.githubusercontent.com",
        "webui/${file}",
        "shared/localizations",
        "asset-manifest.json",
        "localizations/manifest.json",
    ):
        assert expected in sync_script
    for expected in (
        "Generated by tools/build_cloudflare_dashboard_worker.py",
        "export class RelayRoom",
        "const EMBEDDED_ASSETS",
        "serveEmbeddedAsset(request)",
        '"/index.html"',
        '"/app.js"',
        '"/app.css"',
        '"/asset-manifest.json"',
        '"/localizations/manifest.json"',
    ):
        assert expected in dashboard_worker
    assert "env.ASSETS.fetch" not in dashboard_worker
    assert "deploy.workers.cloudflare.com" not in readme
    assert "deploy.workers.cloudflare.com" not in docs
    assert "deploy.workers.cloudflare.com" not in product_readme
    assert "Cloudflare Dashboard Deploy" in readme
    assert "Cloudflare Dashboard Deploy" in docs
    assert "dashboard-worker.mjs" in readme
    assert "dashboard-worker.mjs" in docs
    assert (
        "Cloudflare relay can be deployed from the linked relay docs with only a Cloudflare "
        "account"
        in user_guide
    )
    assert not (ROOT / "deploy/cloudflare/public").exists()


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
        "## LocalTunnel Mode",
        "## Direct IPv6 Mode",
        "## Python Relay Mode",
        "## Cloudflare Relay Mode",
        "## Localization",
        "## Security And Protocol",
    ):
        assert expected_section in checklist
