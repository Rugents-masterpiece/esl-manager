import hashlib
import json
import os
import tempfile
import threading
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from unittest.mock import patch
from urllib.error import HTTPError
from urllib.parse import parse_qs
from urllib.request import Request, urlopen

from esl_web.server import create_server
from esl_web.vendor import (
    LIVE_WRITE_CONFIRMATION,
    VendorClient,
    VendorConfig,
    VendorConfigurationError,
    decode_response,
)


class DecoderTests(unittest.TestCase):
    def test_decodes_supported_vendor_response_shapes(self):
        cases = (
            ('[{"id":1}]', [{"id": 1}]),
            (json.dumps('[{"id":2}]'), [{"id": 2}]),
            ('{"datalist":[{"id":3}],"resultCode":10}', [{"id": 3}]),
            ("true", True),
            ("plain response", "plain response"),
        )
        for raw, expected in cases:
            with self.subTest(raw=raw):
                self.assertEqual(decode_response(raw), expected)

    def test_decodes_utf8_bytes_and_rejects_invalid_utf8(self):
        self.assertEqual(decode_response('čaj'.encode()), "čaj")
        with self.assertRaises(ValueError):
            decode_response(b"\xff")


class ConfigurationTests(unittest.TestCase):
    def test_configuration_loads_credentials_session_and_timeouts(self):
        config = VendorConfig.from_env({
            "ESL_BASE_URL": "http://127.0.0.1:8080/esls_new/",
            "ESL_USERNAME": "operator",
            "ESL_PASSWORD": "secret",
            "ESL_SESSION": "session-token",
            "ESL_CONNECT_TIMEOUT": "1.5",
            "ESL_READ_TIMEOUT": "4",
        })
        self.assertEqual(config.base_url, "http://127.0.0.1:8080/esls_new")
        self.assertEqual(config.username, "operator")
        self.assertEqual(config.password, "secret")
        self.assertEqual(config.session, "session-token")
        self.assertEqual((config.connect_timeout, config.read_timeout), (1.5, 4.0))

    def test_configuration_rejects_unsafe_urls_credentials_and_timeouts(self):
        invalid_environments = (
            {},
            {"ESL_BASE_URL": "file:///tmp/controller"},
            {"ESL_BASE_URL": "http://user:pass@127.0.0.1/esls_new"},
            {"ESL_BASE_URL": "http://127.0.0.1/esls_new?redirect=evil"},
            {"ESL_BASE_URL": "http://127.0.0.1/esls_new#fragment"},
            {"ESL_BASE_URL": "http://127.0.0.1/esls_new", "ESL_USERNAME": "only-user"},
            {"ESL_BASE_URL": "http://127.0.0.1/esls_new", "ESL_SESSION": "bad\r\ncookie"},
            {"ESL_BASE_URL": "http://127.0.0.1/esls_new", "ESL_CONNECT_TIMEOUT": "0"},
            {"ESL_BASE_URL": "http://127.0.0.1/esls_new", "ESL_READ_TIMEOUT": "nan"},
        )
        for environment in invalid_environments:
            with self.subTest(environment=environment), self.assertRaises(VendorConfigurationError):
                VendorConfig.from_env(environment)

    def test_direct_configuration_cannot_bypass_url_or_timeout_validation(self):
        with self.assertRaises(VendorConfigurationError):
            VendorConfig("file:///tmp/controller")
        with self.assertRaises(VendorConfigurationError):
            VendorConfig("http://127.0.0.1/esls_new", connect_timeout=0)


class FakeVendorHandler(BaseHTTPRequestHandler):
    calls = []
    update_status = 200
    expected_updates = []
    tag_status = 1

    def log_message(self, format, *args):
        return

    def _send(self, payload, *, cookie=None):
        body = payload if isinstance(payload, bytes) else payload.encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        if cookie:
            self.send_header("Set-Cookie", cookie)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_POST(self):
        length = int(self.headers.get("Content-Length", "0"))
        body = self.rfile.read(length)
        self.__class__.calls.append(("POST", self.path, self.headers.get("Cookie"), body))
        if self.path == "/esls_new/login/userLogin":
            self.assert_login(body)
            self._send("true", cookie="JSESSIONID=fake-login; Path=/esls_new; HttpOnly")
            return
        if self.path == "/esls_new/associate/updateScreen":
            if self.headers.get("Cookie") != "JSESSIONID=fake-login":
                self.send_error(401)
                return
            if json.loads(body) != self.__class__.expected_updates:
                self.send_error(400)
                return
            if self.__class__.update_status == 500:
                self.send_error(500)
                return
            self._send("true")
            return
        self.send_error(404)

    def assert_login(self, body):
        values = parse_qs(body.decode())
        expected = hashlib.md5(b"secret").hexdigest()
        if values != {"username": ["operator"], "passwd": [expected]}:
            self.send_error(400)
            raise AssertionError(values)

    def do_GET(self):
        self.__class__.calls.append(("GET", self.path, self.headers.get("Cookie"), b""))
        if self.headers.get("Cookie") != "JSESSIONID=fake-login":
            self.send_error(401)
            return
        if self.path == "/esls_new/associate/getRoutersMsg":
            self._send(json.dumps([{
                "routerID": 8, "routerIP": "127.0.0.8", "state": 1,
                "lastHeartbeatTime": 1579163376000,
            }]))
        elif self.path == "/esls_new/associate/getStyleMsgs":
            self._send(json.dumps({"datalist": [{
                "id": 136, "name": "Vendor template", "width": 296,
                "height": 128, "mappingtype": 101,
            }], "resultCode": 10}))
        elif self.path == "/esls_new/associate/getTagsMsg":
            tags = [{
                "mac": "92.91.87.80", "power": 100, "rssi": -54.0,
                "status": self.__class__.tag_status, "routerid": "8", "styleId": 136,
                "width": 296, "height": 128, "showStyle": "Vendor template",
            }]
            self._send(json.dumps(json.dumps(tags)))
        else:
            self.send_error(404)


class ReadOnlySyncTests(unittest.TestCase):
    def setUp(self):
        FakeVendorHandler.calls = []
        FakeVendorHandler.update_status = 200
        FakeVendorHandler.expected_updates = []
        FakeVendorHandler.tag_status = 1
        self.vendor_server = ThreadingHTTPServer(("127.0.0.1", 0), FakeVendorHandler)
        self.vendor_thread = threading.Thread(target=self.vendor_server.serve_forever, daemon=True)
        self.vendor_thread.start()
        self.temporary = tempfile.TemporaryDirectory()
        config = VendorConfig(
            f"http://127.0.0.1:{self.vendor_server.server_port}/esls_new",
            username="operator", password="secret", connect_timeout=2, read_timeout=2,
        )
        self.client = VendorClient(config)
        self.app_server = create_server(
            "127.0.0.1", 0, database_path=Path(self.temporary.name) / "sync.db",
            seed=False, vendor_client=self.client,
        )
        self.app_thread = threading.Thread(target=self.app_server.serve_forever, daemon=True)
        self.app_thread.start()
        self.app_base = f"http://127.0.0.1:{self.app_server.server_port}"

    def tearDown(self):
        self.app_server.shutdown()
        self.app_server.server_close()
        self.app_thread.join(timeout=2)
        self.vendor_server.shutdown()
        self.vendor_server.server_close()
        self.vendor_thread.join(timeout=2)
        self.temporary.cleanup()

    def test_loopback_sync_logs_in_and_upserts_inventory(self):
        request = Request(
            self.app_base + "/api/sync/read-only", data=b"{}", method="POST",
            headers={"Content-Type": "application/json"},
        )
        with urlopen(request, timeout=2) as response:
            result = json.loads(response.read())
            self.assertEqual(response.status, 200)
        self.assertEqual(result["synced"], {"routers": 1, "tags": 1, "templates": 1})

        with urlopen(self.app_base + "/api/tags", timeout=2) as response:
            tag = json.loads(response.read())["items"][0]
        self.assertEqual(tag["id"], "92.91.87.80")
        self.assertEqual(tag["status"], "ready")
        self.assertEqual(tag["router_id"], "8")
        self.assertEqual(tag["template_id"], "136")
        self.assertEqual(FakeVendorHandler.calls[0][1], "/esls_new/login/userLogin")
        self.assertTrue(all(call[2] == "JSESSIONID=fake-login" for call in FakeVendorHandler.calls[1:]))

    def _dispatch_request(self, body):
        return Request(
            self.app_base + "/api/dispatch/live",
            data=json.dumps(body).encode(), method="POST",
            headers={"Content-Type": "application/json"},
        )

    def test_live_dispatch_is_deterministically_denied_without_both_guards(self):
        updates = [{
            "mac": "92.91.87.80", "styleid": 136, "mappingtype": 101,
            "ABDisplayFlag": 163, "Price": "9.99",
        }]
        bodies_and_environments = (
            ({"confirmation": LIVE_WRITE_CONFIRMATION, "updates": updates}, {}),
            ({"confirmation": "almost", "updates": updates}, {"ESL_LIVE_WRITES": "1"}),
            ({"confirmation": LIVE_WRITE_CONFIRMATION, "updates": updates}, {"ESL_LIVE_WRITES": "true"}),
        )
        errors = []
        for body, environment in bodies_and_environments:
            with self.subTest(body=body, environment=environment), patch.dict(
                os.environ, environment, clear=True
            ), self.assertRaises(HTTPError) as caught:
                urlopen(self._dispatch_request(body), timeout=2)
            errors.append((caught.exception.code, json.loads(caught.exception.read())))
            caught.exception.close()
        self.assertEqual(errors, [(403, {
            "error": {"code": "live_writes_forbidden", "details": {},
                      "message": "Live ESL writes are disabled or not explicitly confirmed"}
        })] * 3)
        for environment in ({}, {"ESL_LIVE_WRITES": "1"}):
            malformed = Request(
                self.app_base + "/api/dispatch/live", data=b"{", method="POST",
                headers={"Content-Type": "application/json"},
            )
            with patch.dict(os.environ, environment, clear=True), self.assertRaises(HTTPError) as caught:
                urlopen(malformed, timeout=2)
            self.assertEqual(caught.exception.code, 403)
            self.assertEqual(json.loads(caught.exception.read()), errors[0][1])
            caught.exception.close()
        self.assertEqual(FakeVendorHandler.calls, [])

    def test_authorized_dispatch_rejects_invalid_payload_before_vendor_call(self):
        body = {"confirmation": LIVE_WRITE_CONFIRMATION, "updates": [{
            "mac": "92.91.87.80", "styleid": "invalid", "mappingtype": 101,
            "ABDisplayFlag": 163,
        }]}
        with patch.dict(os.environ, {"ESL_LIVE_WRITES": "1"}, clear=True), self.assertRaises(HTTPError) as caught:
            urlopen(self._dispatch_request(body), timeout=2)
        self.assertEqual(caught.exception.code, 400)
        self.assertEqual(json.loads(caught.exception.read())["error"]["code"], "validation_error")
        caught.exception.close()
        self.assertEqual(FakeVendorHandler.calls, [])

    def test_guarded_loopback_dispatch_verifies_payload_and_reads_back_tag_status(self):
        updates = [{
            "mac": "92.91.87.80", "styleid": 136, "mappingtype": 101,
            "ABDisplayFlag": 163, "Price": "9.99",
        }]
        FakeVendorHandler.expected_updates = updates
        FakeVendorHandler.tag_status = 4
        body = {"confirmation": LIVE_WRITE_CONFIRMATION, "updates": updates}
        with patch.dict(os.environ, {"ESL_LIVE_WRITES": "1"}, clear=True):
            with urlopen(self._dispatch_request(body), timeout=2) as response:
                result = json.loads(response.read())
                self.assertEqual(response.status, 200)
        self.assertEqual(result, {
            "dispatched": 1,
            "verified_tags": [{"mac": "92.91.87.80", "status": "success"}],
        })
        self.assertEqual(
            [call[1] for call in FakeVendorHandler.calls],
            ["/esls_new/login/userLogin", "/esls_new/associate/updateScreen",
             "/esls_new/associate/getTagsMsg"],
        )

    def test_vendor_http_500_is_failure_without_success_readback(self):
        updates = [{
            "mac": "92.91.87.80", "styleid": 136, "mappingtype": 101,
            "ABDisplayFlag": 163,
        }]
        FakeVendorHandler.expected_updates = updates
        FakeVendorHandler.update_status = 500
        body = {"confirmation": LIVE_WRITE_CONFIRMATION, "updates": updates}
        with patch.dict(os.environ, {"ESL_LIVE_WRITES": "1"}, clear=True), self.assertRaises(HTTPError) as caught:
            urlopen(self._dispatch_request(body), timeout=2)
        self.assertEqual(caught.exception.code, 502)
        self.assertEqual(json.loads(caught.exception.read())["error"]["code"], "vendor_error")
        caught.exception.close()
        self.assertEqual(
            [call[1] for call in FakeVendorHandler.calls],
            ["/esls_new/login/userLogin", "/esls_new/associate/updateScreen"],
        )


if __name__ == "__main__":
    unittest.main()
