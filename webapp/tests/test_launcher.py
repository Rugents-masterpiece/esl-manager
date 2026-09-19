import json
import os
import tempfile
import unittest
from pathlib import Path

from run_live import load_settings


class LiveLauncherTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.path = Path(self.temporary.name) / "credentials.json"

    def tearDown(self):
        self.temporary.cleanup()

    def write_settings(self, live_writes):
        self.path.write_text(json.dumps({
            "base_url": "http://127.0.0.1/esls_new",
            "username": "operator",
            "password": "secret",
            "live_writes": live_writes,
        }))
        os.chmod(self.path, 0o600)

    def test_accepts_explicit_boolean_write_modes(self):
        for enabled in (False, True):
            self.write_settings(enabled)
            self.assertIs(load_settings(self.path)["live_writes"], enabled)

    def test_rejects_broad_permissions_symlinks_and_non_boolean_write_mode(self):
        self.write_settings(False)
        os.chmod(self.path, 0o640)
        with self.assertRaises(PermissionError):
            load_settings(self.path)
        os.chmod(self.path, 0o600)
        link = Path(self.temporary.name) / "link.json"
        link.symlink_to(self.path)
        with self.assertRaises(PermissionError):
            load_settings(link)
        self.write_settings("false")
        with self.assertRaises(ValueError):
            load_settings(self.path)
        self.write_settings(False)
        settings = json.loads(self.path.read_text())
        settings["connect_timeout"] = True
        self.path.write_text(json.dumps(settings))
        with self.assertRaises(ValueError):
            load_settings(self.path)


if __name__ == "__main__":
    unittest.main()
