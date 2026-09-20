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
        for path in ("/api/routers", "/api/templates", "/api/jobs", "/api/alerts", "/api/audit"):
            _, _, result = self.request("GET", path)
            self.assertIsInstance(result["items"], list)

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
            body = {"source_id": 145, "target_name": "S21BasePriceTag_V1_BOLD"}
            clone = Request(base + "/api/vendor/templates/clone", data=json.dumps(body).encode(),
                            method="POST", headers={"Content-Type": "application/json",
                                                    "Cookie": cookie, "Origin": base})
            with urlopen(clone, timeout=2) as response:
                self.assertEqual(response.status, 201)
                self.assertEqual(json.loads(response.read())["id"], "200")
            service.clone_vendor_template.assert_called_once_with(
                vendor, body, controller_id="legacy"
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
                    "source_id": 145, "target_name": "S21BasePriceTag_V1_BOLD",
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


if __name__ == "__main__":
    unittest.main()
