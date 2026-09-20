import json
import tempfile
import threading
import unittest
from pathlib import Path
from unittest.mock import Mock, patch
from urllib.error import HTTPError
from urllib.request import Request, urlopen

from esl_web.server import _is_loopback_address, create_server


class ApiTests(unittest.TestCase):
    def test_live_dispatch_client_scope_accepts_only_loopback(self):
        self.assertTrue(_is_loopback_address("127.0.0.1"))
        self.assertTrue(_is_loopback_address("::1"))
        self.assertFalse(_is_loopback_address("192.168.16.42"))
        self.assertFalse(_is_loopback_address("not-an-address"))

    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.server = create_server(
            "127.0.0.1", 0, database_path=Path(self.temporary.name) / "api.db", seed=True
        )
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.base = f"http://127.0.0.1:{self.server.server_port}"

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=2)
        self.temporary.cleanup()

    def request(self, method, path, body=None, content_type="application/json"):
        data = None if body is None else json.dumps(body).encode()
        request = Request(self.base + path, data=data, method=method)
        if data is not None:
            request.add_header("Content-Type", content_type)
        with urlopen(request, timeout=2) as response:
            payload = response.read()
            return response.status, response.headers, json.loads(payload) if payload else None

    def test_health_dashboard_and_filtered_collections(self):
        status, _, health = self.request("GET", "/api/health")
        self.assertEqual(status, 200)
        self.assertEqual(health, {"mode": "simulation", "status": "ok"})

        _, _, dashboard = self.request("GET", "/api/dashboard")
        self.assertEqual(dashboard["products"], 2)
        _, _, products = self.request("GET", "/api/products?search=k%C3%A1va")
        self.assertEqual([item["id"] for item in products["items"]], ["prod-coffee"])
        _, _, tags = self.request("GET", "/api/tags?status=failed&bound=false")
        self.assertEqual([item["id"] for item in tags["items"]], ["tag-002"])
        with self.server.service.storage.connection() as connection:
            connection.execute(
                "UPDATE templates SET vendor_id = '145' WHERE id = 'tpl-default'"
            )
        _, _, templates = self.request("GET", "/api/templates")
        self.assertEqual(
            templates["items"][0]["preview_url"],
            "/api/vendor/templates/145/preview?controller_id=legacy",
        )
        for path in ("/api/routers", "/api/templates", "/api/jobs", "/api/alerts", "/api/audit"):
            _, _, result = self.request("GET", path)
            self.assertIsInstance(result["items"], list)

    def test_tag_collection_can_explicitly_include_unsupported_historical_inventory(self):
        with self.server.service.storage.connection() as connection:
            connection.execute(
                "INSERT INTO tags(id, controller_id, vendor_id, mac, label, width, height, "
                "battery, rssi, status, device_model_id) "
                "VALUES ('historical-1x1', 'legacy', 'old-1', 'opaque-old', 'Historická', "
                "1, 1, 0, 0, 'ready', NULL)"
            )
        _, _, regular = self.request("GET", "/api/tags")
        self.assertNotIn("historical-1x1", {item["id"] for item in regular["items"]})
        _, _, complete = self.request("GET", "/api/tags?include_unsupported=true")
        item = next(item for item in complete["items"] if item["id"] == "historical-1x1")
        self.assertFalse(item["management_supported"])
        self.assertEqual(item["device_model_state"], "unsupported")

    def test_health_reports_live_mode_only_when_writes_are_enabled(self):
        with patch.dict("os.environ", {"ESL_LIVE_WRITES": "1"}):
            status, _, health = self.request("GET", "/api/health")
        self.assertEqual(status, 200)
        self.assertEqual(health, {"mode": "live", "status": "ok"})

    def test_product_binding_and_job_mutations_are_exposed(self):
        status, _, product = self.request("POST", "/api/products", {
            "id": "prod-new", "sku": "NEW-1", "name": "Novinka", "price": 2.5
        })
        self.assertEqual(status, 201)
        self.assertEqual(product["id"], "prod-new")
        status, _, updated = self.request("PATCH", "/api/products/prod-new", {"price": 2.75})
        self.assertEqual(status, 200)
        self.assertEqual(updated["price"], 2.75)

        status, _, binding = self.request("POST", "/api/bindings", {
            "product_id": "prod-new", "tag_id": "tag-002"
        })
        self.assertEqual(status, 201)
        self.assertEqual(binding["tag_id"], "tag-002")
        status, _, job = self.request("POST", "/api/jobs", {"product_ids": ["prod-new"]})
        self.assertEqual(status, 202)
        _, _, failed = self.request("POST", f"/api/jobs/{job['id']}/simulate", {"fail_tag_ids": ["tag-002"]})
        self.assertEqual(failed["status"], "failed")
        _, _, retried = self.request("POST", f"/api/jobs/{job['id']}/retry", {})
        self.assertEqual(retried["status"], "queued")
        _, _, completed = self.request("POST", f"/api/jobs/{job['id']}/simulate", {})
        self.assertEqual(completed["status"], "completed")

        status, _, payload = self.request("DELETE", "/api/bindings/prod-new/tag-002")
        self.assertEqual((status, payload), (204, None))
        status, _, payload = self.request("DELETE", "/api/products/prod-new")
        self.assertEqual((status, payload), (204, None))

    def test_json_errors_and_csv_export_have_stable_contracts(self):
        malformed = Request(
            self.base + "/api/products", data=b"{", method="POST",
            headers={"Content-Type": "application/json"},
        )
        with self.assertRaises(HTTPError) as caught:
            urlopen(malformed, timeout=2)
        self.assertEqual(caught.exception.code, 400)
        error = json.loads(caught.exception.read())
        caught.exception.close()
        self.assertEqual(error["error"]["code"], "validation_error")
        self.assertEqual(error["error"]["message"], "Malformed JSON")

        with self.assertRaises(HTTPError) as caught:
            urlopen(self.base + "/api/products/bad%20id", timeout=2)
        self.assertEqual(caught.exception.code, 400)
        self.assertEqual(json.loads(caught.exception.read())["error"]["code"], "validation_error")
        caught.exception.close()
        with self.assertRaises(HTTPError) as caught:
            urlopen(self.base + "/api/unknown", timeout=2)
        self.assertEqual(caught.exception.code, 404)
        self.assertEqual(json.loads(caught.exception.read())["error"]["code"], "not_found")
        caught.exception.close()

        with urlopen(self.base + "/api/products/export.csv", timeout=2) as response:
            exported = response.read().decode("utf-8")
            self.assertEqual(response.status, 200)
            self.assertEqual(response.headers.get_content_type(), "text/csv")
            self.assertIn("attachment; filename=products.csv", response.headers["Content-Disposition"])
        self.assertEqual(exported.splitlines()[0], "id,sku,ean,name,price,currency,template_id,tag_id")
        self.assertIn("prod-coffee,SKU-COFFEE,8580000000011,Káva,6.49,EUR,tpl-default,tag-001", exported)

    def test_non_standard_json_numbers_are_rejected(self):
        request = Request(
            self.base + "/api/products",
            data=b'{"id":"bad","sku":"BAD","name":"Bad","price":NaN}',
            method="POST",
            headers={"Content-Type": "application/json"},
        )
        with self.assertRaises(HTTPError) as caught:
            urlopen(request, timeout=2)
        self.assertEqual(caught.exception.code, 400)
        payload = json.loads(caught.exception.read())
        caught.exception.close()
        self.assertEqual(payload["error"]["message"], "Malformed JSON")

    def test_template_clone_api_is_a_normal_authenticated_origin_checked_mutation(self):
        token = "A" * 64
        vendor = Mock()
        service = Mock()
        service.clone_vendor_template.return_value = {
            "id": "200", "name": "S21BasePriceTag_V1_BOLD", "source_id": "145",
        }
        protected = create_server(
            "127.0.0.1", 0, service=service, vendor_client=vendor, api_token=token
        )
        thread = threading.Thread(target=protected.serve_forever, daemon=True)
        thread.start()
        base = f"http://127.0.0.1:{protected.server_port}"
        try:
            login = Request(base + "/api/session", data=json.dumps({"token": token}).encode(),
                            method="POST", headers={"Content-Type": "application/json"})
            with urlopen(login, timeout=2) as response:
                cookie = response.headers["Set-Cookie"].split(";", 1)[0]
            body = {
                "source_controller_id": "legacy", "target_controller_id": "legacy",
                "source_template_id": 145, "target_name": "S21BasePriceTag_V1_BOLD",
            }
            clone = Request(base + "/api/vendor/templates/clone", data=json.dumps(body).encode(),
                            method="POST", headers={"Content-Type": "application/json",
                                                    "Cookie": cookie, "Origin": base})
            with urlopen(clone, timeout=2) as response:
                self.assertEqual(response.status, 201)
                self.assertEqual(json.loads(response.read())["id"], "200")
            service.clone_vendor_template.assert_called_once_with(
                vendor, vendor, body, source_controller_id="legacy",
                target_controller_id="legacy",
            )

            cross_origin = Request(
                base + "/api/vendor/templates/clone", data=json.dumps(body).encode(), method="POST",
                headers={"Content-Type": "application/json", "Cookie": cookie,
                         "Origin": "https://evil.example"},
            )
            with self.assertRaises(HTTPError) as caught:
                urlopen(cross_origin, timeout=2)
            self.assertEqual(caught.exception.code, 403)
            caught.exception.close()
            self.assertEqual(service.clone_vendor_template.call_count, 1)
        finally:
            protected.shutdown()
            protected.server_close()
            thread.join(timeout=2)

    def test_local_tag_staging_and_configuration_routes_never_call_vendor(self):
        token = "B" * 64
        vendor = Mock()
        protected = create_server(
            "127.0.0.1", 0, database_path=Path(self.temporary.name) / "local-tags.db",
            seed=True, vendor_client=vendor, api_token=token,
        )
        with protected.service.storage.connection() as connection:
            connection.execute(
                "INSERT INTO controllers(id, name, is_default) VALUES ('south', 'South', 0)"
            )
            connection.execute(
                "INSERT INTO routers(id, controller_id, vendor_id, name, address, status) "
                "VALUES ('south-router', 'south', '1', 'South router', '10.0.1.1', 'online')"
            )
        thread = threading.Thread(target=protected.serve_forever, daemon=True)
        thread.start()
        base = f"http://127.0.0.1:{protected.server_port}"
        payload = {
            "id": "tag-local", "controller_id": "legacy", "mac": "aabb.ccdd.eeff",
            "label": "Staged", "device_model_id": "2.9EPD-BWR", "width": 296,
            "height": 128, "router_id": "router-main", "template_id": "tpl-default",
            "test_data": {"name": "Local", "price": "1.00"},
        }
        try:
            login = Request(base + "/api/session", data=json.dumps({"token": token}).encode(),
                            method="POST", headers={"Content-Type": "application/json"})
            with urlopen(login, timeout=2) as response:
                cookie = response.headers["Set-Cookie"].split(";", 1)[0]
            headers = {"Content-Type": "application/json", "Cookie": cookie, "Origin": base}
            create = Request(base + "/api/tags/staged", data=json.dumps(payload).encode(),
                             method="POST", headers=headers)
            with urlopen(create, timeout=2) as response:
                self.assertEqual(response.status, 201)
                created = json.loads(response.read())
            self.assertTrue(created["staged"])
            self.assertEqual(created["mac"], "AA:BB:CC:DD:EE:FF")

            changed = {
                **{key: value for key, value in payload.items() if key != "id"},
                "label": "Configured", "test_data": {"price": "2.00"},
            }
            update = Request(base + "/api/tags/tag-local/configuration",
                             data=json.dumps(changed).encode(), method="PUT", headers=headers)
            with urlopen(update, timeout=2) as response:
                self.assertEqual(response.status, 200)
                configured = json.loads(response.read())
            self.assertEqual(configured["label"], "Configured")
            self.assertEqual(configured["configuration_source"], "local")

            with urlopen(base + "/api/tags/tag-local", timeout=2) as response:
                detail = json.loads(response.read())
            self.assertEqual(detail["controller"]["id"], "legacy")
            self.assertEqual(detail["rf_router"]["id"], "router-main")
            self.assertEqual(detail["device_model"]["id"], "2.9EPD-BWR")
            self.assertEqual(detail["compatible_template"]["id"], "tpl-default")
            self.assertEqual(detail["test_data"], {"price": "2.00"})

            duplicate = Request(
                base + "/api/tags/staged",
                data=json.dumps({**payload, "id": "tag-duplicate",
                                 "mac": "AA-BB-CC-DD-EE-FF"}).encode(),
                method="POST", headers=headers,
            )
            with self.assertRaises(HTTPError) as caught:
                urlopen(duplicate, timeout=2)
            self.assertEqual(caught.exception.code, 409)
            caught.exception.close()

            cross_controller = Request(
                base + "/api/tags/staged",
                data=json.dumps({**payload, "id": "tag-cross",
                                 "mac": "AA:BB:CC:DD:EE:01",
                                 "router_id": "south-router"}).encode(),
                method="POST", headers=headers,
            )
            with self.assertRaises(HTTPError) as caught:
                urlopen(cross_controller, timeout=2)
            self.assertEqual(caught.exception.code, 400)
            caught.exception.close()

            second_payload = {**payload, "id": "tag-second", "mac": "AA:BB:CC:DD:EE:02"}
            second_create = Request(
                base + "/api/tags/staged", data=json.dumps(second_payload).encode(),
                method="POST", headers=headers,
            )
            with urlopen(second_create, timeout=2) as response:
                self.assertEqual(response.status, 201)
            second_configuration = {
                key: value for key, value in second_payload.items() if key != "id"
            }
            update_cases = (
                ({**second_configuration, "height": 127}, 400),
                ({**second_configuration, "mac": "aabb.ccdd.eeff"}, 409),
                ({**second_configuration, "router_id": "south-router"}, 400),
            )
            for body, expected_status in update_cases:
                request = Request(
                    base + "/api/tags/tag-second/configuration",
                    data=json.dumps(body).encode(), method="PUT", headers=headers,
                )
                with self.subTest(body=body), self.assertRaises(HTTPError) as caught:
                    urlopen(request, timeout=2)
                self.assertEqual(caught.exception.code, expected_status)
                caught.exception.close()
            vendor.assert_not_called()
            self.assertEqual(vendor.mock_calls, [])
        finally:
            protected.shutdown()
            protected.server_close()
            thread.join(timeout=2)

    def test_local_tag_mutations_reject_unauthenticated_and_cross_origin_requests(self):
        token = "C" * 64
        protected = create_server(
            "127.0.0.1", 0, database_path=Path(self.temporary.name) / "protected-tags.db",
            seed=True, api_token=token,
        )
        thread = threading.Thread(target=protected.serve_forever, daemon=True)
        thread.start()
        base = f"http://127.0.0.1:{protected.server_port}"
        payload = {
            "controller_id": "legacy", "mac": "AA:BB:CC:DD:EE:99", "label": "Test",
            "device_model_id": "2.9EPD-BWR", "width": 296, "height": 128,
            "router_id": "router-main", "template_id": "tpl-default", "test_data": {},
        }
        try:
            unauthenticated = Request(
                base + "/api/tags/staged", data=json.dumps(payload).encode(), method="POST",
                headers={"Content-Type": "application/json", "Origin": base},
            )
            with self.assertRaises(HTTPError) as caught:
                urlopen(unauthenticated, timeout=2)
            self.assertEqual(caught.exception.code, 401)
            caught.exception.close()
            unauthenticated_update = Request(
                base + "/api/tags/tag-001/configuration",
                data=json.dumps(payload).encode(), method="PUT",
                headers={"Content-Type": "application/json", "Origin": base},
            )
            with self.assertRaises(HTTPError) as caught:
                urlopen(unauthenticated_update, timeout=2)
            self.assertEqual(caught.exception.code, 401)
            caught.exception.close()

            login = Request(base + "/api/session", data=json.dumps({"token": token}).encode(),
                            method="POST", headers={"Content-Type": "application/json"})
            with urlopen(login, timeout=2) as response:
                cookie = response.headers["Set-Cookie"].split(";", 1)[0]
            cross_origin = Request(
                base + "/api/tags/staged", data=json.dumps(payload).encode(), method="POST",
                headers={"Content-Type": "application/json", "Cookie": cookie,
                         "Origin": "https://evil.example"},
            )
            with self.assertRaises(HTTPError) as caught:
                urlopen(cross_origin, timeout=2)
            self.assertEqual(caught.exception.code, 403)
            caught.exception.close()
            cross_origin_update = Request(
                base + "/api/tags/tag-001/configuration",
                data=json.dumps(payload).encode(), method="PUT",
                headers={"Content-Type": "application/json", "Cookie": cookie,
                         "Origin": "https://evil.example"},
            )
            with self.assertRaises(HTTPError) as caught:
                urlopen(cross_origin_update, timeout=2)
            self.assertEqual(caught.exception.code, 403)
            caught.exception.close()
            self.assertFalse(any(item["mac"] == payload["mac"]
                                 for item in protected.service.list_tags()))
        finally:
            protected.shutdown()
            protected.server_close()
            thread.join(timeout=2)

    def test_template_clone_preflight_vendor_failure_is_mapped_to_502(self):
        vendor = Mock()
        vendor.get_style_catalog.side_effect = RuntimeError("vendor unavailable")
        protected = create_server(
            "127.0.0.1", 0, database_path=Path(self.temporary.name) / "clone.db",
            vendor_client=vendor,
        )
        thread = threading.Thread(target=protected.serve_forever, daemon=True)
        thread.start()
        try:
            request = Request(
                f"http://127.0.0.1:{protected.server_port}/api/vendor/templates/clone",
                data=json.dumps({
                    "source_controller_id": "legacy", "target_controller_id": "legacy",
                    "source_template_id": 145, "target_name": "S21BasePriceTag_V1_BOLD",
                }).encode(), method="POST", headers={"Content-Type": "application/json"},
            )
            with self.assertRaises(HTTPError) as caught:
                urlopen(request, timeout=2)
            self.assertEqual(caught.exception.code, 502)
            payload = json.loads(caught.exception.read())
            caught.exception.close()
            self.assertEqual(payload["error"]["code"], "vendor_error")
        finally:
            protected.shutdown()
            protected.server_close()
            thread.join(timeout=2)

    def test_template_clone_browser_contract_rejects_legacy_body_and_query_selector(self):
        vendor = Mock()
        service = Mock()
        protected = create_server(
            "127.0.0.1", 0, service=service, vendor_client=vendor,
        )
        thread = threading.Thread(target=protected.serve_forever, daemon=True)
        thread.start()
        base = f"http://127.0.0.1:{protected.server_port}"
        cases = (
            ("", {"source_id": 145, "target_name": "Legacy"}),
            ("?controller_id=legacy", {
                "source_controller_id": "legacy", "target_controller_id": "legacy",
                "source_template_id": 145, "target_name": "Query selector",
            }),
        )
        try:
            for suffix, body in cases:
                request = Request(
                    base + "/api/vendor/templates/clone" + suffix,
                    data=json.dumps(body).encode(), method="POST",
                    headers={"Content-Type": "application/json"},
                )
                with self.subTest(suffix=suffix), self.assertRaises(HTTPError) as caught:
                    urlopen(request, timeout=2)
                self.assertEqual(caught.exception.code, 400)
                caught.exception.close()
            service.clone_vendor_template.assert_not_called()
        finally:
            protected.shutdown()
            protected.server_close()
            thread.join(timeout=2)


if __name__ == "__main__":
    unittest.main()
