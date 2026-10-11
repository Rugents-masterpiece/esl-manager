"""Existing display families are immutable, including locally staged tags.

All storage is disposable; no vendor clients or live services are used.
"""
import tempfile
import unittest
from pathlib import Path

from esl_web.service import Service, ValidationError
from esl_web.storage import Storage


FAMILIES = (
    ("2.13EPD-BWR", 250, 122, 2),
    ("2.13TFT-BW", 250, 132, 1),
    ("2.9EPD-BWR", 296, 128, 2),
)


class TagDimensionsImmutableTests(unittest.TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.storage = Storage(Path(directory.name) / "test.sqlite3")
        self.storage.initialize()
        self.storage.seed_demo()
        self.service = Service(self.storage)
        with self.storage.connection() as connection:
            for index, (_, width, height, screen) in enumerate(FAMILIES):
                for suffix in ("original", "replacement"):
                    connection.execute(
                        "INSERT INTO templates(id, controller_id, vendor_id, name, "
                        "width, height, screen_type) VALUES (?, 'legacy', ?, ?, ?, ?, ?)",
                        (f"family-{index}-{suffix}", f"family-{index}-{suffix}",
                         f"Family {index} {suffix}", width, height, screen),
                    )
            connection.execute(
                "INSERT INTO routers(id, controller_id, vendor_id, name, address, status) "
                "VALUES ('replacement-router', 'legacy', 'replacement', 'Other router', "
                "'127.0.0.2', 'online')"
            )
        self.tags = {}
        for source in ("local", "vendor"):
            for index, (model, width, height, _) in enumerate(FAMILIES):
                payload = {
                    "id": f"immutable-{source}-{index}", "controller_id": "legacy",
                    "mac": f"AA:BB:CC:DD:{'01' if source == 'local' else '02'}:{index:02X}",
                    "label": "Original label", "device_model_id": model,
                    "width": width, "height": height, "router_id": "router-main",
                    "template_id": f"family-{index}-original", "test_data": {"name": "Original"},
                }
                tag = self.service.create_staged_tag(payload)
                if source == "vendor":
                    # Represent imported inventory without invoking a vendor adapter.
                    with self.storage.connection() as connection:
                        connection.execute(
                            "UPDATE tags SET inventory_source = 'vendor', "
                            "configuration_source = 'vendor', vendor_id = ? WHERE id = ?",
                            (f"vendor-{index}", tag["id"]),
                        )
                self.tags[source, index] = {key: value for key, value in payload.items() if key != "id"}

    def snapshot(self):
        # Compare every persisted table, including audit and SQLite sequences.
        with self.storage.connection() as connection:
            return tuple(connection.iterdump())

    def edited_payload(self, source, index):
        return {
            **self.tags[source, index],
            "mac": f"CCDD-EEFF-{'01' if source == 'local' else '02'}{index:02X}",
            "label": "Edited label",
            "router_id": "replacement-router", "template_id": f"family-{index}-replacement",
            "test_data": {"name": "Káva", "price": 3.49, "extra": [1, "metadata"]},
        }

    def test_complete_matching_family_swap_is_rejected_atomically(self):
        for source in ("local", "vendor"):
            for index in range(len(FAMILIES)):
                for target, (model, width, height, _) in enumerate(FAMILIES):
                    if target == index:
                        continue
                    with self.subTest(source=source, original=index, target=target):
                        payload = {
                            **self.edited_payload(source, index), "device_model_id": model,
                            "width": width, "height": height,
                            "template_id": f"family-{target}-replacement",
                        }
                        before = self.snapshot()
                        with self.assertRaises(ValidationError):
                            self.service.update_tag_configuration(f"immutable-{source}-{index}", payload)
                        self.assertEqual(self.snapshot(), before)

    def test_individual_family_fields_cannot_change(self):
        for (source, index), original in self.tags.items():
            changes = {
                "device_model_id": FAMILIES[(index + 1) % len(FAMILIES)][0],
                "width": original["width"] + 1, "height": original["height"] + 1,
            }
            for field, value in changes.items():
                with self.subTest(source=source, family=index, field=field):
                    before = self.snapshot()
                    with self.assertRaises(ValidationError) as caught:
                        self.service.update_tag_configuration(
                            f"immutable-{source}-{index}",
                            {**self.edited_payload(source, index), field: value},
                        )
                    self.assertEqual(caught.exception.details, {"fields": [field]})
                    self.assertEqual(self.snapshot(), before)

    def test_same_family_still_updates_metadata_router_template_and_content(self):
        for source, index in self.tags:
            with self.subTest(source=source, family=index):
                tag_id = f"immutable-{source}-{index}"
                before = self.service.get_tag(tag_id)
                audit_before = self.service.list_audit(action="tag.configuration.updated")
                payload = self.edited_payload(source, index)
                updated = self.service.update_tag_configuration(tag_id, payload)
                self.assertEqual(updated, self.service.get_tag(tag_id))
                for field in ("label", "router_id", "template_id", "test_data"):
                    self.assertEqual(updated[field], payload[field])
                    self.assertNotEqual(updated[field], before[field])
                self.assertEqual(updated["mac"], self.service._normalized_mac(payload["mac"]))
                for field in ("device_model_id", "width", "height", "controller_id", "vendor_id",
                              "inventory_source", "battery", "rssi", "status"):
                    self.assertEqual(updated[field], before[field])
                self.assertEqual(updated["configuration_source"], "local")
                self.assertEqual(updated["staged"], source == "local")
                self.assertEqual(updated["template_compatibility"], "compatible")
                audit = self.service.list_audit(action="tag.configuration.updated")
                self.assertEqual(len(audit), len(audit_before) + 1)
                self.assertEqual(audit[0]["entity_id"], tag_id)
                self.assertEqual(audit[0]["details"], {
                    "controller_id": "legacy", "mac": updated["mac"], "inventory_source": source,
                })

    def test_same_family_keeps_exact_template_screen_type_guard(self):
        for source, index in self.tags:
            for screen in (None, 0, 1 if FAMILIES[index][3] == 2 else 2):
                with self.subTest(source=source, family=index, screen=screen):
                    payload = self.edited_payload(source, index)
                    with self.storage.connection() as connection:
                        connection.execute("UPDATE templates SET screen_type = ? WHERE id = ?",
                                           (screen, payload["template_id"]))
                    before = self.snapshot()
                    with self.assertRaises(ValidationError) as caught:
                        self.service.update_tag_configuration(f"immutable-{source}-{index}", payload)
                    self.assertEqual(caught.exception.details, {"field": "template_id"})
                    self.assertEqual(self.snapshot(), before)

    def test_same_family_keeps_controller_and_template_ownership_guards(self):
        with self.storage.connection() as connection:
            connection.execute("INSERT INTO controllers(id, name, is_default) VALUES ('other', 'Other', 0)")
            connection.execute(
                "INSERT INTO routers(id, controller_id, vendor_id, name, address, status) "
                "VALUES ('other-router', 'other', '1', 'Other', '127.0.0.3', 'online')"
            )
            for index, (_, width, height, screen) in enumerate(FAMILIES):
                connection.execute(
                    "INSERT INTO templates(id, controller_id, vendor_id, name, width, height, screen_type) "
                    "VALUES (?, 'other', ?, ?, ?, ?, ?)",
                    (f"other-{index}", str(index), f"Other {index}", width, height, screen),
                )
        for source, index in self.tags:
            for changes, error_field in (
                ({"template_id": f"other-{index}"}, "template_id"),
                ({"controller_id": "other", "router_id": "other-router",
                  "template_id": f"other-{index}"}, "controller_id"),
            ):
                with self.subTest(source=source, family=index, changes=changes):
                    before = self.snapshot()
                    with self.assertRaises(ValidationError) as caught:
                        self.service.update_tag_configuration(
                            f"immutable-{source}-{index}", {**self.edited_payload(source, index), **changes},
                        )
                    self.assertEqual(caught.exception.details, {"field": error_field})
                    self.assertEqual(self.snapshot(), before)

    def test_unsupported_historical_tags_cannot_be_repaired_by_configuration(self):
        for source, index in self.tags:
            for changes in ({"device_model_id": None}, {"width": 400, "height": 300}):
                with self.subTest(source=source, family=index, changes=changes):
                    tag_id = f"immutable-{source}-{index}"
                    original = self.tags[source, index]
                    with self.storage.connection() as connection:
                        connection.execute(
                            "UPDATE tags SET device_model_id = ?, width = ?, height = ? WHERE id = ?",
                            (changes.get("device_model_id", original["device_model_id"]),
                             changes.get("width", original["width"]),
                             changes.get("height", original["height"]), tag_id),
                        )
                    before = self.snapshot()
                    with self.assertRaises(ValidationError) as caught:
                        self.service.update_tag_configuration(tag_id, self.edited_payload(source, index))
                    self.assertIn("Unsupported historical", caught.exception.message)
                    self.assertEqual(self.snapshot(), before)


if __name__ == "__main__":
    unittest.main()
