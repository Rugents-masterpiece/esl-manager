import sqlite3
import tempfile
import threading
import time
import unittest
from contextlib import closing
from pathlib import Path
from unittest.mock import patch

from esl_web.storage import SCHEMA, Storage


class StorageTests(unittest.TestCase):
    @staticmethod
    def _create_populated_v1(database: Path) -> None:
        with closing(sqlite3.connect(database)) as connection:
            connection.executescript(SCHEMA)
            connection.execute("PRAGMA user_version = 1")
            connection.execute(
                "INSERT INTO routers VALUES (?, ?, ?, ?, ?)",
                ("north:7", "Legacy router", "192.0.2.7", "online", "2026-01-01T00:00:00Z"),
            )
            connection.execute(
                "INSERT INTO templates VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                ("north:8", "Legacy template", 250, 122, 0, None, None, None,
                 None, "[]", None, None),
            )
            connection.execute(
                "INSERT INTO products VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                ("product-1", "SKU-1", None, "Product", 1.0, "EUR", "north:8",
                 "2026-01-01T00:00:00Z", "2026-01-01T00:00:00Z"),
            )
            tags = [
                ("tag-zero-a", "00:00:00:00:00:01", 0),
                ("tag-zero-b", "00:00:00:00:00:02", 0),
                ("tag-absent", "00:00:00:00:00:03", None),
                ("tag-positive", "00:00:00:00:00:04", 44),
                ("tag-unique", "00:00:00:00:00:05", 45),
                ("tag-dup-a", "00:00:00:00:00:06", 7),
                ("tag-dup-b", "00:00:00:00:00:07", 7),
            ]
            connection.executemany(
                "INSERT INTO tags(id, mac, label, width, height, battery, rssi, status, "
                "router_id, template_id, last_seen_at, vendor_tag_id) "
                "VALUES (?, ?, ?, 250, 122, 80, -50, 'ready', 'north:7', 'north:8', ?, ?)",
                [(tag_id, mac, tag_id, "2026-01-01T00:00:00Z", vendor_id)
                 for tag_id, mac, vendor_id in tags],
            )
            connection.execute(
                "INSERT INTO product_tags VALUES (?, ?, ?)",
                ("product-1", "tag-zero-a", "2026-01-01T00:00:00Z"),
            )
            connection.execute(
                "INSERT INTO jobs VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                ("job-1", "queued", "2026-01-01T00:00:00Z", None, None, 1, 0, 0),
            )
            connection.execute(
                "INSERT INTO job_items VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                ("item-1", "job-1", "product-1", "tag-zero-b", "queued", 0, None,
                 "2026-01-01T00:00:00Z"),
            )
            connection.execute(
                "INSERT INTO vendor_photos VALUES (?, ?, ?, ?, ?)",
                ("photo-1", "Photo", 10, 10, "2026-01-01T00:00:00Z"),
            )
            connection.commit()

    def test_populated_v1_migration_preserves_references_and_canonical_tag_identity(self):
        with tempfile.TemporaryDirectory() as directory:
            database = Path(directory) / "populated-v1.db"
            self._create_populated_v1(database)
            storage = Storage(database)

            storage.initialize()

            with storage.connection() as connection:
                self.assertEqual(connection.execute("PRAGMA foreign_key_check").fetchall(), [])
                self.assertEqual(connection.execute(
                    "SELECT template_id FROM products WHERE id = 'product-1'"
                ).fetchone()[0], "north:8")
                self.assertEqual(connection.execute(
                    "SELECT tag_id FROM product_tags WHERE product_id = 'product-1'"
                ).fetchone()[0], "tag-zero-a")
                self.assertEqual(tuple(connection.execute(
                    "SELECT product_id, tag_id FROM job_items WHERE id = 'item-1'"
                ).fetchone()), ("product-1", "tag-zero-b"))
                identities = dict(connection.execute(
                    "SELECT id, vendor_id FROM tags ORDER BY id"
                ).fetchall())
                self.assertEqual(identities, {
                    "tag-absent": "id:7461672D616273656E74",
                    "tag-dup-a": "7:id:7461672D6475702D61",
                    "tag-dup-b": "7:id:7461672D6475702D62",
                    "tag-positive": "44", "tag-unique": "45",
                    "tag-zero-a": "id:7461672D7A65726F2D61",
                    "tag-zero-b": "id:7461672D7A65726F2D62",
                })
                connection.execute(
                    "INSERT INTO controllers(id, name, is_default) VALUES ('north', 'North', 0)"
                )
                storage.upsert_tag(connection, {
                    "id": "runtime-zero", "mac": "00:00:00:00:00:06", "label": None,
                    "width": 250, "height": 122, "battery": 80, "rssi": -50,
                    "status": "ready", "router_id": None, "template_id": None,
                    "last_seen_at": None, "vendor_tag_id": "0",
                }, controller_id="north")
                self.assertEqual(connection.execute(
                    "SELECT vendor_id FROM tags WHERE controller_id = 'north'"
                ).fetchone()[0], "runtime-zero")
                storage.upsert_router(connection, {
                    "id": "7", "name": "North router", "address": "192.0.2.8",
                    "status": "online", "last_seen_at": None,
                }, controller_id="north")
                rows = connection.execute(
                    "SELECT id, controller_id, vendor_id FROM routers ORDER BY controller_id"
                ).fetchall()
                self.assertEqual(len(rows), 2)
                self.assertEqual(tuple(rows[0]), ("north:7", "legacy", "north:7"))
                self.assertEqual(rows[1][1:], ("north", "7"))
                self.assertNotEqual(rows[1][0], "north:7")

    def test_migrated_equal_ids_are_reserved_independently_per_entity(self):
        with tempfile.TemporaryDirectory() as directory:
            database = Path(directory) / "equal-cross-entity-ids.db"
            with closing(sqlite3.connect(database)) as connection:
                connection.executescript(SCHEMA)
                connection.execute("PRAGMA user_version = 1")
                connection.execute(
                    "INSERT INTO routers VALUES (?, ?, ?, ?, ?)",
                    ("same", "Legacy router", "192.0.2.7", "online", None),
                )
                connection.execute(
                    "INSERT INTO templates VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                    ("same", "Legacy template", 250, 122, 0, None, None, None,
                     None, "[]", None, None),
                )
                connection.commit()

            storage = Storage(database)
            storage.initialize()
            with storage.connection() as connection:
                self.assertEqual(
                    storage.local_id(connection, "router", "legacy", "same"), "same"
                )
                self.assertEqual(
                    storage.local_id(connection, "template", "legacy", "same"), "same"
                )
                reservations = [tuple(row) for row in connection.execute(
                    "SELECT entity, controller_id, vendor_id, local_id FROM local_ids "
                    "WHERE local_id = 'same' ORDER BY entity"
                )]
                self.assertEqual(reservations, [
                    ("router", "legacy", "same", "same"),
                    ("template", "legacy", "same", "same"),
                ])

                connection.execute("DELETE FROM routers WHERE id = 'same'")
                connection.execute("DELETE FROM templates WHERE id = 'same'")
                storage.upsert_router(connection, {
                    "id": "same", "name": "Legacy router returned",
                    "address": "192.0.2.8", "status": "online", "last_seen_at": None,
                })
                storage.upsert_template(connection, {
                    "id": "same", "name": "Legacy template returned", "width": 250,
                    "height": 122, "mapping_type": 0,
                })
                self.assertEqual(connection.execute(
                    "SELECT id FROM routers WHERE vendor_id = 'same'"
                ).fetchone()[0], "same")
                self.assertEqual(connection.execute(
                    "SELECT id FROM templates WHERE vendor_id = 'same'"
                ).fetchone()[0], "same")

    def test_persisted_id_conflict_is_not_swallowed_without_matching_owner(self):
        with tempfile.TemporaryDirectory() as directory:
            storage = Storage(Path(directory) / "conflicting-reservation.db")
            storage.initialize()
            with storage.connection() as connection:
                connection.execute(
                    "INSERT INTO controllers(id, name, is_default) VALUES ('north', 'North', 0)"
                )
                connection.execute(
                    "INSERT INTO routers(id, controller_id, vendor_id, name, address, status) "
                    "VALUES ('occupied', 'north', 'expected-owner', 'North', "
                    "'192.0.2.7', 'online')"
                )
                connection.execute(
                    "INSERT INTO local_ids(entity, controller_id, vendor_id, local_id) "
                    "VALUES ('router', 'legacy', 'other-owner', 'occupied')"
                )

                with self.assertRaises(sqlite3.IntegrityError):
                    storage.local_id(
                        connection, "router", "north", "expected-owner"
                    )

    def test_runtime_duplicate_positive_tag_ids_are_stably_disambiguated(self):
        with tempfile.TemporaryDirectory() as directory:
            storage = Storage(Path(directory) / "duplicate-tags.db")
            storage.initialize()
            with storage.connection() as connection:
                connection.execute(
                    "INSERT INTO controllers(id, name, is_default) VALUES ('north', 'North', 0)"
                )
                base = {
                    "label": None, "width": 250, "height": 122, "battery": 80,
                    "rssi": -50, "status": "ready", "router_id": None,
                    "template_id": None, "last_seen_at": None, "vendor_tag_id": 7,
                }
                storage.upsert_tag(connection, {
                    **base, "id": "tag-a", "mac": "00:00:00:00:00:01",
                }, controller_id="north")
                storage.upsert_tag(connection, {
                    **base, "id": "tag-b", "mac": "00:00:00:00:00:02",
                }, controller_id="north")
                rows = [tuple(row) for row in connection.execute(
                    "SELECT mac, vendor_id FROM tags WHERE controller_id = 'north' ORDER BY mac"
                )]
                self.assertEqual(rows, [
                    ("00:00:00:00:00:01", "7:id:7461672D61"),
                    ("00:00:00:00:00:02", "7:id:7461672D62"),
                ])

    def test_local_id_reservations_survive_absence_across_scopes_within_each_entity(self):
        with tempfile.TemporaryDirectory() as directory:
            storage = Storage(Path(directory) / "reserved-ids.db")
            storage.initialize()
            with storage.connection() as connection:
                connection.execute(
                    "INSERT INTO controllers(id, name, is_default) VALUES ('north', 'North', 0)"
                )
                entities = ("router", "template", "tag", "photo")
                for entity in entities:
                    reserved = storage.local_id(
                        connection, entity, "north", f"vendor-{entity}"
                    )
                    claimed = storage.local_id(connection, entity, "legacy", reserved)
                    self.assertNotEqual(claimed, reserved)

                storage.replace_vendor_photos(connection, [{
                    "id": "reappearing", "name": "photo.png", "width": 10, "height": 20,
                }], "2026-01-01T00:00:00Z", controller_id="north")
                original = connection.execute(
                    "SELECT id FROM vendor_photos WHERE controller_id = 'north' "
                    "AND vendor_id = 'reappearing'"
                ).fetchone()[0]
                storage.replace_vendor_photos(
                    connection, [], "2026-01-01T00:01:00Z", controller_id="north"
                )
                self.assertNotEqual(
                    storage.local_id(connection, "photo", "legacy", original), original
                )
                storage.replace_vendor_photos(connection, [{
                    "id": "reappearing", "name": "photo.png", "width": 10, "height": 20,
                }], "2026-01-01T00:02:00Z", controller_id="north")
                self.assertEqual(connection.execute(
                    "SELECT id FROM vendor_photos WHERE controller_id = 'north' "
                    "AND vendor_id = 'reappearing'"
                ).fetchone()[0], original)

    def test_scoped_ids_cannot_collide_with_preserved_legacy_ids(self):
        with tempfile.TemporaryDirectory() as directory:
            database = Path(directory) / "collision.db"
            storage = Storage(database)
            storage.initialize()
            with storage.connection() as connection:
                connection.execute(
                    "INSERT INTO routers(id, controller_id, vendor_id, name, address, status) "
                    "VALUES ('north:7', 'legacy', 'legacy-router', 'Legacy', '192.0.2.7', 'online')"
                )
                connection.execute(
                    "INSERT INTO controllers(id, name, is_default) VALUES ('north', 'North', 0)"
                )
                storage.upsert_router(connection, {
                    "id": "7", "name": "North", "address": "192.0.2.8",
                    "status": "online", "last_seen_at": None,
                }, controller_id="north")
                rows = [tuple(row) for row in connection.execute(
                    "SELECT id, controller_id FROM routers ORDER BY controller_id"
                )]
                self.assertEqual(len(rows), 2)
                self.assertEqual(rows[0], ("north:7", "legacy"))
                self.assertNotEqual(rows[1][0], "north:7")

    def test_allocated_id_skips_an_adversarial_preserved_primary_key(self):
        with tempfile.TemporaryDirectory() as directory:
            database = Path(directory) / "adversarial-collision.db"
            storage = Storage(database)
            storage.initialize()
            with storage.connection() as connection:
                connection.execute(
                    "INSERT INTO routers(id, controller_id, vendor_id, name, address, status) "
                    "VALUES ('scoped-router-1', 'legacy', 'legacy-router', 'Legacy', "
                    "'192.0.2.7', 'online')"
                )
                connection.execute(
                    "INSERT INTO controllers(id, name, is_default) VALUES ('north', 'North', 0)"
                )
                storage.upsert_router(connection, {
                    "id": "7", "name": "North", "address": "192.0.2.8",
                    "status": "online", "last_seen_at": None,
                }, controller_id="north")
                allocated = connection.execute(
                    "SELECT id FROM routers WHERE controller_id = 'north'"
                ).fetchone()[0]
                self.assertEqual(allocated, "scoped-router-2")
                storage.upsert_router(connection, {
                    "id": "7", "name": "North updated", "address": "192.0.2.9",
                    "status": "online", "last_seen_at": None,
                }, controller_id="north")
                self.assertEqual(connection.execute(
                    "SELECT id FROM routers WHERE controller_id = 'north'"
                ).fetchone()[0], allocated)

    def test_legacy_runtime_id_allocates_when_raw_vendor_id_is_an_existing_scoped_pk(self):
        with tempfile.TemporaryDirectory() as directory:
            storage = Storage(Path(directory) / "legacy-runtime-collision.db")
            storage.initialize()
            with storage.connection() as connection:
                connection.execute(
                    "INSERT INTO controllers(id, name, is_default) VALUES ('north', 'North', 0)"
                )
                storage.upsert_router(connection, {
                    "id": "7", "name": "North", "address": "192.0.2.7",
                    "status": "online", "last_seen_at": None,
                }, controller_id="north")
                scoped_id = connection.execute(
                    "SELECT id FROM routers WHERE controller_id = 'north'"
                ).fetchone()[0]
                storage.upsert_router(connection, {
                    "id": scoped_id, "name": "Legacy", "address": "192.0.2.8",
                    "status": "online", "last_seen_at": None,
                })
                rows = connection.execute(
                    "SELECT id, controller_id, vendor_id FROM routers ORDER BY controller_id"
                ).fetchall()
                self.assertEqual(len(rows), 2)
                self.assertEqual(rows[0][1:], ("legacy", scoped_id))
                self.assertNotEqual(rows[0][0], scoped_id)

    def test_interrupted_migration_rolls_back_schema_and_version_then_recovers(self):
        with tempfile.TemporaryDirectory() as directory:
            database = Path(directory) / "interrupted.db"
            self._create_populated_v1(database)
            storage = Storage(database)
            original = Storage._migrate_controller_scope

            def interrupt(connection):
                original(connection)
                raise RuntimeError("simulated interruption before version update")

            with patch.object(Storage, "_migrate_controller_scope", side_effect=interrupt):
                with self.assertRaisesRegex(RuntimeError, "simulated interruption"):
                    storage.initialize()

            with closing(sqlite3.connect(database)) as connection:
                self.assertEqual(connection.execute("PRAGMA user_version").fetchone()[0], 1)
                self.assertEqual([row[1] for row in connection.execute(
                    "PRAGMA table_info(routers)"
                )], ["id", "name", "address", "status", "last_seen_at"])

            storage.initialize()
            with closing(sqlite3.connect(database)) as connection:
                self.assertEqual(connection.execute("PRAGMA user_version").fetchone()[0], 3)
                self.assertIn("controller_id", [row[1] for row in connection.execute(
                    "PRAGMA table_info(routers)"
                )])

    def test_concurrent_initializers_migrate_once_after_version_recheck_under_lock(self):
        with tempfile.TemporaryDirectory() as directory:
            database = Path(directory) / "concurrent.db"
            self._create_populated_v1(database)
            original = Storage._migrate_controller_scope
            entered = threading.Event()
            calls = 0
            calls_lock = threading.Lock()
            errors = []

            def delayed_migration(connection):
                nonlocal calls
                with calls_lock:
                    calls += 1
                    call_number = calls
                if call_number == 1:
                    entered.set()
                    time.sleep(0.2)
                original(connection)

            def initialize():
                try:
                    Storage(database).initialize()
                except Exception as error:  # captured for assertion in the main thread
                    errors.append(error)

            with patch.object(Storage, "_migrate_controller_scope",
                              side_effect=delayed_migration):
                first = threading.Thread(target=initialize)
                second = threading.Thread(target=initialize)
                first.start()
                self.assertTrue(entered.wait(timeout=2))
                second.start()
                first.join(timeout=5)
                second.join(timeout=5)

            self.assertFalse(first.is_alive())
            self.assertFalse(second.is_alive())
            self.assertEqual(errors, [])
            self.assertEqual(calls, 1)
            with closing(sqlite3.connect(database)) as connection:
                self.assertEqual(connection.execute("PRAGMA user_version").fetchone()[0], 3)

    def test_versioned_migration_preserves_rows_and_scopes_vendor_identities(self):
        with tempfile.TemporaryDirectory() as directory:
            database = Path(directory) / "migration.db"
            storage = Storage(database)
            storage.initialize()
            storage.seed_demo()
            before = storage.table_counts()
            storage.initialize()

            with storage.connection() as connection:
                self.assertEqual(connection.execute("PRAGMA user_version").fetchone()[0], 3)
                self.assertEqual(connection.execute("PRAGMA foreign_key_check").fetchall(), [])
                models = [tuple(row) for row in connection.execute(
                    "SELECT name, width, height, alignment_id, screen_type FROM device_models ORDER BY name"
                )]
                self.assertEqual(models, [
                    ("2.13EPD-BWR", 250, 122, 9, 2),
                    ("2.13TFT-BW", 250, 132, 8, 1),
                    ("2.9EPD-BWR", 296, 128, 2, 2),
                ])
                connection.executemany(
                    "INSERT INTO controllers(id, name, is_default) VALUES (?, ?, ?)",
                    [("north", "North", 0), ("south", "South", 0)],
                )
                router = {"id": "7", "name": "Shared", "address": "10.0.0.7",
                          "status": "online", "last_seen_at": None}
                template = {"id": "8", "name": "Shared style", "width": 250,
                            "height": 122, "mapping_type": 2}
                storage.upsert_router(connection, router, controller_id="north")
                storage.upsert_router(connection, {**router, "address": "10.0.1.7"},
                                      controller_id="south")
                storage.upsert_template(connection, template, controller_id="north")
                storage.upsert_template(connection, template, controller_id="south")
                self.assertEqual(connection.execute(
                    "SELECT COUNT(*) FROM routers WHERE vendor_id = '7'"
                ).fetchone()[0], 2)
                self.assertEqual(connection.execute(
                    "SELECT COUNT(*) FROM templates WHERE vendor_id = '8' AND name = 'Shared style'"
                ).fetchone()[0], 2)

            self.assertEqual(storage.table_counts()["products"], before["products"])
            self.assertEqual(storage.table_counts()["tags"], before["tags"])

    def test_v2_tag_configuration_migration_is_idempotent_and_preserves_inventory(self):
        with tempfile.TemporaryDirectory() as directory:
            database = Path(directory) / "v2-tags.db"
            with closing(sqlite3.connect(database)) as connection:
                connection.executescript(SCHEMA)
                Storage._ensure_columns(connection, "templates", {
                    "descriptor": "TEXT", "screen_type": "INTEGER",
                    "background_id": "INTEGER", "vendor_updated_at": "TEXT",
                    "style_fields": "TEXT NOT NULL DEFAULT '[]'", "rotate": "INTEGER",
                    "user_id": "INTEGER",
                })
                Storage._ensure_columns(connection, "tags", {
                    "show_style": "TEXT", "vendor_tag_id": "INTEGER",
                    "router_status": "INTEGER", "sub": "INTEGER",
                })
                Storage._migrate_controller_scope(connection)
                connection.execute("PRAGMA user_version = 2")
                connection.execute(
                    "INSERT INTO tags(id, controller_id, vendor_id, mac, width, height, "
                    "battery, rssi, status) VALUES "
                    "('kept', 'legacy', 'vendor-7', 'aa-bb-cc-dd-ee-ff', 296, 128, 80, -50, 'ready')"
                )
                connection.execute(
                    "INSERT INTO tags(id, controller_id, vendor_id, mac, width, height, "
                    "battery, rssi, status) VALUES "
                    "('numeric-mac', 'legacy', 'vendor-8', '000000000001', 296, 128, "
                    "80, -50, 'ready')"
                )
                connection.commit()

            storage = Storage(database)
            storage.initialize()
            storage.initialize()

            with storage.connection() as connection:
                self.assertEqual(connection.execute("PRAGMA user_version").fetchone()[0], 3)
                row = connection.execute(
                    "SELECT id, mac, device_model_id, inventory_source, configuration_source, "
                    "test_data FROM tags WHERE id = 'kept'"
                ).fetchone()
                self.assertEqual(tuple(row), (
                    "kept", "AA:BB:CC:DD:EE:FF", "2.9EPD-BWR", "vendor", "vendor", "{}",
                ))
                self.assertEqual(connection.execute(
                    "SELECT mac FROM tags WHERE id = 'numeric-mac'"
                ).fetchone()[0], "00:00:00:00:00:01")
                self.assertEqual(connection.execute("PRAGMA foreign_key_check").fetchall(), [])

    def test_v2_normalized_mac_collision_rolls_back_schema_and_version(self):
        with tempfile.TemporaryDirectory() as directory:
            database = Path(directory) / "v2-mac-collision.db"
            with closing(sqlite3.connect(database)) as connection:
                connection.executescript(SCHEMA)
                Storage._ensure_columns(connection, "templates", {
                    "descriptor": "TEXT", "screen_type": "INTEGER",
                    "background_id": "INTEGER", "vendor_updated_at": "TEXT",
                    "style_fields": "TEXT NOT NULL DEFAULT '[]'", "rotate": "INTEGER",
                    "user_id": "INTEGER",
                })
                Storage._ensure_columns(connection, "tags", {
                    "show_style": "TEXT", "vendor_tag_id": "INTEGER",
                    "router_status": "INTEGER", "sub": "INTEGER",
                })
                Storage._migrate_controller_scope(connection)
                connection.execute("PRAGMA user_version = 2")
                connection.executemany(
                    "INSERT INTO tags(id, controller_id, vendor_id, mac, width, height, "
                    "battery, rssi, status) VALUES (?, 'legacy', ?, ?, 296, 128, 80, -50, 'ready')",
                    [("one", "one", "aa-bb-cc-dd-ee-ff"),
                     ("two", "two", "AA:BB:CC:DD:EE:FF")],
                )
                connection.commit()

            with self.assertRaises(sqlite3.IntegrityError):
                Storage(database).initialize()

            with closing(sqlite3.connect(database)) as connection:
                self.assertEqual(connection.execute("PRAGMA user_version").fetchone()[0], 2)
                columns = {row[1] for row in connection.execute("PRAGMA table_info(tags)")}
                self.assertNotIn("inventory_source", columns)
                self.assertEqual(
                    [row[0] for row in connection.execute("SELECT mac FROM tags ORDER BY id")],
                    ["aa-bb-cc-dd-ee-ff", "AA:BB:CC:DD:EE:FF"],
                )

    def test_v2_migration_preserves_unsupported_dimensions_without_assigning_a_model(self):
        with tempfile.TemporaryDirectory() as directory:
            database = Path(directory) / "v2-unsupported.db"
            with closing(sqlite3.connect(database)) as connection:
                connection.executescript(SCHEMA)
                Storage._ensure_columns(connection, "templates", {
                    "descriptor": "TEXT", "screen_type": "INTEGER",
                    "background_id": "INTEGER", "vendor_updated_at": "TEXT",
                    "style_fields": "TEXT NOT NULL DEFAULT '[]'", "rotate": "INTEGER",
                    "user_id": "INTEGER",
                })
                Storage._ensure_columns(connection, "tags", {
                    "show_style": "TEXT", "vendor_tag_id": "INTEGER",
                    "router_status": "INTEGER", "sub": "INTEGER",
                })
                Storage._migrate_controller_scope(connection)
                connection.execute("PRAGMA user_version = 2")
                connection.execute(
                    "INSERT INTO tags(id, controller_id, vendor_id, mac, width, height, "
                    "battery, rssi, status) VALUES "
                    "('old', 'legacy', 'old', 'AA:BB:CC:DD:EE:77', 400, 300, 80, -50, 'ready')"
                )
                connection.commit()

            storage = Storage(database)
            storage.initialize()
            storage.initialize()
            with storage.connection() as connection:
                row = connection.execute(
                    "SELECT width, height, device_model_id, inventory_source FROM tags "
                    "WHERE id = 'old'"
                ).fetchone()
                self.assertEqual(tuple(row), (400, 300, None, "vendor"))
                self.assertEqual(connection.execute("PRAGMA user_version").fetchone()[0], 3)

    def test_vendor_upsert_assigns_supported_device_model_without_overwriting_local_state(self):
        with tempfile.TemporaryDirectory() as directory:
            storage = Storage(Path(directory) / "vendor-model.db")
            storage.initialize()
            with storage.connection() as connection:
                tag = {
                    "id": "vendor-tag", "mac": "aa-bb-cc-dd-ee-10", "label": "Vendor",
                    "width": 250, "height": 122, "battery": 80, "rssi": -50,
                    "status": "ready", "router_id": None, "template_id": None,
                    "last_seen_at": None, "vendor_tag_id": 10,
                }
                storage.upsert_tag(connection, tag)
                connection.execute(
                    "UPDATE tags SET configuration_source = 'local', test_data = ?, mac = ? "
                    "WHERE mac = ?", ('{\"price\":\"1.00\"}', "AA:BB:CC:DD:EE:11",
                                      "AA:BB:CC:DD:EE:10"),
                )
                storage.upsert_tag(connection, {**tag, "battery": 70, "rssi": -60})
                row = connection.execute(
                    "SELECT device_model_id, inventory_source, configuration_source, test_data, "
                    "battery, rssi FROM tags WHERE mac = ?", ("AA:BB:CC:DD:EE:11",)
                ).fetchone()
                self.assertEqual(tuple(row), (
                    "2.13EPD-BWR", "vendor", "local", '{"price":"1.00"}', 70, -60,
                ))

    def test_vendor_upsert_keeps_12_digit_mac_distinct_from_uint32_identity(self):
        with tempfile.TemporaryDirectory() as directory:
            storage = Storage(Path(directory) / "vendor-identities.db")
            storage.initialize()
            base = {
                "label": "Vendor", "width": 296, "height": 128, "battery": 80,
                "rssi": -50, "status": "ready", "router_id": None,
                "template_id": None, "last_seen_at": None,
            }
            with storage.connection() as connection:
                storage.upsert_tag(connection, {
                    **base, "id": "mac", "vendor_tag_id": 11, "mac": "000000000001",
                })
                storage.upsert_tag(connection, {
                    **base, "id": "uint32", "vendor_tag_id": 12, "mac": "1",
                })
                rows = [tuple(row) for row in connection.execute(
                    "SELECT id, mac FROM tags ORDER BY id"
                )]
                for malformed in (
                        "9" * 5000, "4294967296", "١", "abc", "-1", "1.2.3",
                        "1.2.3.256", "1.2.3.4.5", "00:00-00:00:00:01", ""):
                    with self.subTest(malformed=malformed), self.assertRaises(sqlite3.IntegrityError):
                        storage.upsert_tag(connection, {
                            **base, "id": "invalid", "vendor_tag_id": 13, "mac": malformed,
                        })
            self.assertEqual(rows, [
                ("mac", "00:00:00:00:00:01"), ("uint32", "0.0.0.1"),
            ])

    def test_schema_and_demo_seed_are_complete_and_idempotent(self):
        with tempfile.TemporaryDirectory() as directory:
            database = Path(directory) / "esl.db"
            storage = Storage(database)
            storage.initialize()
            storage.seed_demo()
            first = storage.table_counts()
            storage.seed_demo()
            second = storage.table_counts()

            self.assertEqual(first, second)
            self.assertGreaterEqual(first["products"], 2)
            self.assertGreaterEqual(first["tags"], 2)
            self.assertGreaterEqual(first["routers"], 1)
            self.assertGreaterEqual(first["templates"], 1)
            self.assertGreaterEqual(first["product_tags"], 1)
            self.assertGreaterEqual(first["jobs"], 1)
            self.assertGreaterEqual(first["job_items"], 1)
            self.assertGreaterEqual(first["alerts"], 1)
            self.assertGreaterEqual(first["audit_events"], 1)
            self.assertEqual(first["controllers"], 1)
            self.assertEqual(first["device_models"], 3)

            with closing(sqlite3.connect(database)) as connection:
                connection.execute("PRAGMA foreign_keys = ON")
                with self.assertRaises(sqlite3.IntegrityError):
                    connection.execute(
                        "INSERT INTO product_tags(product_id, tag_id, bound_at) "
                        "VALUES ('missing', 'missing', 'now')"
                    )


if __name__ == "__main__":
    unittest.main()
