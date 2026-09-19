import sqlite3
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock

from esl_web.service import ConflictError, IntegrationError, NotFoundError, Service, ValidationError
from esl_web.storage import Storage


class ServiceTests(unittest.TestCase):
    def test_vendor_sync_rejects_missing_and_conflicting_merge_records(self):
        router = {"id": "1", "ip": "127.0.0.1", "state": True, "description": "Router"}
        mms_style = {"id": "10", "name": "Desk", "styleLen": "400x300"}
        catalog_style = {
            "id": 10, "name": "Desk", "descriptor": "Desk", "width": 400,
            "height": 300, "mappingtype": 1, "type": 2,
        }
        mms_tag = {
            "mac": "99.99.33.35", "power": 90, "routerMac": "1", "styleName": "Desk",
            "updateProgress": 1,
        }
        extended_tag = {
            "mac": "99.99.33.35", "power": 89, "routerid": "1", "styleId": 10,
            "status": 1, "width": 400, "height": 300, "rssi": -50,
        }
        cases = (
            {"templates": [mms_style], "catalog": [catalog_style],
             "tags": [mms_tag], "extended": []},
            {"templates": [mms_style], "catalog": [catalog_style],
             "tags": [], "extended": [extended_tag]},
            {"templates": [mms_style], "catalog": [], "tags": [], "extended": []},
            {"templates": [mms_style], "catalog": [{**catalog_style, "name": "Other"}],
             "tags": [], "extended": []},
        )
        for case in cases:
            client = Mock()
            client.get_routers.return_value = [router]
            client.get_templates.return_value = case["templates"]
            client.get_tags.return_value = case["tags"]
            client.get_style_catalog.return_value = case["catalog"]
            client.get_extended_tags.return_value = case["extended"]
            with self.subTest(case=case), self.assertRaises(IntegrationError):
                self.service.sync_read_only(client)

    def test_schema_migration_preserves_existing_template_and_tag_rows(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "legacy.db"
            connection = sqlite3.connect(path)
            connection.executescript("""
                CREATE TABLE templates (
                    id TEXT PRIMARY KEY, name TEXT NOT NULL UNIQUE, width INTEGER NOT NULL,
                    height INTEGER NOT NULL, mapping_type INTEGER NOT NULL DEFAULT 0
                );
                CREATE TABLE tags (
                    id TEXT PRIMARY KEY, mac TEXT NOT NULL UNIQUE, label TEXT, width INTEGER NOT NULL,
                    height INTEGER NOT NULL, battery INTEGER NOT NULL, rssi INTEGER NOT NULL,
                    status TEXT NOT NULL, router_id TEXT, template_id TEXT, last_seen_at TEXT
                );
                INSERT INTO templates VALUES ('10', 'Kept template', 400, 300, 1);
                INSERT INTO tags VALUES ('tag-1', '99.99.33.35', 'Kept tag', 400, 300, 90, -50,
                                         'ready', NULL, '10', '2026-01-01T00:00:00Z');
            """)
            connection.commit()
            connection.close()

            storage = Storage(path)
            storage.initialize()
            with storage.connection() as migrated:
                self.assertEqual(migrated.execute("SELECT COUNT(*) FROM templates").fetchone()[0], 1)
                self.assertEqual(migrated.execute("SELECT COUNT(*) FROM tags").fetchone()[0], 1)
                template_columns = {row[1] for row in migrated.execute("PRAGMA table_info(templates)")}
                tag_columns = {row[1] for row in migrated.execute("PRAGMA table_info(tags)")}
            self.assertTrue({"descriptor", "style_fields", "background_id"} <= template_columns)
            self.assertTrue({"show_style", "vendor_tag_id", "router_status"} <= tag_columns)

    def test_vendor_integer_value_rejects_ambiguous_or_invalid_numbers(self):
        for value in (True, 1.5, "1.5", "invalid", float("inf"), 1e100,
                      str(2**63), str(-(2**63) - 1)):
            with self.subTest(value=value), self.assertRaises(IntegrationError):
                Service._vendor_integer_value(value, "field", minimum=1)
        self.assertEqual(Service._vendor_integer_value("5", "field", minimum=1), 5)

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
