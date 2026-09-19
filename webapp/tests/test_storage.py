import sqlite3
import tempfile
import unittest
from pathlib import Path

from esl_web.storage import Storage


class StorageTests(unittest.TestCase):
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

            with sqlite3.connect(database) as connection:
                connection.execute("PRAGMA foreign_keys = ON")
                with self.assertRaises(sqlite3.IntegrityError):
                    connection.execute(
                        "INSERT INTO product_tags(product_id, tag_id, bound_at) "
                        "VALUES ('missing', 'missing', 'now')"
                    )


if __name__ == "__main__":
    unittest.main()
