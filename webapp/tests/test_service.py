import copy
import json
import os
import sqlite3
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

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

    def test_vendor_sync_matches_decimal_and_dotted_tag_identity_and_infers_model(self):
        client = Mock()
        client.get_routers.return_value = [
            {"id": "1", "ip": "127.0.0.1", "state": True, "description": "Router"}
        ]
        client.get_templates.return_value = [
            {"id": "145", "name": "Supported", "styleLen": "296x128"}
        ]
        client.get_style_catalog.return_value = [{
            "id": 145, "name": "Supported", "descriptor": "Supported",
            "width": 296, "height": 128, "mappingtype": 2, "type": 2,
        }]
        client.get_tags.return_value = [{
            "mac": "1331705177", "power": 90, "routerMac": "1",
            "styleName": "Supported", "updateProgress": 1,
        }]
        client.get_extended_tags.return_value = [{
            "mac": "79.96.53.89", "routerid": "1", "styleId": 145,
            "status": 1, "width": 296, "height": 128, "rssi": -50,
        }]
        with self.storage.connection() as connection:
            connection.execute(
                "UPDATE tags SET mac = '1331705177' WHERE id = 'tag-001'"
            )

        self.assertEqual(self.service.sync_read_only(client)["synced"]["tags"], 1)
        with self.storage.connection() as connection:
            row = connection.execute(
                "SELECT id, mac, width, height, device_model_id FROM tags "
                "WHERE mac = '79.96.53.89'"
            ).fetchone()
        self.assertIsNotNone(row)
        self.assertEqual(row["id"], "tag-001")
        self.assertEqual(tuple(row)[1:], ("79.96.53.89", 296, 128, "2.9EPD-BWR"))

    def test_vendor_sync_rejects_malformed_or_overflow_tag_identities(self):
        for identity in (
                "4294967296", "9" * 5000, "-1", "1.2.3", "1.2.3.256",
                "1.2.3.4.5", "abc", "١"):
            client = Mock()
            client.get_routers.return_value = []
            client.get_templates.return_value = []
            client.get_style_catalog.return_value = []
            client.get_tags.return_value = [{
                "mac": identity, "power": 90, "updateProgress": 1,
            }]
            client.get_extended_tags.return_value = [{
                "mac": identity, "status": 1, "width": 296, "height": 128,
            }]
            with self.subTest(identity=identity), self.assertRaises(IntegrationError):
                self.service.sync_read_only(client)
        with self.assertRaises(IntegrationError):
            Service._vendor_tag_identity(10 ** 5000)

    def test_vendor_sync_keeps_48_bit_mac_distinct_from_uint32_identity(self):
        client = Mock()
        client.get_routers.return_value = []
        client.get_templates.return_value = []
        client.get_style_catalog.return_value = []
        client.get_tags.return_value = [
            {"mac": "000000000001", "power": 90, "updateProgress": 1},
            {"mac": "1", "power": 80, "updateProgress": 1},
        ]
        client.get_extended_tags.return_value = [
            {"mac": "00:00:00:00:00:01", "status": 1, "width": 296, "height": 128},
            {"mac": "0.0.0.1", "status": 1, "width": 296, "height": 128},
        ]

        self.assertEqual(self.service.sync_read_only(client)["synced"]["tags"], 2)
        self.assertEqual(self.service.sync_read_only(client)["synced"]["tags"], 2)
        with self.storage.connection() as connection:
            rows = [tuple(row) for row in connection.execute(
                "SELECT mac, COUNT(*) FROM tags WHERE mac IN (?, ?) GROUP BY mac ORDER BY mac",
                ("00:00:00:00:00:01", "0.0.0.1"),
            )]
        self.assertEqual(rows, [("0.0.0.1", 1), ("00:00:00:00:00:01", 1)])

    def test_template_list_exposes_only_safe_vendor_preview_urls(self):
        with self.storage.connection() as connection:
            connection.execute(
                "UPDATE templates SET vendor_id = '145' WHERE id = 'tpl-default'"
            )
            connection.execute(
                "INSERT INTO templates(id, controller_id, vendor_id, name, width, height, "
                "mapping_type) VALUES ('local-template', 'legacy', 'local-template', "
                "'Lokálna', 296, 128, 0)"
            )
        templates = {item["id"]: item for item in self.service.list_templates()}
        self.assertEqual(
            templates["tpl-default"]["preview_url"],
            "/api/vendor/templates/145/preview?controller_id=legacy",
        )
        self.assertIsNone(templates["local-template"]["preview_url"])

    def test_vendor_sync_preserves_unsupported_tag_dimensions_as_read_only(self):
        client = Mock()
        client.get_routers.return_value = []
        client.get_templates.return_value = []
        client.get_style_catalog.return_value = [{
            "id": 300, "name": "Unsupported", "descriptor": "Unsupported",
            "width": 800, "height": 480, "mappingtype": 1, "type": 2,
        }]
        client.get_tags.return_value = [{
            "mac": "3232235777", "power": 70, "styleName": "Unsupported",
            "updateProgress": 1,
        }]
        client.get_extended_tags.return_value = [{
            "mac": "192.168.1.1", "styleId": 300, "status": 1,
            "width": 800, "height": 480, "rssi": -60,
        }]

        self.service.sync_read_only(client)
        with self.storage.connection() as connection:
            row = connection.execute(
                "SELECT id, width, height, device_model_id FROM tags "
                "WHERE mac = '192.168.1.1'"
            ).fetchone()
        self.assertIsNotNone(row)
        self.assertEqual(tuple(row)[1:], (800, 480, None))
        detail = self.service.get_tag(row["id"])
        self.assertFalse(detail["management_supported"])
        self.assertNotIn(row["id"], {item["id"] for item in self.service.list_tags()})

    def test_vendor_sync_persists_full_catalog_with_mms_subset_and_is_idempotent(self):
        supported = [
            (145, 250, 132), (147, 250, 132), (149, 250, 122),
            (158, 250, 122), (159, 296, 128), (160, 296, 128),
        ]
        filler = [(identifier, 400, 300) for identifier in range(200, 259)]
        catalog = [{
            "id": identifier, "name": f"Style {identifier}",
            "descriptor": f"Style {identifier}", "width": width, "height": height,
            "mappingtype": 1, "type": 2,
        } for identifier, width, height in supported + filler]
        client = Mock()
        client.get_routers.return_value = []
        client.get_templates.return_value = [{
            "id": str(item["id"]), "name": item["name"],
            "styleLen": f"{item['width']}x{item['height']}",
        } for item in catalog[-4:]]
        client.get_tags.return_value = []
        client.get_style_catalog.return_value = catalog
        client.get_extended_tags.return_value = []

        first = self.service.sync_read_only(client)
        second = self.service.sync_read_only(client)
        self.assertEqual(first["synced"]["templates"], 65)
        self.assertEqual(second["synced"]["templates"], 65)
        with self.storage.connection() as connection:
            rows = connection.execute(
                "SELECT vendor_id, width, height FROM templates "
                "WHERE vendor_id IN ('145', '147', '149', '158', '159', '160') "
                "ORDER BY CAST(vendor_id AS INTEGER)"
            ).fetchall()
            catalog_count = connection.execute(
                "SELECT COUNT(*) FROM templates WHERE vendor_id IN ("
                + ",".join("?" for _item in catalog) + ")",
                tuple(str(item["id"]) for item in catalog),
            ).fetchone()[0]
        self.assertEqual(catalog_count, 65)
        self.assertEqual([tuple(row) for row in rows], [
            ("145", 250, 132), ("147", 250, 132), ("149", 250, 122),
            ("158", 250, 122), ("159", 296, 128), ("160", 296, 128),
        ])

    def test_sync_audit_is_controller_distinguishable(self):
        client = Mock()
        client.get_routers.return_value = []
        client.get_templates.return_value = []
        client.get_tags.return_value = []
        client.get_style_catalog.return_value = []
        client.get_extended_tags.return_value = []

        self.service.sync_read_only(client, controller_id="north")
        self.service.sync_read_only(client, controller_id="south")

        events = self.service.list_audit(action="vendor.sync.read_only")
        self.assertEqual(
            {(event["entity_id"], event["details"]["controller_id"]) for event in events},
            {("north:vendor", "north"), ("south:vendor", "south")},
        )

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

    def test_tag_list_and_detail_include_controller_hardware_and_local_data(self):
        with self.storage.connection() as connection:
            connection.execute("UPDATE controllers SET name = 'Legacy north'")
            connection.execute(
                "UPDATE tags SET device_model_id = '2.9EPD-BWR', test_data = ?, "
                "inventory_source = 'vendor', configuration_source = 'vendor' "
                "WHERE id = 'tag-001'",
                (json.dumps({"price": "6.49", "name": "Káva"}),),
            )

        listed = next(item for item in self.service.list_tags() if item["id"] == "tag-001")
        detail = self.service.get_tag("tag-001")

        for item in (listed, detail):
            self.assertEqual(item["controller"], {
                "id": "legacy", "name": "Legacy north", "is_default": True,
            })
            self.assertEqual(item["rf_router"]["id"], "router-main")
            self.assertEqual(item["device_model"]["id"], "2.9EPD-BWR")
            self.assertEqual((item["device_model"]["width"], item["device_model"]["height"]),
                             (296, 128))
            self.assertEqual(item["compatible_template"]["id"], "tpl-default")
            self.assertEqual(item["test_data"], {"price": "6.49", "name": "Káva"})
            self.assertEqual(item["inventory_source"], "vendor")
            self.assertEqual(item["configuration_source"], "vendor")
            self.assertFalse(item["staged"])

    def test_unsupported_inventory_is_preserved_but_excluded_from_supported_management(self):
        with self.storage.connection() as connection:
            connection.execute(
                "INSERT INTO tags(id, controller_id, vendor_id, mac, label, width, height, "
                "battery, rssi, status, router_id, template_id) VALUES "
                "('legacy-unsupported', 'legacy', 'legacy-unsupported', "
                "'AA:BB:CC:DD:EE:88', 'Old hardware', 400, 300, 80, -50, 'ready', "
                "'router-main', 'tpl-default')"
            )

        self.assertNotIn("legacy-unsupported", {item["id"] for item in self.service.list_tags()})
        detail = self.service.get_tag("legacy-unsupported")
        self.assertEqual((detail["width"], detail["height"]), (400, 300))
        self.assertIsNone(detail["device_model"])
        self.assertEqual(detail["device_model_state"], "unsupported")
        self.assertFalse(detail["management_supported"])
        self.assertIsNone(detail["compatible_template"])
        self.assertEqual(detail["template_compatibility"], "incompatible")

        supported_payload = {
            "controller_id": "legacy", "mac": "AA:BB:CC:DD:EE:88",
            "label": "Converted", "device_model_id": "2.9EPD-BWR",
            "width": 296, "height": 128, "router_id": "router-main",
            "template_id": "tpl-default", "test_data": {},
        }
        with self.assertRaises(ValidationError) as caught:
            self.service.update_tag_configuration("legacy-unsupported", supported_payload)
        self.assertIn("unsupported", caught.exception.message.lower())
        unchanged = self.service.get_tag("legacy-unsupported")
        self.assertFalse(unchanged["management_supported"])
        self.assertEqual((unchanged["width"], unchanged["height"]), (400, 300))
        self.assertEqual(unchanged["label"], "Old hardware")

    def test_incompatible_historical_template_link_is_not_reported_as_compatible(self):
        with self.storage.connection() as connection:
            connection.execute(
                "INSERT INTO controllers(id, name, is_default) VALUES ('south', 'South', 0)"
            )
            connection.execute(
                "INSERT INTO templates(id, controller_id, vendor_id, name, width, height) "
                "VALUES ('south-template', 'south', '1', 'South template', 296, 128)"
            )
            connection.execute(
                "UPDATE tags SET device_model_id = '2.9EPD-BWR', "
                "template_id = 'south-template' WHERE id = 'tag-001'"
            )

        detail = self.service.get_tag("tag-001")
        self.assertEqual(detail["device_model_state"], "supported")
        self.assertTrue(detail["management_supported"])
        self.assertIsNone(detail["compatible_template"])
        self.assertEqual(detail["template_compatibility"], "incompatible")
        self.assertEqual(detail["template_id"], "south-template")

    def test_create_staged_tag_normalizes_mac_and_audits_controller_identity(self):
        created = self.service.create_staged_tag({
            "id": "tag-local", "controller_id": "legacy", "mac": "aabb.ccdd.eeff",
            "label": "Local shelf", "device_model_id": "2.9EPD-BWR",
            "width": 296, "height": 128, "router_id": "router-main",
            "template_id": "tpl-default", "test_data": {"name": "Test", "price": 1.25},
        })

        self.assertEqual(created["mac"], "AA:BB:CC:DD:EE:FF")
        self.assertEqual(self.storage.normalized_mac("000000000001"), "00:00:00:00:00:01")
        self.assertEqual(created["inventory_source"], "local")
        self.assertEqual(created["configuration_source"], "local")
        self.assertTrue(created["staged"])
        self.assertEqual(created["test_data"], {"name": "Test", "price": 1.25})
        event = self.service.list_audit(action="tag.staged")[0]
        self.assertEqual(event["entity_id"], "tag-local")
        self.assertEqual(event["details"]["controller_id"], "legacy")
        self.assertEqual(event["details"]["mac"], "AA:BB:CC:DD:EE:FF")

    def test_update_tag_configuration_is_local_and_preserves_vendor_inventory_origin(self):
        updated = self.service.update_tag_configuration("tag-001", {
            "controller_id": "legacy", "mac": "0011-2233-4455", "label": "Local override",
            "device_model_id": "2.9EPD-BWR", "width": 296, "height": 128,
            "router_id": "router-main", "template_id": "tpl-default",
            "test_data": {"name": "Override"},
        })

        self.assertEqual(updated["mac"], "00:11:22:33:44:55")
        self.assertEqual(updated["inventory_source"], "vendor")
        self.assertEqual(updated["configuration_source"], "local")
        self.assertFalse(updated["staged"])
        self.assertEqual(updated["label"], "Local override")
        event = self.service.list_audit(action="tag.configuration.updated")[0]
        self.assertEqual(event["details"]["controller_id"], "legacy")
        self.assertEqual(event["details"]["inventory_source"], "vendor")

    def test_staged_tag_validation_rejects_collisions_unknowns_and_cross_controller_links(self):
        with self.storage.connection() as connection:
            connection.execute("UPDATE controllers SET is_default = 0")
            connection.executemany(
                "INSERT INTO controllers(id, name, is_default) VALUES (?, ?, ?)",
                [("north", "North", 1), ("south", "South", 0)],
            )
            connection.executemany(
                "INSERT INTO routers(id, controller_id, vendor_id, name, address, status) "
                "VALUES (?, ?, ?, ?, ?, 'online')",
                [("north-router", "north", "1", "North router", "10.0.0.1"),
                 ("south-router", "south", "1", "South router", "10.0.1.1")],
            )
            connection.executemany(
                "INSERT INTO templates(id, controller_id, vendor_id, name, width, height) "
                "VALUES (?, ?, ?, ?, ?, ?)",
                [("north-template", "north", "1", "North template", 250, 122),
                 ("south-template", "south", "1", "South template", 250, 122),
                 ("wrong-size", "north", "2", "Wrong size", 296, 128)],
            )
            connection.execute(
                "INSERT INTO device_models(id, name, width, height, alignment_id, screen_type) "
                "VALUES ('unsupported', 'Unsupported', 250, 122, 99, 99)"
            )
        valid = {
            "controller_id": "north", "mac": "AA:BB:CC:DD:EE:01", "label": "Test",
            "device_model_id": "2.13EPD-BWR", "width": 250, "height": 122,
            "router_id": "north-router", "template_id": "north-template", "test_data": {},
        }
        self.service.create_staged_tag(valid)
        cases = (
            ({**valid, "mac": "aabb.ccdd.ee01"}, ConflictError),
            ({**valid, "mac": "AA:BB:CC:DD:EE:02", "controller_id": "missing"}, ValidationError),
            ({**valid, "mac": "AA:BB:CC:DD:EE:03", "device_model_id": "unknown"}, ValidationError),
            ({**valid, "mac": "AA:BB:CC:DD:EE:0A", "device_model_id": "unsupported"}, ValidationError),
            ({**valid, "mac": "AA:BB:CC:DD:EE:04", "height": 123}, ValidationError),
            ({**valid, "mac": "AA:BB:CC:DD:EE:05", "router_id": "south-router"}, ValidationError),
            ({**valid, "mac": "AA:BB:CC:DD:EE:06", "template_id": "south-template"}, ValidationError),
            ({**valid, "mac": "AA:BB:CC:DD:EE:07", "template_id": "wrong-size"}, ValidationError),
            ({**valid, "mac": "not-a-mac"}, ValidationError),
            ({**valid, "mac": "AA:BB:CC:DD:EE:08", "test_data": []}, ValidationError),
        )
        for payload, error_type in cases:
            with self.subTest(payload=payload), self.assertRaises(error_type):
                self.service.create_staged_tag(payload)

        second = {**valid, "mac": "AA:BB:CC:DD:EE:09"}
        second_tag = self.service.create_staged_tag(second)
        with self.assertRaises(ConflictError):
            self.service.update_tag_configuration(second_tag["id"], {
                **second, "mac": "aabb-ccdd-ee01",
            })
        with self.assertRaises(ValidationError):
            self.service.update_tag_configuration(second_tag["id"], {
                **second, "router_id": "south-router",
            })

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

    def test_live_dispatch_updates_only_the_selected_controller_scope(self):
        with self.storage.connection() as connection:
            connection.execute("UPDATE controllers SET is_default = 0")
            connection.executemany(
                "INSERT INTO controllers(id, name, is_default) VALUES (?, ?, ?)",
                [("north", "North", 1), ("south", "South", 0)],
            )
            tag = {
                "id": "tag-7", "mac": "00:11:22:33:44:77", "label": None,
                "width": 250, "height": 122, "battery": 80, "rssi": -50,
                "status": "ready", "router_id": None, "template_id": None,
                "last_seen_at": None, "vendor_tag_id": 7,
            }
            self.storage.upsert_tag(connection, tag, controller_id="north")
            self.storage.upsert_tag(connection, tag, controller_id="south")
        client = Mock()
        client.update_screen.return_value = [
            {"mac": "00:11:22:33:44:77", "_verified_status": "success"}
        ]
        payload = {"confirmation": "I CONFIRM LIVE ESL UPDATE", "updates": [{
            "mac": "00:11:22:33:44:77", "styleid": 9,
            "mappingtype": 0, "ABDisplayFlag": 161,
        }]}
        with patch.dict(os.environ, {"ESL_LIVE_WRITES": "1"}):
            self.service.dispatch_live(client, payload, controller_id="south")
        with self.storage.connection() as connection:
            self.assertEqual([tuple(row) for row in connection.execute(
                "SELECT controller_id, status FROM tags "
                "WHERE mac = '00:11:22:33:44:77' ORDER BY controller_id"
            )], [("north", "ready"), ("south", "success")])

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
                self.created_id = 200
                self.include_source = True
                self.target_width = 250
                self.target_height = 122
                self.target_alignment = 9
                self.target_screen_type = 2
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
                items = []
                if self.include_source:
                    items.append({"id": 145, "name": "S21BasePriceTag_V1", "width": 250,
                                  "height": 122, "mappingtype": 291, "type": 2})
                if self.created and not self.deleted:
                    items.append({"id": self.created_id, "name": self.target_name,
                                  "width": self.target_width, "height": self.target_height,
                                  "mappingtype": 700, "type": self.target_screen_type})
                if self.unrelated_created:
                    items.append({"id": 201, "name": "Concurrent unrelated template", "width": 400,
                                  "height": 300, "mappingtype": 701, "type": 4})
                return items

            def get_style_data(self, style_id):
                self.calls.append(("data", style_id))
                if style_id == 145 and self.include_source:
                    return {"id": 145, "name": "S21BasePriceTag_V1", "mappingtype": 291,
                            "width": 250, "height": 122, "type": 9,
                            "dispMs": self.detail_layout(self.source_layout, 145)}
                if style_id == 201:
                    return {"id": 201, "name": "Concurrent unrelated template", "mappingtype": 701,
                            "styleFileds": ["other"], "dispMs": []}
                return {"id": self.created_id, "name": self.target_name, "mappingtype": 700,
                        "width": self.target_width, "height": self.target_height,
                        "type": self.target_alignment,
                        "dispMs": self.detail_layout(self.target_layout, self.created_id)}

            def get_style_detail(self, style_id):
                self.calls.append(("metadata", style_id))
                if style_id == 145 and self.include_source:
                    return {"id": 145, "name": "S21BasePriceTag_V1", "width": 250,
                            "height": 122, "mappingtype": 291, "type": 2,
                            "styleFileds": ["name", "price", "logo"]}
                return {"id": self.created_id, "name": self.target_name,
                        "width": self.target_width, "height": self.target_height,
                        "mappingtype": 700,
                        "type": self.target_screen_type,
                        "styleFileds": [item["mpname"] for item in self.target_layout]}

            def get_style_layout(self, style_id):
                self.calls.append(("layout", style_id))
                return copy.deepcopy(
                    self.source_layout if style_id == 145 and self.include_source
                    else self.target_layout
                )

            def get_template_preview(self, style_id):
                self.calls.append(("preview", style_id))
                return (b"source-preview" if style_id == 145 and self.include_source
                        else b"target-preview", "image/png")

            def create_style(self, style_align) -> int:
                self.calls.append(("create", style_align))
                dimensions, screen_type = {
                    9: ((250, 122), 2), 8: ((250, 132), 1), 2: ((296, 128), 2),
                }[style_align]
                self.target_width, self.target_height = dimensions
                self.target_alignment = style_align
                self.target_screen_type = screen_type
                self.created = True
                return self.created_id

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

    @staticmethod
    def _remap_clone_source(client, source_id, width, height, alignment, screen_type):
        original_catalog = client.get_style_catalog
        original_data = client.get_style_data
        original_metadata = client.get_style_detail
        original_layout = client.get_style_layout
        original_preview = client.get_template_preview

        def catalog():
            items = original_catalog()
            source = next(item for item in items if item["id"] == 145)
            source.update({"id": source_id, "width": width, "height": height,
                           "type": screen_type})
            return items

        def data(style_id):
            if style_id != source_id:
                return original_data(style_id)
            result = original_data(145)
            result.update({"id": source_id, "width": width, "height": height,
                           "type": alignment})
            for component in result["dispMs"]:
                component["styleid"] = source_id
            return result

        def metadata(style_id):
            if style_id != source_id:
                return original_metadata(style_id)
            result = original_metadata(145)
            result.update({"id": source_id, "width": width, "height": height,
                           "type": screen_type})
            return result

        client.get_style_catalog = catalog
        client.get_style_data = data
        client.get_style_detail = metadata
        client.get_style_layout = lambda style_id: (
            original_layout(145) if style_id == source_id else original_layout(style_id)
        )
        client.get_template_preview = lambda style_id: (
            original_preview(145) if style_id == source_id else original_preview(style_id)
        )

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

    def test_cross_controller_clone_reads_source_and_mutates_only_target(self):
        source = self._clone_client()
        target = self._clone_client()
        source_before = copy.deepcopy(source.source_layout)

        result = self.service.clone_vendor_template(source, target, {
            "source_controller_id": "north", "target_controller_id": "south",
            "source_template_id": 145, "target_name": "Cross controller bold",
        }, source_controller_id="north", target_controller_id="south")

        self.assertEqual(result["id"], "200")
        self.assertEqual(result["source_template_id"], "145")
        self.assertEqual(result["source_controller_id"], "north")
        self.assertEqual(result["target_controller_id"], "south")
        self.assertEqual(source.source_layout, source_before)
        self.assertFalse(any(call[0] in {"create", "field", "rename", "save", "delete"}
                             for call in source.calls))
        saved = next(call[2] for call in target.calls if call[0] == "save")
        self.assertEqual([item["id"] for item in saved], [9001, 9002, 9003])
        self.assertTrue(all(item["id"] not in {501, 502, 503} for item in saved))
        self.assertEqual(
            {call[2] for call in target.calls if call[0] == "field"}, {700}
        )

    def test_explicit_same_controller_contract_keeps_single_client_safety_guards(self):
        client = self._clone_client()

        result = self.service.clone_vendor_template(client, client, {
            "source_controller_id": "north", "target_controller_id": "north",
            "source_template_id": 145, "target_name": "Same controller explicit",
        }, source_controller_id="north", target_controller_id="north")

        self.assertEqual(result["id"], "200")
        self.assertEqual(result["source_controller_id"], "north")
        self.assertEqual(result["target_controller_id"], "north")
        self.assertEqual(sum(call[0] == "create" for call in client.calls), 1)
        self.assertNotIn(("delete", 145), client.calls)

    def test_cross_controller_allows_isolated_template_id_collision(self):
        source = self._clone_client()
        target = self._clone_client()
        target.include_source = False
        target.created_id = 145

        result = self.service.clone_vendor_template(source, target, {
            "source_controller_id": "north", "target_controller_id": "south",
            "source_template_id": 145, "target_name": "Same numeric id isolated",
        }, source_controller_id="north", target_controller_id="south")

        self.assertEqual(result["id"], "145")
        self.assertFalse(any(call[0] == "delete" for call in target.calls))

    def test_cross_controller_clone_accepts_supported_dimensions_not_source_id_allowlist(self):
        source = self._clone_client()
        target = self._clone_client()
        self._remap_clone_source(source, 777, 250, 122, 9, 2)

        result = self.service.clone_vendor_template(source, target, {
            "source_controller_id": "north", "target_controller_id": "south",
            "source_template_id": 777, "target_name": "Remapped source",
        }, source_controller_id="north", target_controller_id="south")

        self.assertEqual(result["source_id"], "777")
        self.assertIn(("create", 9), target.calls)

    def test_cross_controller_clone_supports_exactly_all_three_model_dimensions(self):
        models = ((250, 122, 9, 2), (250, 132, 8, 1), (296, 128, 2, 2))
        for width, height, alignment, screen_type in models:
            source = self._clone_client()
            target = self._clone_client()
            self._remap_clone_source(source, 777, width, height, alignment, screen_type)

            with self.subTest(dimensions=(width, height)):
                result = self.service.clone_vendor_template(source, target, {
                    "source_controller_id": "north", "target_controller_id": "south",
                    "source_template_id": 777,
                    "target_name": f"Supported {width}x{height}",
                }, source_controller_id="north", target_controller_id="south")

            self.assertEqual(result["id"], "200")
            self.assertIn(("create", alignment), target.calls)

    def test_cross_controller_clone_rejects_unsupported_dimensions_before_target_mutation(self):
        source = self._clone_client()
        target = self._clone_client()
        self._remap_clone_source(source, 777, 400, 300, 4, 4)

        with self.assertRaisesRegex(ValidationError, "dimensions"):
            self.service.clone_vendor_template(source, target, {
                "source_controller_id": "north", "target_controller_id": "south",
                "source_template_id": 777, "target_name": "Unsupported",
            }, source_controller_id="north", target_controller_id="south")

        self.assertFalse(any(call[0] in {"create", "field", "rename", "save", "delete"}
                             for call in target.calls))

    def test_cross_controller_clone_rejects_inconsistent_source_dimensions_before_create(self):
        source = self._clone_client()
        target = self._clone_client()
        original_data = source.get_style_data

        def inconsistent_data(style_id):
            result = original_data(style_id)
            if style_id == 145:
                result["height"] = 132
            return result

        source.get_style_data = inconsistent_data
        with self.assertRaisesRegex(IntegrationError, "dimensions"):
            self.service.clone_vendor_template(source, target, {
                "source_controller_id": "north", "target_controller_id": "south",
                "source_template_id": 145, "target_name": "Inconsistent source",
            }, source_controller_id="north", target_controller_id="south")

        self.assertFalse(any(call[0] == "create" for call in target.calls))

    def test_cross_controller_source_failure_never_mutates_target(self):
        source = self._clone_client()
        target = self._clone_client()
        source.get_style_detail = Mock(side_effect=RuntimeError("source failed"))

        with self.assertRaises(IntegrationError):
            self.service.clone_vendor_template(source, target, {
                "source_controller_id": "north", "target_controller_id": "south",
                "source_template_id": 145, "target_name": "Never created",
            }, source_controller_id="north", target_controller_id="south")

        self.assertFalse(any(call[0] in {"create", "field", "rename", "save", "delete"}
                             for call in target.calls))

    def test_cross_controller_ambiguous_create_reads_back_once_without_rollback(self):
        source = self._clone_client()
        target = self._clone_client()

        def ambiguous_create(style_align):
            target.calls.append(("create", style_align))
            target.created = True
            raise RuntimeError("response lost")

        target.create_style = ambiguous_create
        with self.assertRaisesRegex(IntegrationError, "create outcome"):
            self.service.clone_vendor_template(source, target, {
                "source_controller_id": "north", "target_controller_id": "south",
                "source_template_id": 145, "target_name": "Ambiguous",
            }, source_controller_id="north", target_controller_id="south")

        self.assertEqual(sum(call[0] == "create" for call in target.calls), 1)
        self.assertEqual(sum(call[0] == "catalog" for call in target.calls), 2)
        self.assertFalse(any(call[0] == "delete" for call in target.calls))

    def test_cross_controller_partial_failure_rolls_back_only_response_owned_target(self):
        source = self._clone_client()
        target = self._clone_client()
        target.save_style_layout = Mock(side_effect=RuntimeError("save failed"))

        with self.assertRaises(IntegrationError):
            self.service.clone_vendor_template(source, target, {
                "source_controller_id": "north", "target_controller_id": "south",
                "source_template_id": 145, "target_name": "Owned target",
            }, source_controller_id="north", target_controller_id="south")

        self.assertIn(("delete", 200), target.calls)
        self.assertFalse(any(call[0] == "delete" for call in source.calls))
        self.assertNotIn(("delete", 145), target.calls)

    def test_cross_controller_source_hash_change_fails_and_rolls_back_owned_target(self):
        source = self._clone_client()
        target = self._clone_client()
        original_layout = source.get_style_layout
        reads = 0

        def changed_layout(style_id):
            nonlocal reads
            result = original_layout(style_id)
            if style_id == 145:
                reads += 1
                if reads > 1:
                    result[0]["text"] = "source changed"
            return result

        source.get_style_layout = changed_layout
        with self.assertRaisesRegex(IntegrationError, "Source vendor template changed"):
            self.service.clone_vendor_template(source, target, {
                "source_controller_id": "north", "target_controller_id": "south",
                "source_template_id": 145, "target_name": "Source hash guard",
            }, source_controller_id="north", target_controller_id="south")

        self.assertEqual(reads, 2)
        self.assertIn(("delete", 200), target.calls)

    def test_clone_audit_identity_is_controller_distinguishable(self):
        client = self._clone_client()
        self.service.clone_vendor_template(client, {
            "source_id": 145, "target_name": "S21BasePriceTag_V1_BOLD",
        }, controller_id="north")

        event = self.service.list_audit(action="vendor.template.cloned")[0]
        self.assertEqual(event["entity_id"], "north:200")
        self.assertEqual(event["details"]["controller_id"], "north")
        self.assertEqual(event["details"]["vendor_template_id"], "200")

    def test_clone_populates_an_empty_server_created_template(self):
        client = self._clone_client()
        client.target_layout = []
        result = self.service.clone_vendor_template(client, {
            "source_id": 145, "target_name": "S21BasePriceTag_V1_BOLD",
        })
        self.assertEqual(result["id"], "200")
        self.assertEqual([call[-1] for call in client.calls if call[0] == "field"],
                         ["name", "price", "logo"])
        saved = next(call[2] for call in client.calls if call[0] == "save")
        self.assertEqual([item["mpname"] for item in saved], ["name", "price", "logo"])

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

    def test_legacy_clone_rejects_invalid_source_id_with_legacy_error_contract(self):
        for source_id in ([], {}, True, 145.0, 999):
            client = self._clone_client()
            with self.subTest(source_id=source_id):
                with self.assertRaises(ValidationError) as caught:
                    self.service.clone_vendor_template(client, {
                        "source_id": source_id, "target_name": "Invalid legacy source",
                    })
                self.assertEqual(caught.exception.message, "Unsupported source_id")
                self.assertEqual(caught.exception.details, {"field": "source_id"})
                self.assertFalse(any(call[0] == "catalog" for call in client.calls))

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

    def test_clone_accepts_vendor_numeric_bold_and_reordered_editor_readback(self):
        client = self._clone_client()
        original_layout = client.get_style_layout

        def normalized_layout(style_id):
            result = original_layout(style_id)
            if style_id == 200 and any(call[0] == "save" for call in client.calls):
                result.reverse()
                for component in result:
                    style = component.get("style", {})
                    if style.get("font-weight") == "700":
                        style["font-weight"] = 700
            return result

        client.get_style_layout = normalized_layout
        result = self.service.clone_vendor_template(client, {
            "source_id": 145, "target_name": "S21BasePriceTag_V1_BOLD",
        })
        self.assertEqual(result["id"], "200")

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
        with self.assertRaisesRegex(IntegrationError, "could not be verified"):
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

    def test_clone_rejects_target_mappingtype_changed_after_component_creation(self):
        source = self._clone_client()
        target = self._clone_client()
        original_detail = target.get_style_detail

        def changed_mappingtype(style_id):
            result = original_detail(style_id)
            if style_id == 200:
                result["mappingtype"] = 291
            return result

        target.get_style_detail = changed_mappingtype
        with self.assertRaisesRegex(IntegrationError, "mappingtype"):
            self.service.clone_vendor_template(source, target, {
                "source_controller_id": "north", "target_controller_id": "south",
                "source_template_id": 145, "target_name": "Mapping guard",
            }, source_controller_id="north", target_controller_id="south")
        self.assertIn(("delete", 200), target.calls)

    def test_clone_maps_preflight_vendor_failure_to_integration_error(self):
        client = self._clone_client()
        client.get_style_catalog = Mock(side_effect=RuntimeError("vendor unavailable"))
        with self.assertRaises(IntegrationError):
            self.service.clone_vendor_template(client, {
                "source_id": 145, "target_name": "S21BasePriceTag_V1_BOLD",
            })


if __name__ == "__main__":
    unittest.main()
