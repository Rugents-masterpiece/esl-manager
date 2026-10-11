"""Loopback-only regression for modern native array dispatch and detail read-back."""
import json
import os
import threading
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from unittest.mock import patch

from esl_web.vendor import (
    LIVE_WRITE_CONFIRMATION, LiveWritesDisabled, VendorClient, VendorConfig, VendorError,
)


class DispatchWireServer(ThreadingHTTPServer):
    calls: list[tuple[str, str, bytes, str | None]]
    expected_updates: list[dict]
    tag_status: str
    after_status: str
    post_status: int
    native_timestamp: int


class DispatchWireHandler(BaseHTTPRequestHandler):
    server: DispatchWireServer  # type: ignore[reportIncompatibleVariableOverride]

    def log_message(self, format, *args):
        pass

    def respond(self, payload, status=200):
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        self.server.calls.append(("GET", self.path, b"", None))
        if self.path == "/esls_new/tag/getTagById?id=8":
            self.respond({"tag": {"id": 8, "mac": 1548769328, "width": 250, "height": 122,
                                  "styleid": 98, "updateProgress": 5,
                                  "tagAndGood": {"status": self.server.tag_status, "timestamp": self.server.native_timestamp}}})
        elif not self.path.startswith("/esls_new/mms/queryTags?"):
            self.respond(False, 404)
        elif "currentPage=1&" in self.path:
            self.respond({"datalist": [{"id": 8, "mac": "1548769328",
                                        "updateProgress": self.server.tag_status}],
                          "resultCode": 1})
        else:
            self.respond({"datalist": [], "resultCode": 1})

    def do_POST(self):
        body = self.rfile.read(int(self.headers.get("Content-Length", "0")))
        content_type = self.headers.get("Content-Type")
        self.server.calls.append(("POST", self.path, body, content_type))
        try:
            inner = json.loads(body)
            if not isinstance(inner, list) or inner != self.server.expected_updates:
                raise ValueError("Expected inner update array")
        except (ValueError, TypeError):
            self.respond(False, 400)
            return
        if (self.path != "/esls_new/associate/updateScreen"
                or content_type != "application/json"):
            self.respond(False, 400)
            return
        if self.server.post_status != 200:
            self.respond(False, self.server.post_status)
            return
        if self.server.tag_status != self.server.after_status:
            self.server.native_timestamp += 1000
        self.server.tag_status = self.server.after_status
        self.respond(True)


class DispatchWireTests(unittest.TestCase):
    def setUp(self):
        self.updates = [{"mac": "92.80.88.48", "styleid": 136, "mappingtype": 101,
                         "ABDisplayFlag": 163,
                         "Price": 'Čaj 中文 😀 "quoted" \\ path\nnext\tline'}]
        self.server = DispatchWireServer(("127.0.0.1", 0), DispatchWireHandler)
        self.server.calls = []
        self.server.expected_updates = [{k: v for k, v in item.items() if k != "ABDisplayFlag"} for item in self.updates]
        self.server.tag_status = "5"
        self.server.after_status = "4"
        self.server.post_status = 200
        self.server.native_timestamp = 1000
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.client = VendorClient(VendorConfig(
            base_url=f"http://127.0.0.1:{self.server.server_port}/esls_new",
            session="offline-fixture", connect_timeout=2, read_timeout=2,
        ))
        self.client._minimum_request_gap = 0.0
        self.environment = patch.dict(os.environ, {"ESL_LIVE_WRITES": "1"}, clear=True)
        self.environment.start()
        self.addCleanup(self.environment.stop)

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=2)

    def dispatch(self, confirmation=LIVE_WRITE_CONFIRMATION):
        return self.client.update_screen(self.updates, confirmation)

    def posts(self):
        return [call for call in self.server.calls if call[0] == "POST"]

    def test_native_array_roundtrips_unicode_and_escaping_after_one_post(self):
        original = json.loads(json.dumps(self.updates))
        result = self.dispatch()
        self.assertEqual(result[0]["mac"], "92.80.88.48")
        self.assertEqual(result[0]["native_update_progress"], 4)
        self.assertEqual(result[0]["update_progress"], 5)
        self.assertEqual(result[0]["_verified_status"], "success")
        self.assertEqual(self.updates, original)
        self.assertEqual(len(self.posts()), 1)
        method, path, body, content_type = self.posts()[0]
        self.assertEqual((method, path, content_type),
                         ("POST", "/esls_new/associate/updateScreen", "application/json"))
        wire = json.loads(body)
        self.assertIsInstance(wire, list)
        self.assertEqual(wire, self.server.expected_updates)
        self.assertNotIn('ABDisplayFlag', wire[0])
        self.assertIn('Čaj 中文 😀', body.decode("utf-8"))
        self.assertIn(r'\"quoted\"', body.decode("utf-8"))
        self.assertIn(r'\n', body.decode("utf-8"))
        post_index = self.server.calls.index(self.posts()[0])
        self.assertTrue(any(call[0] == "GET" for call in self.server.calls[:post_index]))
        self.assertTrue(any(call[0] == "GET" for call in self.server.calls[post_index + 1:]))

    def test_unchanged_success_or_updating_is_not_verified_or_retried(self):
        for status in ("2", "4"):
            with self.subTest(status=status):
                self.server.calls.clear()
                self.server.tag_status = self.server.after_status = status
                with self.assertRaisesRegex(VendorError, "already-updating" if status == "2" else "did not confirm"):
                    self.dispatch()
                self.assertEqual(len(self.posts()), 0 if status == "2" else 1)
                self.assertEqual(len([call for call in self.server.calls
                                      if call[0] == "GET"]), 3 if status == "2" else 6)

    def test_http_failure_is_not_retried_or_followed_by_success_readback(self):
        self.server.post_status = 500
        with self.assertRaisesRegex(VendorError, "HTTP 500"):
            self.dispatch()
        self.assertEqual(len(self.posts()), 1)
        self.assertEqual(self.server.calls[-1][0], "POST")
        self.assertEqual(self.server.tag_status, "5")

    def test_both_exact_gates_are_required_before_any_http_request(self):
        for flag, confirmation in ((None, LIVE_WRITE_CONFIRMATION),
                                   ("0", LIVE_WRITE_CONFIRMATION),
                                   ("true", LIVE_WRITE_CONFIRMATION),
                                   ("1", "wrong"),
                                   ("1", LIVE_WRITE_CONFIRMATION + " ")):
            environment = {} if flag is None else {"ESL_LIVE_WRITES": flag}
            with self.subTest(flag=flag, confirmation=confirmation), patch.dict(
                    os.environ, environment, clear=True):
                with self.assertRaises(LiveWritesDisabled):
                    self.dispatch(confirmation)
                self.assertEqual(self.server.calls, [])


if __name__ == "__main__":
    unittest.main()
