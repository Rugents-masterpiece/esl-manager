import tempfile
import threading
import unittest
from html.parser import HTMLParser
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import urlopen

from esl_web.server import create_server


WEBAPP = Path(__file__).resolve().parents[1]
STATIC = WEBAPP / "static"


class MarkerParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.ids = set()
        self.labels = []
        self.text = []
        self.scripts = []
        self.stylesheets = []

    def handle_starttag(self, tag, attrs):
        values = dict(attrs)
        if values.get("id"):
            self.ids.add(values["id"])
        if tag == "script" and values.get("src"):
            self.scripts.append(values["src"])
        if tag == "link" and values.get("rel") == "stylesheet":
            self.stylesheets.append(values.get("href"))

    def handle_data(self, data):
        value = data.strip()
        if value:
            self.text.append(value)


class FrontendSourceTests(unittest.TestCase):
    def test_shell_has_all_views_accessibility_and_safety_markers(self):
        parser = MarkerParser()
        parser.feed((STATIC / "index.html").read_text(encoding="utf-8"))
        rendered_text = " ".join(parser.text)

        for view in ("Prehľad", "Cenovky", "Produkty", "Šablóny", "Stanice", "Úlohy", "Audit"):
            self.assertIn(view, rendered_text)
        for marker in (
            "app-status", "safety-banner", "mobile-nav-toggle", "view-overview",
            "view-tags", "view-products", "view-templates", "view-routers", "view-jobs",
            "view-audit", "product-modal", "product-form", "tag-search", "tag-status",
            "tag-battery", "tag-signal", "tag-router", "selected-count",
        ):
            self.assertIn(marker, parser.ids)
        self.assertEqual(parser.scripts, ["/static/app.js"])
        self.assertEqual(parser.stylesheets, ["/static/styles.css"])
        self.assertIn("Simulačný režim", rendered_text)
        self.assertNotIn("Vymazať fyzickú cenovku", rendered_text)

    def test_assets_are_offline_safe_and_wire_the_real_api(self):
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
        for endpoint in (
            "/api/dashboard", "/api/tags", "/api/products", "/api/templates", "/api/routers",
            "/api/jobs", "/api/alerts", "/api/audit", "/api/bindings", "/api/sync/read-only",
            "/simulate", "/retry", "/api/products/export.csv",
        ):
            self.assertIn(endpoint, script if endpoint != "/api/products/export.csv" else combined)
        for method in ('method: "POST"', 'method: "PATCH"', 'method: "DELETE"'):
            self.assertIn(method, script)
        self.assertNotIn("/api/dispatch/live", script)
        self.assertNotIn("/api/tags/", script)

    def test_operational_metrics_are_rendered_from_live_values(self):
        script = (STATIC / "app.js").read_text(encoding="utf-8")

        self.assertIn('byId("tag-signal").value', script)
        self.assertIn('progressFill.style.width = `${successRate}%`', script)
        self.assertIn('router.version || router.firmware_version', script)
        self.assertIn('health.mode === "live"', script)
        self.assertIn('health.mode === "read_only"', script)


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


if __name__ == "__main__":
    unittest.main()
