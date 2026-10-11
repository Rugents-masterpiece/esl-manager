"""Disposable real-Chromium regression for HTTP/1.1 native-preview starvation.

Run: PYTHONPATH=webapp python3 -m unittest discover -s webapp/tests \
    -p test_login_preview_browser.py -v
No real vendor, persistent database, credentials, or application restart is used.
"""
import base64
import json
import os
import socket
import subprocess
import tempfile
import threading
import time
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.request import urlopen

import test_frontend as frontend
from esl_web.server import ApiHandler, create_server


class SlowPreviewVendor:
    """Gate native reads before a serialized fake transport, never use the LAN."""
    def __init__(self):
        self.release = threading.Event()
        self.lock = threading.Lock()
        self.transport_lock = threading.Lock()
        self.active = 0
        self.peak = 0
        self.calls = 0
        self.session_posts = 0

    def get_template_metadata(self, style_id):
        return {"id": style_id, "name": f"Preview {style_id - 1000:02}",
                "width": 250, "height": 132, "type": 1, "rotate": 0,
                "backgroundId": 0}

    def get_template_preview(self, style_id):
        with self.lock:
            self.active += 1
            self.calls += 1
            self.peak = max(self.peak, self.active)
        try:
            # All six HTTP handlers can enter while vendor work is serialized.
            # Explicit release avoids timing-dependent 5-second sleeps.
            with self.transport_lock:
                if not self.release.wait(25):
                    raise TimeoutError("test preview release was not signalled")
                return (base64.b64decode(
                    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwC"
                    "AAAAC0lEQVR42mP8/x8AAwMCAO+aX1sAAAAASUVORK5CYII="
                ), "image/png")
        finally:
            with self.lock:
                self.active -= 1


@unittest.skipUnless(frontend.CHROMIUM.exists(), "local headless Chromium is unavailable")
class LoginPreviewBrowserTests(unittest.TestCase):
    def test_login_without_previews_and_cookie_reuse(self):
        self.run_browser("tags")

    def test_login_completes_before_slow_native_previews_are_released(self):
        self.run_browser("templates")

    def run_browser(self, view):
        vendor = SlowPreviewVendor()
        with tempfile.TemporaryDirectory(prefix="esl-login-preview-") as temporary:
            class FixtureRegistry:
                default_id = "legacy"

                def get(self, controller_id=None):
                    if controller_id not in (None, "legacy"):
                        raise KeyError(controller_id)
                    return vendor

                def metadata(self):
                    return [{"id": "legacy", "name": "Disposable controller",
                             "base_url": "http://controller.invalid", "default": True}]

            server = create_server(
                "127.0.0.1", 0, database_path=Path(temporary) / "browser.db",
                seed=True, api_token="A" * 64, controller_registry=FixtureRegistry(),
            )
            # Keep seeded tag references valid, but give only our 43 native styles
            # supported dimensions. Inventory is local; only image reads hit fake vendor.
            with server.service.storage.connection() as connection:
                connection.executemany(
                    "INSERT INTO templates(id, controller_id, vendor_id, name, width, height, "
                    "mapping_type, screen_type) VALUES (?, 'legacy', ?, ?, 250, 132, 0, 1)",
                    [(f"preview-{i:02}", str(1000 + i), f"Preview {i:02}") for i in range(43)],
                )

            class ObservedHandler(ApiHandler):
                def handle(handler):
                    try:
                        super().handle()
                    except ConnectionResetError:
                        # Chromium closes remaining keep-alive image sockets on exit.
                        handler.close_connection = True

                def do_POST(handler):
                    if handler.path == "/api/session":
                        with vendor.lock:
                            vendor.session_posts += 1
                    super().do_POST()

            server.RequestHandlerClass = ObservedHandler

            class ControlHandler(BaseHTTPRequestHandler):
                def log_message(handler, *args):
                    pass

                def do_GET(handler):
                    with vendor.lock, server.session_lock:
                        payload = {"active": vendor.active, "peak": vendor.peak,
                                   "calls": vendor.calls, "session_posts": vendor.session_posts,
                                   "sessions": len(server.sessions),
                                   "released": vendor.release.is_set()}
                    raw = json.dumps(payload).encode()
                    handler.send_response(200)
                    handler.send_header("Content-Type", "application/json")
                    handler.send_header("Content-Length", str(len(raw)))
                    handler.end_headers()
                    handler.wfile.write(raw)

                def do_POST(handler):
                    if handler.path != "/release":
                        handler.send_error(404)
                        return
                    vendor.release.set()
                    handler.send_response(204)
                    handler.end_headers()

            control = ThreadingHTTPServer(("127.0.0.1", 0), ControlHandler)
            threads = [threading.Thread(target=s.serve_forever, daemon=True)
                       for s in (server, control)]
            for thread in threads:
                thread.start()
            with socket.socket() as probe:
                probe.bind(("127.0.0.1", 0))
                cdp_port = probe.getsockname()[1]
            browser = subprocess.Popen(
                [str(frontend.CHROMIUM), "--headless", "--no-sandbox", "--disable-gpu",
                 "--disable-dev-shm-usage", "--disable-background-networking",
                 "--disable-background-timer-throttling", "--disable-extensions",
                 "--no-first-run", "--no-default-browser-check",
                 f"--remote-debugging-port={cdp_port}",
                 f"--user-data-dir={Path(temporary) / 'chrome'}", "--no-startup-window"],
                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
            )
            try:
                cdp = f"http://127.0.0.1:{cdp_port}"
                for _ in range(100):
                    try:
                        with urlopen(cdp + "/json/version", timeout=0.25):
                            break
                    except OSError:
                        time.sleep(0.025)
                else:
                    self.fail("headless Chromium CDP did not become ready")
                result = subprocess.run(
                    ["node", str(frontend.WEBAPP / "tests/login_preview_browser.test.js")],
                    cwd=frontend.WEBAPP,
                    env={**os.environ, "ESL_BROWSER_CDP": cdp,
                         "ESL_BROWSER_BASE": f"http://127.0.0.1:{server.server_port}",
                         "ESL_PREVIEW_CONTROL": f"http://127.0.0.1:{control.server_port}",
                         "ESL_LOGIN_VIEW": view},
                    capture_output=True, text=True, timeout=35, check=False,
                )
                self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
                print(result.stdout.strip())
            finally:
                vendor.release.set()
                browser.terminate()
                try:
                    browser.wait(timeout=3)
                except subprocess.TimeoutExpired:
                    browser.kill()
                    browser.wait(timeout=3)
                for instance in (server, control):
                    instance.shutdown()
                    instance.server_close()
                for thread in threads:
                    thread.join(timeout=2)


if __name__ == "__main__":
    unittest.main()
