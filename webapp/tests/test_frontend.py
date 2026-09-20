import json
import os
import socket
import tempfile
import threading
import time
import unittest
import subprocess
from html.parser import HTMLParser
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import urlopen

from esl_web.server import create_server


WEBAPP = Path(__file__).resolve().parents[1]
STATIC = WEBAPP / "static"
CHROMIUM = Path("/home/rugent/.cache/ms-playwright/chromium-1234/chrome-linux64/chrome")


class MarkerParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.ids = set()
        self.labels = []
        self.text = []
        self.scripts = []
        self.stylesheets = []
        self.elements = {}

    def handle_starttag(self, tag, attrs):
        values = dict(attrs)
        if values.get("id"):
            self.ids.add(values["id"])
            self.elements[values["id"]] = (tag, values)
        if tag == "script" and values.get("src"):
            self.scripts.append(values["src"])
        if tag == "link" and values.get("rel") == "stylesheet":
            self.stylesheets.append(values.get("href"))

    def handle_data(self, data):
        value = data.strip()
        if value:
            self.text.append(value)


class FrontendSourceTests(unittest.TestCase):
    def test_template_families_require_exact_dimensions_and_screen_type(self):
        result = subprocess.run(
            ["node", str(WEBAPP / "tests" / "template_family.test.js")],
            cwd=WEBAPP, capture_output=True, text=True, check=False,
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_browser_flow_uses_cdp_pointer_actions_for_initiating_controls(self):
        script = (WEBAPP / "tests" / "browser_mutation_flows.test.js").read_text(
            encoding="utf-8"
        )
        self.assertIn('call("DOM.getBoxModel"', script)
        self.assertIn('call("Input.dispatchMouseEvent", { type: "mousePressed"', script)
        self.assertIn('call("Input.dispatchMouseEvent", { type: "mouseReleased"', script)
        self.assertNotIn("requestSubmit", script)
        for forbidden in (
            'byId("auth-button").focus()',
            'byId("save-new-tag").focus()',
            'byId("save-tag-detail").focus()',
            'byId("clone-submit").focus()',
        ):
            self.assertNotIn(forbidden, script)

    def test_clone_guard_blocks_a_second_post_while_first_is_pending(self):
        result = subprocess.run(
            ["node", str(WEBAPP / "tests" / "clone_guard.test.js")],
            cwd=WEBAPP, capture_output=True, text=True, check=False,
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_detail_guard_rejects_stale_or_failed_selection(self):
        result = subprocess.run(
            ["node", str(WEBAPP / "tests" / "detail_guard.test.js")],
            cwd=WEBAPP, capture_output=True, text=True, check=False,
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_dialog_focus_manager_preserves_nested_auth_focus_chain(self):
        result = subprocess.run(
            ["node", str(WEBAPP / "tests" / "dialog_focus.test.js")],
            cwd=WEBAPP, capture_output=True, text=True, check=False,
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

        script = (STATIC / "app.js").read_text(encoding="utf-8")
        self.assertIn("authReturnTarget", script)
        self.assertIn("openAuthModal(authReturnTarget)", script)
        self.assertGreaterEqual(script.count("authReturnTarget: button"), 3)

    def test_dialog_operation_guard_rejects_close_and_stale_completion(self):
        result = subprocess.run(
            ["node", str(WEBAPP / "tests" / "dialog_operation_guard.test.js")],
            cwd=WEBAPP, capture_output=True, text=True, check=False,
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_shell_is_purpose_specific_slovak_esl_navigation(self):
        parser = MarkerParser()
        parser.feed((STATIC / "index.html").read_text(encoding="utf-8"))
        rendered_text = " ".join(parser.text)

        for view in ("Cenovky", "Šablóny", "Controllery", "Audit"):
            self.assertIn(view, rendered_text)
        for clutter in ("Produkty", "Úlohy", "Vytvoriť update job", "Posledné úlohy"):
            self.assertNotIn(clutter, rendered_text)
        for marker in (
            "app-status", "safety-banner", "mobile-nav-toggle", "controller-select",
            "view-tags", "view-templates", "view-controllers", "view-audit", "tag-search",
            "tags-list", "add-tag", "tag-drawer", "tag-detail-form", "tag-test-data",
            "tag-modal", "tag-form", "clone-modal", "clone-form", "clone-confirm",
            "clone-result", "controllers-grid", "auth-modal", "auth-form", "auth-token",
        ):
            self.assertIn(marker, parser.ids)
        self.assertEqual(parser.scripts, [
            "/static/clone-guard.js", "/static/detail-guard.js",
            "/static/dialog-focus.js", "/static/dialog-operation-guard.js",
            "/static/template-family.js", "/static/template-preview.js", "/static/app.js",
        ])
        self.assertEqual(parser.stylesheets, ["/static/styles.css"])
        self.assertIn('<link rel="icon" href="data:,">', (STATIC / "index.html").read_text(encoding="utf-8"))
        self.assertIn("bez fyzického odoslania", rendered_text.lower())

    def test_dialog_dom_has_accessible_labels_and_password_only_token_input(self):
        parser = MarkerParser()
        parser.feed((STATIC / "index.html").read_text(encoding="utf-8"))
        for dialog_id in ("tag-drawer", "tag-modal", "clone-modal", "auth-modal"):
            tag, attrs = parser.elements[dialog_id]
            self.assertEqual(tag, "dialog")
            self.assertIn("aria-labelledby", attrs)
        token_tag, token_attrs = parser.elements["auth-token"]
        self.assertEqual(token_tag, "input")
        self.assertEqual(token_attrs.get("type"), "password")
        self.assertEqual(token_attrs.get("autocomplete"), "off")
        html = (STATIC / "index.html").read_text(encoding="utf-8")
        self.assertEqual(html.count('type="password"'), 1)

    def test_assets_are_offline_safe_xss_safe_and_wire_management_contracts(self):
        html = (STATIC / "index.html").read_text(encoding="utf-8")
        css = (STATIC / "styles.css").read_text(encoding="utf-8")
        script = (STATIC / "app.js").read_text(encoding="utf-8")
        combined = html + css + script

        self.assertNotIn("innerHTML", script)
        self.assertNotIn("http://", combined)
        self.assertNotIn("https://", combined)
        self.assertNotIn("@import", css)
        self.assertIn("textContent", script)
        self.assertIn(":focus-visible", css)
        self.assertIn("height: 48px", css)
        self.assertIn("@media", css)
        self.assertIn(".field-grow{flex:none}", css)
        self.assertIn(".controller-context select{height:48px", css)
        self.assertIn(".button-tertiary{min-height:48px", css)
        self.assertIn(".confirm{min-height:48px", css)
        self.assertIn(".tag-row>.tag-mobile-meta.tag-mobile-meta{display:block", css)
        for endpoint in (
            "/api/controllers", "/api/tags?include_unsupported=true", "/api/tags/staged",
            "/configuration", "/api/templates", "/api/routers", "/api/audit",
            "/api/vendor/templates/clone", "/api/session",
        ):
            self.assertIn(endpoint, script)
        for method in ('method: "POST"', 'method: "PUT"'):
            self.assertIn(method, script)
        self.assertNotIn("/api/dispatch/live", script)
        self.assertNotIn("localStorage", combined)
        self.assertNotIn("sessionStorage", combined)

    def test_source_encodes_models_clone_confirmation_token_cleanup_and_focus_return(self):
        script = (STATIC / "app.js").read_text(encoding="utf-8")
        family_script = (STATIC / "template-family.js").read_text(encoding="utf-8")
        for model in ("2.13TFT-BW", "2.13EPD-BWR", "2.9EPD-BWR"):
            self.assertIn(model, family_script)
        for field in (
            "source_controller_id", "source_template_id", "target_controller_id", "target_name",
        ):
            self.assertIn(field, script)
        self.assertIn("clone-confirm", script)
        self.assertIn("let cloneBusy = false", script)
        self.assertIn("if (cloneBusy) return", script)
        self.assertIn("control.disabled = cloneBusy", script)
        self.assertIn("const detailGuard = new DetailLoadGuard()", script)
        self.assertIn("detailGuard.invalidate()", script)
        self.assertIn('setMessage("templates-state", message, true)', script)
        self.assertIn('setMessage("controllers-state", message, true)', script)
        self.assertIn("clearSessionToken", script)
        self.assertGreaterEqual(script.count("clearSessionToken()"), 4)
        self.assertIn("focusManager.restore(dialog)", script)
        self.assertNotIn("let returnFocus", script)
        self.assertIn("management_supported", script)
        self.assertIn("Nepodporovaná historická cenovka", script)

    def test_startup_keeps_loading_copy_until_inventory_resolves(self):
        script = (STATIC / "app.js").read_text(encoding="utf-8")
        self.assertIn("inventoryLoaded: false", script)
        self.assertIn("if (!state.inventoryLoaded) return", script)
        self.assertIn("state.inventoryLoaded = true", script)
        self.assertLess(script.rfind("loadInventory();"), script.rfind("navigate();"))

    def test_tag_accessible_name_contains_management_context(self):
        script = (STATIC / "app.js").read_text(encoding="utf-8")
        self.assertIn("tag.label || tag.id", script)
        self.assertIn("tag.mac", script)
        self.assertIn("${model}", script)
        self.assertIn('tag.rf_router?.name || "Bez routera"', script)
        self.assertIn("${tag.battery} %", script)
        self.assertIn("${tag.rssi} dBm", script)
        self.assertIn('tag.staged ? "lokálny staging" : "vendor inventár"', script)


class StaticServerTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.server = create_server(
            "127.0.0.1", 0, database_path=Path(self.temporary.name) / "ui.db", seed=True
        )
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.base = f"http://127.0.0.1:{self.server.server_port}"

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=2)
        self.temporary.cleanup()

    def test_root_and_static_assets_are_served_with_safe_types(self):
        cases = (
            ("/", "text/html", b'id="app-shell"'),
            ("/static/styles.css", "text/css", b":focus-visible"),
            ("/static/clone-guard.js", "text/javascript", b"CloneSubmissionGuard"),
            ("/static/detail-guard.js", "text/javascript", b"DetailLoadGuard"),
            ("/static/dialog-focus.js", "text/javascript", b"DialogFocusManager"),
            ("/static/dialog-operation-guard.js", "text/javascript", b"DialogOperationGuard"),
            ("/static/template-family.js", "text/javascript", b"TemplateFamilies"),
            ("/static/template-preview.js", "text/javascript", b"renderTemplatePreview"),
            ("/static/app.js", "text/javascript", b"textContent"),
        )
        for path, content_type, marker in cases:
            with self.subTest(path=path), urlopen(self.base + path, timeout=2) as response:
                self.assertEqual(response.status, 200)
                self.assertEqual(response.headers.get_content_type(), content_type)
                self.assertIn(marker, response.read())
                self.assertEqual(response.headers["X-Content-Type-Options"], "nosniff")

    def test_static_traversal_and_unknown_files_are_not_served(self):
        for path in ("/static/%2e%2e/esl_web/server.py", "/static/missing.js", "/favicon.ico"):
            with self.subTest(path=path), self.assertRaises(HTTPError) as caught:
                urlopen(self.base + path, timeout=2)
            self.assertEqual(caught.exception.code, 404)
            caught.exception.close()

    def test_api_behavior_remains_json(self):
        with urlopen(self.base + "/api/health", timeout=2) as response:
            self.assertEqual(response.headers.get_content_type(), "application/json")
            self.assertIn(b'"status":"ok"', response.read())


@unittest.skipUnless(CHROMIUM.exists(), "local headless Chromium is unavailable")
class BrowserDomIntegrationTests(unittest.TestCase):
    def test_create_detail_and_clone_401_flows_preserve_focus_and_block_pending_close(self):
        with tempfile.TemporaryDirectory() as temporary:
            server = create_server(
                "127.0.0.1", 0, database_path=Path(temporary) / "browser.db",
                seed=True, api_token="A" * 64,
            )
            with server.service.storage.connection() as connection:
                connection.execute(
                    "UPDATE templates SET vendor_id = '1', screen_type = 2 "
                    "WHERE id = 'tpl-default'"
                )
                connection.executemany(
                    "INSERT INTO templates(id, controller_id, vendor_id, name, width, height, "
                    "mapping_type, screen_type) VALUES (?, 'legacy', ?, ?, ?, ?, 0, ?)",
                    [
                        ("wrong-250-epd", "2", "Wrong 250 EPD", 250, 132, 2),
                        ("wrong-296-tft", "3", "Wrong 296 TFT", 296, 128, 1),
                    ],
                )
            server_thread = threading.Thread(target=server.serve_forever, daemon=True)
            server_thread.start()
            base_url = f"http://127.0.0.1:{server.server_port}"
            with socket.socket() as probe:
                probe.bind(("127.0.0.1", 0))
                cdp_port = probe.getsockname()[1]
            browser = subprocess.Popen(
                [str(CHROMIUM),
                 "--headless", "--no-sandbox", "--disable-gpu",
                 "--disable-field-trial-config", "--disable-background-networking",
                 "--disable-background-timer-throttling", "--disable-backgrounding-occluded-windows",
                 "--disable-back-forward-cache", "--disable-breakpad",
                 "--disable-client-side-phishing-detection",
                 "--disable-component-extensions-with-background-pages", "--disable-component-update",
                 "--no-default-browser-check", "--disable-default-apps", "--disable-dev-shm-usage",
                 "--disable-extensions",
                 "--disable-features=HttpsUpgrades,OptimizationHints,Translate",
                 "--disable-hang-monitor", "--disable-ipc-flooding-protection",
                 "--disable-popup-blocking", "--disable-prompt-on-repost",
                 "--disable-renderer-backgrounding", "--force-color-profile=srgb",
                 "--metrics-recording-only", "--no-first-run", "--password-store=basic",
                 "--use-mock-keychain", "--no-service-autorun", "--hide-scrollbars", "--mute-audio",
                 f"--remote-debugging-port={cdp_port}",
                 f"--user-data-dir={Path(temporary) / 'chrome'}", "--no-startup-window"],
                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
            )
            try:
                cdp = f"http://127.0.0.1:{cdp_port}"
                for _attempt in range(80):
                    try:
                        with urlopen(cdp + "/json/version", timeout=0.25):
                            break
                    except OSError:
                        time.sleep(0.025)
                else:
                    self.fail("headless Chromium CDP did not become ready")
                environment = {
                    **os.environ,
                    "ESL_BROWSER_BASE": base_url,
                    "ESL_BROWSER_CDP": cdp,
                }
                result = subprocess.run(
                    ["node", str(WEBAPP / "tests" / "browser_mutation_flows.test.js")],
                    cwd=WEBAPP, env=environment, capture_output=True, text=True,
                    check=False, timeout=30,
                )
                self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            finally:
                browser.terminate()
                try:
                    browser.wait(timeout=3)
                except subprocess.TimeoutExpired:
                    browser.kill()
                    browser.wait(timeout=3)
                server.shutdown()
                server.server_close()
                server_thread.join(timeout=2)


if __name__ == "__main__":
    unittest.main()
