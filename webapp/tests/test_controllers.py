import json
import os
import sqlite3
import tempfile
import threading
import unittest
from contextlib import closing
from pathlib import Path
from unittest.mock import Mock, patch
from urllib.error import HTTPError
from urllib.request import Request, urlopen

from esl_web.controllers import ControllerRegistry
from esl_web.server import create_server
from esl_web.vendor import VendorClient, VendorConfig
from run_live import load_settings


class ControllerRegistryTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.path = Path(self.temporary.name) / "credentials.json"

    def tearDown(self):
        self.temporary.cleanup()

    def write_settings(self, settings):
        self.path.write_text(json.dumps(settings), encoding="utf-8")
        os.chmod(self.path, 0o600)

    def test_new_settings_create_isolated_clients_and_safe_metadata(self):
        self.write_settings({
            "api_token": "A" * 64,
            "live_writes": False,
            "default_controller": "north",
            "controllers": [
                {"id": "north", "name": "North", "base_url": "http://127.0.0.1/north",
                 "username": "north-user", "password": "north-secret", "connect_timeout": 1,
                 "read_timeout": 2},
                {"id": "south", "name": "South", "base_url": "http://127.0.0.1/south",
                 "username": "south-user", "password": "south-secret", "connect_timeout": 3,
                 "read_timeout": 4},
            ],
        })
        settings = load_settings(self.path)
        registry = ControllerRegistry.from_settings(settings)

        north = registry.get("north")
        south = registry.get("south")
        self.assertIs(registry.get(), north)
        self.assertIsNot(north, south)
        self.assertEqual(north.config.username, "north-user")
        self.assertEqual(south.config.read_timeout, 4)
        metadata = registry.metadata()
        self.assertEqual([item["id"] for item in metadata], ["north", "south"])
        self.assertTrue(metadata[0]["default"])
        serialized = json.dumps(metadata)
        self.assertNotIn("north-secret", serialized)
        self.assertNotIn("north-user", serialized)

    def test_public_controller_api_exposes_only_safe_metadata(self):
        controllers = [
            {"id": "north", "name": "North", "base_url": "http://127.0.0.1/north",
             "username": "north-user", "password": "north-secret"},
            {"id": "south", "name": "South", "base_url": "http://127.0.0.1/south",
             "username": "south-user", "password": "south-secret"},
        ]
        registry = ControllerRegistry(controllers, "north")
        safe_metadata = registry.metadata()
        registry.metadata = lambda: [
            {**item, "future_private_field": "must-not-leak"} for item in safe_metadata
        ]
        server = create_server(
            "127.0.0.1", 0, database_path=Path(self.temporary.name) / "public.db",
            seed=False, controller_registry=registry,
        )
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            with urlopen(
                f"http://127.0.0.1:{server.server_port}/api/controllers", timeout=2
            ) as response:
                self.assertEqual(response.status, 200)
                payload = json.loads(response.read())
            self.assertEqual(payload["items"], [
                {"id": "north", "name": "North", "base_url": "http://127.0.0.1/north",
                 "default": True},
                {"id": "south", "name": "South", "base_url": "http://127.0.0.1/south",
                 "default": False},
                {"id": "legacy", "name": "Legacy controller", "base_url": None,
                 "default": False},
            ])
            for item in payload["items"]:
                self.assertEqual(set(item), {"id", "name", "base_url", "default"})
            serialized = json.dumps(payload)
            for secret in ("north-user", "north-secret", "south-user", "south-secret"):
                self.assertNotIn(secret, serialized)
        finally:
            server.shutdown()
            server.server_close()
            thread.join(timeout=2)

    def test_controller_entry_can_declare_the_single_explicit_default(self):
        self.write_settings({
            "api_token": "A" * 64, "live_writes": False,
            "controllers": [
                {"id": "north", "name": "North", "default": True,
                 "base_url": "http://127.0.0.1/north", "username": "user", "password": "secret"},
                {"id": "south", "name": "South",
                 "base_url": "http://127.0.0.1/south", "username": "user", "password": "secret"},
            ],
        })
        settings = load_settings(self.path)
        self.assertEqual(settings["default_controller"], "north")
        self.assertEqual(ControllerRegistry.from_settings(settings).default_id, "north")

    def test_create_server_supports_registry_and_legacy_vendor_client(self):
        controllers = [{"id": "one", "name": "One", "base_url": "http://127.0.0.1/one",
                        "username": "user", "password": "secret"}]
        registry = ControllerRegistry(controllers, "one")
        database = Path(self.temporary.name) / "registry.db"
        server = create_server(database_path=database, seed=False, controller_registry=registry)
        try:
            self.assertIs(server.controller_registry, registry)
            self.assertIs(server.vendor_client, registry.get())
        finally:
            server.server_close()

        legacy = VendorClient(VendorConfig("http://127.0.0.1/legacy"))
        server = create_server(database_path=database, seed=False, vendor_client=legacy)
        try:
            self.assertIs(server.vendor_client, legacy)
            self.assertIsNone(server.controller_registry)
        finally:
            server.server_close()

    def test_registry_metadata_and_default_vendor_reads_use_controller_scope(self):
        controllers = [
            {"id": "north", "name": "North", "base_url": "http://127.0.0.1/north",
             "username": "user", "password": "secret"},
            {"id": "south", "name": "South", "base_url": "http://127.0.0.1/south",
             "username": "user", "password": "secret"},
        ]
        registry = ControllerRegistry(controllers, "north")
        database = Path(self.temporary.name) / "scoped.db"
        server = create_server(
            "127.0.0.1", 0, database_path=database, seed=False,
            controller_registry=registry,
        )
        client = Mock()
        client.get_routers.return_value = []
        client.get_templates.return_value = []
        client.get_tags.return_value = []
        client.get_style_catalog.return_value = []
        client.get_extended_tags.return_value = []
        client.get_photos.return_value = [
            {"id": 7, "name": "north.png", "width": 10, "height": 20}
        ]
        server.vendor_client = client
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        base = f"http://127.0.0.1:{server.server_port}"
        try:
            request = Request(
                base + "/api/sync/read-only", data=b"{}", method="POST",
                headers={"Content-Type": "application/json"},
            )
            with urlopen(request, timeout=2) as response:
                self.assertEqual(response.status, 200)
            with urlopen(base + "/api/vendor/photos", timeout=2) as response:
                self.assertEqual(response.status, 200)
        finally:
            server.shutdown()
            server.server_close()
            thread.join(timeout=2)

        with closing(sqlite3.connect(database)) as connection:
            controllers_in_db = connection.execute(
                "SELECT id, name, is_default FROM controllers ORDER BY id"
            ).fetchall()
            self.assertEqual(controllers_in_db, [
                ("legacy", "Legacy controller", 0),
                ("north", "North", 1),
                ("south", "South", 0),
            ])
            self.assertEqual(connection.execute(
                "SELECT controller_id, vendor_id FROM vendor_photos"
            ).fetchall(), [("north", "7")])
            self.assertEqual(connection.execute(
                "SELECT COUNT(*) FROM vendor_photos WHERE controller_id = 'legacy'"
            ).fetchone()[0], 0)

    def test_constructor_rejects_duplicate_identity_and_missing_default(self):
        base = {"id": "north", "name": "North", "base_url": "http://127.0.0.1/api",
                "username": "user", "password": "secret"}
        invalid = [
            ([base, {**base, "name": "Other"}], "north"),
            ([base, {**base, "id": "south", "name": "NORTH"}], "north"),
            ([base, {**base, "id": "south", "name": "South",
                     "base_url": "http://127.0.0.1/api/"}], "north"),
            ([base], "missing"),
            ([{**base, "id": "legacy"}], "legacy"),
        ]
        for controllers, default_id in invalid:
            with self.subTest(controllers=controllers, default_id=default_id):
                with self.assertRaises(ValueError):
                    ControllerRegistry(controllers, default_id)

    def test_constructor_rejects_malformed_entries_and_defaults_with_controlled_errors(self):
        valid = {"id": "north", "name": "North", "base_url": "http://127.0.0.1/north",
                 "username": "user", "password": "secret"}
        cases = [
            (None, "north"), ([valid], None), ([valid], 7), ([valid], "bad id"),
            ([{}], "north"), ([{**valid, "base_url": None}], "north"),
            ([{**valid, "username": 1}], "north"),
            ([{**valid, "connect_timeout": "fast"}], "north"),
        ]
        for controllers, default_id in cases:
            with self.subTest(controllers=controllers, default_id=default_id):
                with self.assertRaises(ValueError) as caught:
                    ControllerRegistry(controllers, default_id)
                self.assertNotIsInstance(caught.exception, (KeyError, TypeError))

        with patch("esl_web.controllers.VendorClient") as client_type:
            with self.assertRaises(ValueError):
                ControllerRegistry([valid, {**valid, "id": "bad id"}], "north")
            client_type.assert_not_called()

    def test_explicit_non_default_controller_is_used_and_persistence_is_isolated(self):
        controllers = [
            {"id": "north", "name": "North", "base_url": "http://127.0.0.1/north",
             "username": "user", "password": "secret"},
            {"id": "south", "name": "South", "base_url": "http://127.0.0.1/south",
             "username": "user", "password": "secret"},
        ]
        registry = ControllerRegistry(controllers, "north")
        north = Mock()
        south = Mock()
        for client, photo_name in ((north, "north.png"), (south, "south.png")):
            client.get_photos.return_value = [
                {"id": 7, "name": photo_name, "width": 10, "height": 20}
            ]
        south.get_style_catalog.return_value = [
            {"id": 9, "name": "South style", "width": 10, "height": 20,
             "mappingtype": 0}
        ]
        setattr(registry, "_clients", {"north": north, "south": south})
        database = Path(self.temporary.name) / "selected.db"
        server = create_server("127.0.0.1", 0, database_path=database, seed=False,
                               controller_registry=registry)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        base = f"http://127.0.0.1:{server.server_port}"
        try:
            with urlopen(base + "/api/vendor/photos", timeout=2) as response:
                self.assertEqual(json.loads(response.read())["items"][0]["name"], "north.png")
            with urlopen(base + "/api/vendor/photos?controller_id=south", timeout=2) as response:
                south_payload = json.loads(response.read())
                self.assertEqual(south_payload["items"][0]["name"], "south.png")
                self.assertEqual(
                    south_payload["items"][0]["data_url"],
                    "/api/vendor/photos/south.png/data?controller_id=south",
                )
            with urlopen(base + "/api/vendor/templates?controller_id=south", timeout=2) as response:
                self.assertEqual(
                    json.loads(response.read())["items"][0]["preview_url"],
                    "/api/vendor/templates/9/preview?controller_id=south",
                )
        finally:
            server.shutdown()
            server.server_close()
            thread.join(timeout=2)
        north.get_photos.assert_called_once_with()
        south.get_photos.assert_called_once_with()
        south.get_style_catalog.assert_called_once_with()
        with closing(sqlite3.connect(database)) as connection:
            self.assertEqual(connection.execute(
                "SELECT controller_id, name FROM vendor_photos ORDER BY controller_id"
            ).fetchall(), [("north", "north.png"), ("south", "south.png")])

    def test_controller_selector_rejects_unknown_malformed_and_duplicate_values(self):
        controllers = [{"id": "north", "name": "North", "base_url": "http://127.0.0.1/north",
                        "username": "user", "password": "secret"}]
        server = create_server("127.0.0.1", 0,
                               database_path=Path(self.temporary.name) / "selectors.db",
                               seed=False, controller_registry=ControllerRegistry(controllers, "north"))
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        base = f"http://127.0.0.1:{server.server_port}/api/vendor/photos"
        try:
            for suffix in ("?controller_id=missing", "?controller_id=bad%20id",
                           "?controller_id=north&controller_id=north", "?other=north"):
                with self.subTest(suffix=suffix), self.assertRaises(HTTPError) as caught:
                    urlopen(base + suffix, timeout=2)
                self.assertEqual(caught.exception.code, 400)
                caught.exception.close()
        finally:
            server.shutdown()
            server.server_close()
            thread.join(timeout=2)

    def test_every_vendor_route_uses_the_explicit_controller_client(self):
        controllers = [
            {"id": key, "name": key.title(), "base_url": f"http://127.0.0.1/{key}",
             "username": "user", "password": "secret"}
            for key in ("north", "south")
        ]
        registry = ControllerRegistry(controllers, "north")
        north, south = Mock(), Mock()
        setattr(registry, "_clients", {"north": north, "south": south})
        service = Mock()
        service.sync_read_only.return_value = {}
        service.clone_vendor_template.return_value = {}
        service.dispatch_live.return_value = {}
        service.vendor_style_catalog.return_value = []
        service.vendor_style_detail.return_value = {}
        service.vendor_template_preview.return_value = (b"png", "image/png")
        service.vendor_photos.return_value = []
        service.vendor_photo_data.return_value = (b"png", "image/png")
        server = create_server("127.0.0.1", 0, service=service, controller_registry=registry)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        base = f"http://127.0.0.1:{server.server_port}"

        def post(path, body):
            request = Request(base + path, data=json.dumps(body).encode(), method="POST",
                              headers={"Content-Type": "application/json"})
            with urlopen(request, timeout=2) as response:
                response.read()

        try:
            post("/api/sync/read-only?controller_id=south", {})
            post("/api/vendor/templates/clone", {
                "source_controller_id": "north", "target_controller_id": "south",
                "source_template_id": 145, "target_name": "Cross clone",
            })
            with patch.dict(os.environ, {"ESL_LIVE_WRITES": "1"}):
                post("/api/dispatch/live?controller_id=south",
                     {"confirmation": "I CONFIRM LIVE ESL UPDATE"})
            for path in (
                "/api/vendor/templates?controller_id=south",
                "/api/vendor/templates/9?controller_id=south",
                "/api/vendor/templates/9/preview?controller_id=south",
                "/api/vendor/photos?controller_id=south",
                "/api/vendor/photos/photo.png/data?controller_id=south",
            ):
                with urlopen(base + path, timeout=2) as response:
                    response.read()
        finally:
            server.shutdown()
            server.server_close()
            thread.join(timeout=2)

        service.sync_read_only.assert_called_once_with(south, controller_id="south")
        service.clone_vendor_template.assert_called_once_with(
            north, south, {
                "source_controller_id": "north", "target_controller_id": "south",
                "source_template_id": 145, "target_name": "Cross clone",
            }, source_controller_id="north", target_controller_id="south",
        )
        service.dispatch_live.assert_called_once_with(
            south, {"confirmation": "I CONFIRM LIVE ESL UPDATE"}, controller_id="south"
        )
        service.vendor_style_catalog.assert_called_once_with(south, controller_id="south")
        service.vendor_style_detail.assert_called_once_with(south, 9, controller_id="south")
        service.vendor_template_preview.assert_called_once_with(south, 9)
        service.vendor_photos.assert_called_once_with(south, controller_id="south")
        service.vendor_photo_data.assert_called_once_with(south, "photo.png")
        self.assertEqual(north.method_calls, [])

    def test_clone_rejects_unknown_source_or_target_controller_before_service_call(self):
        controllers = [
            {"id": key, "name": key.title(), "base_url": f"http://127.0.0.1/{key}",
             "username": "user", "password": "secret"}
            for key in ("north", "south")
        ]
        registry = ControllerRegistry(controllers, "north")
        service = Mock()
        server = create_server(
            "127.0.0.1", 0, service=service, controller_registry=registry,
        )
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        base = f"http://127.0.0.1:{server.server_port}/api/vendor/templates/clone"
        try:
            for source_id, target_id in (("missing", "south"), ("north", "missing")):
                request = Request(
                    base, data=json.dumps({
                        "source_controller_id": source_id,
                        "target_controller_id": target_id,
                        "source_template_id": 145,
                        "target_name": "Unknown controller",
                    }).encode(), method="POST", headers={"Content-Type": "application/json"},
                )
                with self.subTest(source=source_id, target=target_id), self.assertRaises(HTTPError) as caught:
                    urlopen(request, timeout=2)
                self.assertEqual(caught.exception.code, 400)
                payload = json.loads(caught.exception.read())
                caught.exception.close()
                self.assertEqual(payload["error"]["message"], "Unknown controller_id")
            service.clone_vendor_template.assert_not_called()
        finally:
            server.shutdown()
            server.server_close()
            thread.join(timeout=2)

    def test_rejects_unsafe_duplicate_or_implicit_controller_identity(self):
        base = {"api_token": "A" * 64, "live_writes": False, "controllers": [
            {"id": "north", "name": "North", "base_url": "http://127.0.0.1",
             "username": "user", "password": "secret"},
        ]}
        cases = [
            base,
            {**base, "default_controller": "north", "controllers": [
                base["controllers"][0], {**base["controllers"][0], "name": "Other"}]},
            {**base, "default_controller": "north", "controllers": [
                base["controllers"][0], {**base["controllers"][0], "id": "south", "name": "North"}]},
            {**base, "default_controller": "north", "controllers": [
                base["controllers"][0], {**base["controllers"][0], "id": "south", "name": "South",
                                         "base_url": "http://127.0.0.1/"}]},
            {**base, "default_controller": "bad id"},
        ]
        for settings in cases:
            with self.subTest(settings=settings):
                self.write_settings(settings)
                with self.assertRaises(ValueError):
                    load_settings(self.path)


if __name__ == "__main__":
    unittest.main()
