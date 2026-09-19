import base64
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
    VendorError,
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


class PaginationTests(unittest.TestCase):
    def test_every_vendor_client_uses_a_central_five_second_gap(self):
        client = VendorClient(VendorConfig(base_url="http://127.0.0.1/esls_new"))
        self.assertEqual(client._minimum_request_gap, 5.0)
        client._last_request_finished = 100.0
        with patch("esl_web.vendor.time.monotonic", return_value=102.0), patch(
            "esl_web.vendor.time.sleep"
        ) as sleep_call:
            client._wait_for_request_slot()
        sleep_call.assert_called_once_with(3.0)

    def test_update_status_rejects_non_finite_and_out_of_range_values(self):
        client = VendorClient(VendorConfig(base_url="http://127.0.0.1/esls_new"))
        for value in (float("inf"), float("nan"), 1e100, "999", True, "2.5"):
            with self.subTest(value=value):
                self.assertIsNone(client._update_status({"updateProgress": value}))

    def test_tag_inventory_fetches_all_pages_without_duplicating_page_zero(self):
        client = VendorClient(VendorConfig(base_url="http://192.0.2.1/esls_new"))
        first = [{"mac": str(index)} for index in range(10)]
        second = [{"mac": str(index)} for index in range(10, 13)]
        with patch.object(client, "_request", side_effect=[first, second, []]) as request_call:
            tags = client.get_tags()
        self.assertEqual(len(tags), 13)
        self.assertIn("currentPage=1", request_call.call_args_list[0].args[1])
        self.assertIn("currentPage=2", request_call.call_args_list[1].args[1])
        self.assertIn("currentPage=3", request_call.call_args_list[2].args[1])


class ExtendedReadOnlyVendorTests(unittest.TestCase):
    def setUp(self):
        self.client = VendorClient(VendorConfig(base_url="http://127.0.0.1/esls_new"))

    def test_extended_collections_and_template_detail_use_documented_routes(self):
        style = {
            "id": 10, "name": "Desk", "styleFileds": ["name", "price"],
            "width": 400, "height": 300, "mappingtype": 1,
        }
        with patch.object(self.client, "_request_document", side_effect=[
            [{"mac": "99.99.33.35", "width": 400, "height": 300}],
            {"datalist": [style], "resultCode": 10},
            {"datalist": [style], "resultCode": 10},
            {"datalist": [{"id": 8, "name": "bg1", "width": 640, "height": 384}],
             "resultCode": 10},
        ]) as request_call:
            self.assertEqual(len(self.client.get_extended_tags()), 1)
            self.assertEqual(self.client.get_style_catalog()[0]["id"], 10)
            self.assertEqual(self.client.get_style_detail(10)["styleFileds"], ["name", "price"])
            self.assertEqual(self.client.get_photos()[0]["name"], "bg1")
        self.assertEqual([call.args[:2] for call in request_call.call_args_list], [
            ("GET", "/associate/getTagsMsg"),
            ("GET", "/associate/getStyleMsgs"),
            ("POST", "/associate/getStyleMsgById?id=10"),
            ("GET", "/associate/getPhotos"),
        ])
        self.assertEqual(json.loads(request_call.call_args_list[2].args[2]), {"id": 10})

    def test_documented_envelopes_fail_closed(self):
        invalid_values = (
            {"datalist": [], "resultCode": 0},
            {"datalist": "not-a-list", "resultCode": 10},
            {"datalist": ["not-an-object"], "resultCode": 10},
        )
        for value in invalid_values:
            with self.subTest(value=value), patch.object(
                self.client, "_request_document", return_value=value
            ), self.assertRaises(VendorError):
                self.client.get_style_catalog()
        with self.assertRaises(VendorError):
            self.client.get_style_detail(True)

    def test_photo_data_is_bounded_validated_and_typed(self):
        png = b"\x89PNG\r\n\x1a\n" + b"image"
        encoded = base64.b64encode(png).decode("ascii")
        with patch.object(self.client, "_request_document", return_value={
            "data": encoded, "t": encoded, "datalist": [], "resultCode": 10,
        }):
            data, media_type = self.client.get_photo_data("bg1")
        self.assertEqual(data, png)
        self.assertEqual(media_type, "image/png")

        invalid_payloads = (
            {"data": "not-base64", "datalist": [], "resultCode": 10},
            {"data": base64.b64encode(b"not an image").decode(), "datalist": [], "resultCode": 10},
            {"data": "A" * (VendorClient.MAX_ENCODED_IMAGE_BYTES + 1), "datalist": [], "resultCode": 10},
        )
        for payload in invalid_payloads:
            with self.subTest(payload_type=len(payload["data"])), patch.object(
                self.client, "_request_document", return_value=payload
            ), self.assertRaises(VendorError):
                self.client.get_photo_data("bg1")

    def test_template_preview_uses_derived_same_origin_path_and_rejects_non_image(self):
        detail = {"id": 10, "name": "Desk template", "styleFileds": []}
        png = b"\x89PNG\r\n\x1a\n" + b"preview"
        with patch.object(self.client, "get_style_detail", return_value=detail), patch.object(
            self.client, "_request_bytes", return_value=(png, "image/png")
        ) as raw_request:
            data, media_type = self.client.get_template_preview(10)
        self.assertEqual((data, media_type), (png, "image/png"))
        self.assertEqual(raw_request.call_args.args[:2], ("GET", "/Desk%20template10.png"))

        with patch.object(self.client, "get_style_detail", return_value=detail), patch.object(
            self.client, "_request_bytes", return_value=(b"<html>", "text/html")
        ), self.assertRaises(VendorError):
            self.client.get_template_preview(10)


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
        with self.assertRaises(VendorConfigurationError):
            VendorConfig("http://127.0.0.1/esls_new", username=123, password="secret")


class FakeVendorHandler(BaseHTTPRequestHandler):
    calls = []
    update_status = 200
    expected_updates = []
    tag_status = 1
    updated_tag_status = 4
    login_authenticated = True

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
            self._send('<html><a href="login/logout">logout</a></html>', cookie="JSESSIONID=fake-login; Path=/esls_new; HttpOnly")
            return
        if self.path.startswith("/esls_new/associate/getStyleMsgById?id="):
            style_id = int(self.path.rsplit("=", 1)[1])
            if json.loads(body) != {"id": style_id}:
                self.send_error(400)
                return
            self._send(json.dumps({
                "datalist": [{
                    "id": style_id, "name": "Vendor template", "descriptor": "Desk template",
                    "width": 296, "height": 128, "mappingtype": 7, "type": 2,
                    "styleFileds": ["name", "price"], "rotate": 0, "userid": 18,
                    "backgroundId": 8, "updatetime": "Sep 19, 2026",
                }],
                "resultCode": 10, "resultMsg": "success",
            }))
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
            self.__class__.tag_status = self.__class__.updated_tag_status
            self._send("true")
            return
        self.send_error(404)

    def assert_login(self, body):
        values = parse_qs(body.decode())
        expected = hashlib.md5(b"secret").hexdigest()
        if values != {"name": ["operator"], "passwd": [expected]}:
            self.send_error(400)
            raise AssertionError(values)

    def do_GET(self):
        self.__class__.calls.append(("GET", self.path, self.headers.get("Cookie"), b""))
        if not self.__class__.login_authenticated:
            self.send_error(401)
            return
        if self.headers.get("Cookie") != "JSESSIONID=fake-login":
            self.send_error(401)
            return
        if self.path == "/esls_new/mms/queryRouters?currentPage=0&routerId=0":
            self._send(json.dumps({"datalist": [{
                "id": "98", "mac": "1", "ip": "127.0.0.8", "state": "true",
                "shopName": "Test shop", "description": "Test router",
            }], "resultCode": 1}))
        elif self.path == "/esls_new/mms/queryStyles?currentPage=0&templateType=0":
            self._send(json.dumps({"datalist": [
                {"id": "136", "name": "Vendor template", "styleLen": "296x128"},
                {"id": "138", "name": "Vendor template (137)", "styleLen": "296x128"},
                {"id": "137", "name": "Vendor template", "styleLen": "296x128"},
            ], "resultCode": 1}))
        elif self.path.startswith("/esls_new/mms/queryTags?"):
            if "currentPage=2" in self.path:
                self._send(json.dumps({"datalist": [], "resultCode": 1}))
                return
            self._send(json.dumps({"datalist": [{
                "id": "7", "mac": "92.91.87.80", "power": "100",
                "state": "true" if self.__class__.tag_status in {1, 2, 4} else "false",
                "routerMac": "1", "styleName": "Vendor template",
                "name": "Test tag", "status": "1",
                "updateProgress": str(self.__class__.tag_status),
            }], "resultCode": 1}))
        elif self.path == "/esls_new/associate/getTagsMsg":
            self._send(json.dumps([{
                "mac": "92.91.87.80", "power": 99, "routerid": "1", "rssi": -48,
                "showStyle": "2.9 inch", "status": 1, "styleId": 136,
                "width": 296, "height": 128, "routerStatus": 1, "ido": 7, "sub": 0,
            }]))
        elif self.path == "/esls_new/associate/getStyleMsgs":
            self._send(json.dumps({
                "datalist": [
                    {
                        "id": 136, "name": "Vendor template", "descriptor": "Desk template",
                        "width": 296, "height": 128, "mappingtype": 7, "type": 2,
                        "backgroundID": 8, "updateTime": "Sep 19, 2026",
                    },
                    {
                        "id": 138, "name": "Vendor template (137)", "descriptor": "Desk template B",
                        "width": 296, "height": 128, "mappingtype": 8, "type": 2,
                        "backgroundID": 0, "updateTime": "Sep 19, 2026",
                    },
                    {
                        "id": 137, "name": "Vendor template", "descriptor": "Desk template C",
                        "width": 296, "height": 128, "mappingtype": 9, "type": 2,
                        "backgroundID": 0, "updateTime": "Sep 19, 2026",
                    },
                ],
                "resultCode": 10, "resultMsg": "success",
            }))
        elif self.path == "/esls_new/associate/getPhotos":
            self._send(json.dumps({
                "datalist": [{"id": 8, "name": "bg1", "width": 640, "height": 384}],
                "resultCode": 10, "resultMsg": "success",
            }))
        elif self.path == "/esls_new/associate/getPhotoDataByName?photoName=bg1":
            encoded = base64.b64encode(b"\x89PNG\r\n\x1a\nphoto").decode("ascii")
            self._send(json.dumps({"data": encoded, "t": encoded, "datalist": [], "resultCode": 10}))
        elif self.path == "/esls_new/Vendor%20template136.png":
            body = b"\x89PNG\r\n\x1a\npreview"
            self.send_response(200)
            self.send_header("Content-Type", "image/png")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
        else:
            self.send_error(404)


class ReadOnlySyncTests(unittest.TestCase):
    def setUp(self):
        FakeVendorHandler.calls = []
        FakeVendorHandler.update_status = 200
        FakeVendorHandler.expected_updates = []
        FakeVendorHandler.tag_status = 1
        FakeVendorHandler.updated_tag_status = 4
        FakeVendorHandler.login_authenticated = True
        self.vendor_server = ThreadingHTTPServer(("127.0.0.1", 0), FakeVendorHandler)
        self.vendor_thread = threading.Thread(target=self.vendor_server.serve_forever, daemon=True)
        self.vendor_thread.start()
        self.temporary = tempfile.TemporaryDirectory()
        config = VendorConfig(
            f"http://127.0.0.1:{self.vendor_server.server_port}/esls_new",
            username="operator", password="secret", connect_timeout=2, read_timeout=2,
        )
        self.client = VendorClient(config)
        self.client._minimum_request_gap = 0.0
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
        FakeVendorHandler.tag_status = 4
        with patch.dict(os.environ, {}, clear=True), urlopen(
            self.app_base + "/api/health", timeout=2
        ) as response:
            self.assertEqual(json.loads(response.read())["mode"], "read_only")
        request = Request(
            self.app_base + "/api/sync/read-only", data=b"{}", method="POST",
            headers={"Content-Type": "application/json"},
        )
        with urlopen(request, timeout=2) as response:
            result = json.loads(response.read())
            self.assertEqual(response.status, 200)
        self.assertEqual(result["synced"], {"routers": 1, "tags": 1, "templates": 3})

        with urlopen(self.app_base + "/api/tags", timeout=2) as response:
            tag = json.loads(response.read())["items"][0]
        self.assertEqual(tag["id"], "92.91.87.80")
        self.assertEqual(tag["status"], "success")
        self.assertEqual(tag["router_id"], "1")
        self.assertEqual(tag["template_id"], "136")
        self.assertEqual(FakeVendorHandler.calls[0][1], "/esls_new/login/userLogin")
        self.assertTrue(all(call[2] == "JSESSIONID=fake-login" for call in FakeVendorHandler.calls[1:]))

    def test_extended_sync_and_read_only_vendor_api_preserve_inventory(self):
        request = Request(
            self.app_base + "/api/sync/read-only", data=b"{}", method="POST",
            headers={"Content-Type": "application/json"},
        )
        with urlopen(request, timeout=2) as response:
            result = json.loads(response.read())
        self.assertEqual(result["synced"], {"routers": 1, "tags": 1, "templates": 3})

        with urlopen(self.app_base + "/api/tags", timeout=2) as response:
            tag = json.loads(response.read())["items"][0]
        self.assertEqual(tag["width"], 296)
        self.assertEqual(tag["height"], 128)
        self.assertEqual(tag["show_style"], "2.9 inch")
        self.assertEqual(tag["vendor_tag_id"], 7)
        self.assertEqual(tag["router_status"], 1)

        with urlopen(self.app_base + "/api/templates", timeout=2) as response:
            templates = json.loads(response.read())["items"]
        template = next(item for item in templates if item["id"] == "136")
        self.assertEqual(template["mapping_type"], 7)
        self.assertEqual(template["descriptor"], "Desk template")
        self.assertEqual(template["screen_type"], 2)
        self.assertEqual(template["background_id"], 8)

        with urlopen(self.app_base + "/api/vendor/templates", timeout=2) as response:
            catalog = json.loads(response.read())["items"]
        self.assertEqual(catalog[0]["id"], "136")
        self.assertEqual(catalog[0]["preview_url"], "/api/vendor/templates/136/preview")

        with urlopen(self.app_base + "/api/vendor/templates/136", timeout=2) as response:
            detail = json.loads(response.read())
        self.assertEqual(detail["style_fields"], ["name", "price"])
        self.assertEqual(detail["user_id"], 18)

        with urlopen(self.app_base + "/api/vendor/photos", timeout=2) as response:
            photos = json.loads(response.read())["items"]
        self.assertEqual(photos, [{
            "id": "8", "name": "bg1", "width": 640, "height": 384,
            "data_url": "/api/vendor/photos/bg1/data",
        }])

        with urlopen(self.app_base + "/api/vendor/photos/bg1/data", timeout=2) as response:
            self.assertEqual(response.headers.get_content_type(), "image/png")
            self.assertTrue(response.read().startswith(b"\x89PNG"))
            self.assertEqual(response.headers["X-Content-Type-Options"], "nosniff")
        with urlopen(self.app_base + "/api/vendor/templates/136/preview", timeout=2) as response:
            self.assertEqual(response.headers.get_content_type(), "image/png")
            self.assertTrue(response.read().startswith(b"\x89PNG"))

    def test_read_only_sync_rejects_query_parameters_before_vendor_call(self):
        request = Request(
            self.app_base + "/api/sync/read-only?unexpected=", data=b"{}", method="POST",
            headers={"Content-Type": "application/json"},
        )
        with self.assertRaises(HTTPError) as caught:
            urlopen(request, timeout=2)
        self.assertEqual(caught.exception.code, 400)
        self.assertEqual(json.loads(caught.exception.read())["error"]["code"], "validation_error")
        caught.exception.close()
        self.assertEqual(FakeVendorHandler.calls, [])

    def _dispatch_request(self, body):
        return Request(
            self.app_base + "/api/dispatch/live",
            data=json.dumps(body).encode(), method="POST",
            headers={"Content-Type": "application/json"},
        )

    def test_login_html_and_cookie_are_not_enough_without_authenticated_probe(self):
        FakeVendorHandler.login_authenticated = False
        client = VendorClient(VendorConfig(
            base_url=self.client.config.base_url, username="operator", password="secret"
        ))
        with self.assertRaises(VendorError):
            client.get_routers()
        self.assertFalse(client._logged_in)

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
        FakeVendorHandler.tag_status = 1
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
            ["/esls_new/login/userLogin",
             "/esls_new/mms/queryRouters?currentPage=0&routerId=0",
             "/esls_new/mms/queryTags?currentPage=1&tagMac=0&routerMac=0&startTime=&endTime=&templateType=0",
             "/esls_new/mms/queryTags?currentPage=2&tagMac=0&routerMac=0&startTime=&endTime=&templateType=0",
             "/esls_new/associate/updateScreen",
             "/esls_new/mms/queryTags?currentPage=1&tagMac=0&routerMac=0&startTime=&endTime=&templateType=0",
             "/esls_new/mms/queryTags?currentPage=2&tagMac=0&routerMac=0&startTime=&endTime=&templateType=0"],
        )

    def test_dispatch_rejects_stale_success_status_as_unverified(self):
        updates = [{"mac": "92.91.87.80", "styleid": 136, "mappingtype": 101,
                    "ABDisplayFlag": 163}]
        FakeVendorHandler.expected_updates = updates
        FakeVendorHandler.tag_status = 4
        FakeVendorHandler.updated_tag_status = 4
        body = {"confirmation": LIVE_WRITE_CONFIRMATION, "updates": updates}
        with patch.dict(os.environ, {"ESL_LIVE_WRITES": "1"}, clear=True), \
             self.assertRaises(HTTPError) as caught:
            urlopen(self._dispatch_request(body), timeout=2)
        self.assertEqual(caught.exception.code, 502)
        self.assertEqual(json.loads(caught.exception.read())["error"]["code"], "vendor_error")
        caught.exception.close()

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
            ["/esls_new/login/userLogin",
             "/esls_new/mms/queryRouters?currentPage=0&routerId=0",
             "/esls_new/mms/queryTags?currentPage=1&tagMac=0&routerMac=0&startTime=&endTime=&templateType=0",
             "/esls_new/mms/queryTags?currentPage=2&tagMac=0&routerMac=0&startTime=&endTime=&templateType=0",
             "/esls_new/associate/updateScreen"],
        )


if __name__ == "__main__":
    unittest.main()
