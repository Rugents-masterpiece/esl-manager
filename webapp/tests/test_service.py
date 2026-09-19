import copy
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

    def _clone_client(self):
        class FakeCloneClient:
            def __init__(self):
                self.calls = []
                self.source_layout = [
                    {"id": 501, "name": "text1", "type": "text", "feil": "text", "mpname": "name", "text": "Coffee",
                     "style": {"left": "3px", "font-weight": "400"}},
                    {"id": 502, "name": "text2", "type": "text", "feil": "text", "mpname": "price", "text": "9.99",
                     "style": {"top": "7px", "font-weight": "400"}},
                    {"id": 503, "name": "image1", "type": "image", "feil": "photo", "mpname": "logo", "src": "logo.png",
                     "style": {"left": "9px"}},
                ]
                self.target_layout = [
                    {"id": 9001, "name": "text1", "type": "text", "feil": "text", "mpname": "name", "text": "default",
                     "style": {"left": "0px", "font-weight": "400"}},
                ]
                self.target_name = "Default Template200"
                self.created = False
                self.deleted = False
                self.next_id = 9002
                self.unrelated_created = False

            @staticmethod
            def detail_layout(layout, style_id):
                return [{
                    "id": item["id"], "styleid": style_id, "name": item["name"],
                    "columnType": item["type"], "sourceColumn": item["feil"],
                    "text": item.get("text"), "src": item.get("src"),
                    "left": item.get("style", {}).get("left"),
                    "top": item.get("style", {}).get("top"),
                    "fontBold": (
                        "bold" if str(item.get("style", {}).get("font-weight")) == "700"
                        else "normal"
                    ),
                } for item in layout]

            def get_style_catalog(self):
                self.calls.append(("catalog",))
                items = [{"id": 145, "name": "S21BasePriceTag_V1", "width": 250,
                          "height": 122, "mappingtype": 291, "type": 2}]
                if self.created and not self.deleted:
                    items.append({"id": 200, "name": self.target_name, "width": 250,
                                  "height": 122, "mappingtype": 700, "type": 2})
                if self.unrelated_created:
                    items.append({"id": 201, "name": "Concurrent unrelated template", "width": 400,
                                  "height": 300, "mappingtype": 701, "type": 4})
                return items

            def get_style_data(self, style_id):
                self.calls.append(("data", style_id))
                if style_id == 145:
                    return {"id": 145, "name": "S21BasePriceTag_V1", "mappingtype": 291,
                            "width": 250, "height": 122, "type": 9,
                            "dispMs": self.detail_layout(self.source_layout, 145)}
                if style_id == 201:
                    return {"id": 201, "name": "Concurrent unrelated template", "mappingtype": 701,
                            "styleFileds": ["other"], "dispMs": []}
                return {"id": 200, "name": self.target_name, "mappingtype": 700,
                        "width": 250, "height": 122, "type": 9,
                        "dispMs": self.detail_layout(self.target_layout, 200)}

            def get_style_detail(self, style_id):
                self.calls.append(("metadata", style_id))
                if style_id == 145:
                    return {"id": 145, "name": "S21BasePriceTag_V1", "width": 250,
                            "height": 122, "mappingtype": 291, "type": 2,
                            "styleFileds": ["name", "price", "logo"]}
                return {"id": 200, "name": self.target_name, "width": 250,
                        "height": 122, "mappingtype": 700, "type": 2,
                        "styleFileds": [item["mpname"] for item in self.target_layout]}

            def get_style_layout(self, style_id):
                self.calls.append(("layout", style_id))
                return copy.deepcopy(self.source_layout if style_id == 145 else self.target_layout)

            def get_template_preview(self, style_id):
                self.calls.append(("preview", style_id))
                return (b"source-preview" if style_id == 145 else b"target-preview", "image/png")

            def create_style(self, style_align) -> int:
                self.calls.append(("create", style_align))
                self.created = True
                return 200

            def add_style_field(self, style_id, mapping_type, column_name, mapping_text):
                self.calls.append(("field", style_id, mapping_type, column_name, mapping_text))
                source = next(item for item in self.source_layout if item["mpname"] == mapping_text)
                added = copy.deepcopy(source)
                added["id"] = self.next_id
                self.next_id += 1
                self.target_layout.append(added)
                return 1

            def rename_style(self, style_id, style_align, target_name):
                self.calls.append(("rename", style_id, style_align, target_name))
                self.target_name = target_name
                return 1

            def save_style_layout(self, style_id, layout):
                self.calls.append(("save", style_id, copy.deepcopy(layout)))
                self.target_layout = copy.deepcopy(layout)
                return {"resultCode": 10}

            def delete_style(self, style_id):
                self.calls.append(("delete", style_id))
                self.deleted = True

        return FakeCloneClient()

    def test_clone_template_deep_copies_bold_layout_with_server_ids_and_audit(self):
        client = self._clone_client()
        source_before = copy.deepcopy(client.source_layout)
        result = self.service.clone_vendor_template(client, {
            "source_id": 145, "target_name": "S21BasePriceTag_V1_BOLD",
        })

        self.assertEqual(result["id"], "200")
        self.assertEqual(result["name"], "S21BasePriceTag_V1_BOLD")
        self.assertEqual(client.source_layout, source_before)
        saved = next(call[2] for call in client.calls if call[0] == "save")
        self.assertEqual([item["id"] for item in saved], [9001, 9002, 9003])
        self.assertEqual(saved[0]["style"], {"left": "3px", "font-weight": "700"})
        self.assertEqual(saved[1]["style"], {"top": "7px", "font-weight": "700"})
        self.assertEqual(saved[2], {**source_before[2], "id": 9003})
        self.assertEqual([call[-1] for call in client.calls if call[0] == "field"],
                         ["price", "logo"])
        self.assertEqual(sum(call[0] == "create" for call in client.calls), 1)
        self.assertEqual(sum(call[0] == "save" for call in client.calls), 1)
        self.assertGreaterEqual(sum(call == ("data", 200) for call in client.calls), 4)
        self.assertEqual(sum(call == ("metadata", 145) for call in client.calls), 2)
        self.assertEqual(sum(call == ("metadata", 200) for call in client.calls), 1)
        event = self.service.list_audit(action="vendor.template.cloned")[0]
        self.assertEqual(event["entity_id"], "200")
        self.assertEqual(event["details"]["source_id"], 145)

    def test_clone_rejects_unknown_source_and_duplicate_name_before_mutation(self):
        client = self._clone_client()
        with self.assertRaises(ValidationError):
            self.service.clone_vendor_template(client, {"source_id": 999, "target_name": "X"})
        client.target_name = "Already there"
        client.created = True
        with self.assertRaises(ConflictError):
            self.service.clone_vendor_template(client, {
                "source_id": 145, "target_name": "Already there",
            })
        self.assertFalse(any(call[0] == "create" for call in client.calls))

    def test_clone_rolls_back_only_created_id_and_verifies_absence(self):
        client = self._clone_client()
        client.save_style_layout = Mock(side_effect=RuntimeError("ambiguous status"))
        with self.assertRaises(IntegrationError):
            self.service.clone_vendor_template(client, {
                "source_id": 145, "target_name": "S21BasePriceTag_V1_BOLD",
            })
        self.assertIn(("delete", 200), client.calls)
        self.assertNotIn(("delete", 145), client.calls)
        self.assertEqual(sum(call[0] == "create" for call in client.calls), 1)

    def test_clone_reconciles_ambiguous_mutation_errors_without_retrying(self):
        client = self._clone_client()
        original_add = client.add_style_field
        original_rename = client.rename_style
        original_save = client.save_style_layout
        counts = {"field": 0, "rename": 0, "save": 0}

        def ambiguous(name, operation):
            def call(*args):
                counts[name] += 1
                operation(*args)
                raise RuntimeError("ambiguous transport status")
            return call

        client.add_style_field = ambiguous("field", original_add)
        client.rename_style = ambiguous("rename", original_rename)
        client.save_style_layout = ambiguous("save", original_save)
        result = self.service.clone_vendor_template(client, {
            "source_id": 145, "target_name": "S21BasePriceTag_V1_BOLD",
        })
        self.assertEqual(result["id"], "200")
        self.assertEqual(counts, {"field": 2, "rename": 1, "save": 1})

    def test_clone_never_adopts_or_mutates_delta_without_a_create_response_id(self):
        client = self._clone_client()

        def ambiguous_create(style_align):
            client.calls.append(("create", style_align))
            client.created = True
            client.unrelated_created = True
            raise RuntimeError("response lost")

        client.create_style = ambiguous_create
        with self.assertRaisesRegex(IntegrationError, "create outcome"):
            self.service.clone_vendor_template(client, {
                "source_id": 145, "target_name": "S21BasePriceTag_V1_BOLD",
            })
        self.assertFalse(any(call[0] in {"field", "rename", "save", "delete"}
                             for call in client.calls))

    def test_clone_response_mismatch_never_touches_the_unrelated_delta(self):
        client = self._clone_client()

        def mismatched_create(style_align):
            client.calls.append(("create", style_align))
            client.created = True
            client.unrelated_created = True
            return 202

        client.create_style = mismatched_create
        with self.assertRaisesRegex(IntegrationError, "create outcome"):
            self.service.clone_vendor_template(client, {
                "source_id": 145, "target_name": "S21BasePriceTag_V1_BOLD",
            })
        self.assertFalse(any(call[0] in {"field", "rename", "save", "delete"}
                             for call in client.calls))

    def test_clone_with_multiple_new_ids_mutates_only_response_owned_id(self):
        client = self._clone_client()
        original_create = client.create_style

        def concurrent_create(style_align):
            result = original_create(style_align)
            client.unrelated_created = True
            return result

        client.create_style = concurrent_create
        result = self.service.clone_vendor_template(client, {
            "source_id": 145, "target_name": "S21BasePriceTag_V1_BOLD",
        })
        self.assertEqual(result["id"], "200")
        mutated_ids = [call[1] for call in client.calls
                       if call[0] in {"field", "rename", "save", "delete"}]
        self.assertTrue(mutated_ids)
        self.assertEqual(set(mutated_ids), {200})

    def test_clone_accepts_ambiguous_rollback_delete_when_readback_proves_absence(self):
        client = self._clone_client()
        client.save_style_layout = Mock(side_effect=RuntimeError("save failed"))
        original_delete = client.delete_style

        def ambiguous_delete(style_id):
            original_delete(style_id)
            raise RuntimeError("delete response lost")

        client.delete_style = ambiguous_delete
        with self.assertRaisesRegex(IntegrationError, "save could not be verified"):
            self.service.clone_vendor_template(client, {
                "source_id": 145, "target_name": "S21BasePriceTag_V1_BOLD",
            })
        self.assertIn(("delete", 200), client.calls)
        self.assertTrue(client.deleted)

    def test_clone_rejects_lost_style_fields_on_final_readback(self):
        client = self._clone_client()
        original_detail = client.get_style_detail

        def detail_without_all_fields(style_id):
            result = original_detail(style_id)
            if style_id == 200 and any(call[0] == "save" for call in client.calls):
                result["styleFileds"] = ["name", "price"]
            return result

        client.get_style_detail = detail_without_all_fields
        with self.assertRaises(IntegrationError):
            self.service.clone_vendor_template(client, {
                "source_id": 145, "target_name": "S21BasePriceTag_V1_BOLD",
            })
        self.assertIn(("delete", 200), client.calls)

    def test_clone_rejects_changed_detail_layout_on_final_readback(self):
        client = self._clone_client()
        original_data = client.get_style_data

        def data_with_stale_detail_layout(style_id):
            result = original_data(style_id)
            if style_id == 200 and any(call[0] == "save" for call in client.calls):
                result["dispMs"][0]["text"] = "stale"
            return result

        client.get_style_data = data_with_stale_detail_layout
        with self.assertRaises(IntegrationError):
            self.service.clone_vendor_template(client, {
                "source_id": 145, "target_name": "S21BasePriceTag_V1_BOLD",
            })
        self.assertIn(("delete", 200), client.calls)

    def test_clone_rejects_detail_endpoint_that_did_not_persist_bold(self):
        client = self._clone_client()
        original_data = client.get_style_data

        def data_without_bold_readback(style_id):
            result = original_data(style_id)
            if style_id == 200 and any(call[0] == "save" for call in client.calls):
                for component in result["dispMs"]:
                    if component["columnType"] == "text":
                        component["fontBold"] = "normal"
            return result

        client.get_style_data = data_without_bold_readback
        with self.assertRaises(IntegrationError):
            self.service.clone_vendor_template(client, {
                "source_id": 145, "target_name": "S21BasePriceTag_V1_BOLD",
            })
        self.assertIn(("delete", 200), client.calls)

    def test_clone_rejects_changed_target_dimensions_on_final_readback(self):
        client = self._clone_client()
        original_detail = client.get_style_detail

        def changed_dimensions(style_id):
            result = original_detail(style_id)
            if style_id == 200:
                result["width"] = 251
            return result

        client.get_style_detail = changed_dimensions
        with self.assertRaises(IntegrationError):
            self.service.clone_vendor_template(client, {
                "source_id": 145, "target_name": "S21BasePriceTag_V1_BOLD",
            })
        self.assertIn(("delete", 200), client.calls)

    def test_clone_maps_preflight_vendor_failure_to_integration_error(self):
        client = self._clone_client()
        client.get_style_catalog = Mock(side_effect=RuntimeError("vendor unavailable"))
        with self.assertRaises(IntegrationError):
            self.service.clone_vendor_template(client, {
                "source_id": 145, "target_name": "S21BasePriceTag_V1_BOLD",
            })


if __name__ == "__main__":
    unittest.main()
