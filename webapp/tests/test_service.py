import tempfile
import unittest
from pathlib import Path

from esl_web.service import ConflictError, NotFoundError, Service, ValidationError
from esl_web.storage import Storage


class ServiceTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.storage = Storage(Path(self.temporary.name) / "esl.db")
        self.storage.initialize()
        self.storage.seed_demo()
        self.service = Service(self.storage)

    def tearDown(self):
        self.temporary.cleanup()

    def test_product_lifecycle_validates_and_audits_mutations(self):
        created = self.service.create_product(
            {"id": "prod-milk", "sku": "MILK-1", "ean": "8580000000035", "name": "Mlieko", "price": 1.59}
        )
        self.assertEqual(created["currency"], "EUR")
        self.assertEqual(self.service.get_product("prod-milk")["sku"], "MILK-1")
        self.assertEqual([item["id"] for item in self.service.list_products(search="mlie")], ["prod-milk"])

        updated = self.service.update_product("prod-milk", {"price": 1.79, "name": "Mlieko 1L"})
        self.assertEqual(updated["price"], 1.79)
        with self.assertRaises(ValidationError):
            self.service.create_product({"id": "bad id", "sku": "X", "name": "X", "price": -1})
        with self.assertRaises(ConflictError):
            self.service.create_product({"id": "other", "sku": "MILK-1", "name": "X", "price": 1})

        self.service.delete_product("prod-milk")
        with self.assertRaises(NotFoundError):
            self.service.get_product("prod-milk")
        actions = [event["action"] for event in self.service.list_audit()]
        self.assertIn("product.created", actions)
        self.assertIn("product.updated", actions)
        self.assertIn("product.deleted", actions)

    def test_inventory_filters_dashboard_and_binding_lifecycle(self):
        bound = self.service.bind_tag("prod-tea", "tag-002")
        self.assertEqual(bound, {"product_id": "prod-tea", "tag_id": "tag-002"})
        self.assertEqual(self.service.list_tags(status="failed")[0]["product_id"], "prod-tea")
        with self.assertRaises(ConflictError):
            self.service.bind_tag("prod-coffee", "tag-002")

        dashboard = self.service.dashboard()
        self.assertEqual(dashboard["products"], 2)
        self.assertEqual(dashboard["bound_tags"], 2)
        self.assertEqual(dashboard["active_alerts"], 1)
        self.assertEqual(len(self.service.list_routers(status="online")), 1)
        self.assertEqual(len(self.service.list_templates(search="základ")), 1)
        self.assertEqual(len(self.service.list_alerts(active=True)), 1)

        self.service.unbind_tag("prod-tea", "tag-002")
        self.assertIsNone(self.service.get_tag("tag-002")["product_id"])
        with self.assertRaises(NotFoundError):
            self.service.unbind_tag("prod-tea", "tag-002")

    def test_bulk_jobs_simulate_failures_and_retry_without_vendor_calls(self):
        self.service.bind_tag("prod-tea", "tag-002")
        queued = self.service.queue_bulk_update({"product_ids": ["prod-coffee", "prod-tea"]})
        self.assertEqual(queued["status"], "queued")
        self.assertEqual(queued["total_items"], 2)

        processed = self.service.simulate_job(queued["id"], {"fail_tag_ids": ["tag-002"]})
        self.assertEqual(processed["status"], "partial")
        self.assertEqual(processed["succeeded_items"], 1)
        self.assertEqual(processed["failed_items"], 1)
        self.assertEqual(len(self.service.list_jobs(status="partial")), 1)
        self.assertTrue(self.service.list_alerts(kind="failed_update"))

        retried = self.service.retry_failed_items(queued["id"])
        self.assertEqual(retried["status"], "queued")
        self.assertEqual(sum(item["status"] == "queued" for item in retried["items"]), 1)
        completed = self.service.simulate_job(queued["id"], {})
        self.assertEqual(completed["status"], "completed")
        self.assertEqual(completed["succeeded_items"], 2)
        with self.assertRaises(ConflictError):
            self.service.retry_failed_items(queued["id"])
        with self.assertRaises(NotFoundError):
            self.service.queue_bulk_update({"product_ids": ["missing"]})

    def test_non_finite_product_prices_are_rejected(self):
        for value in (float("nan"), float("inf"), float("-inf")):
            with self.subTest(value=value), self.assertRaises(ValidationError):
                self.service.create_product({
                    "id": "prod-nonfinite", "sku": "NONFINITE", "name": "Bad", "price": value
                })


if __name__ == "__main__":
    unittest.main()
