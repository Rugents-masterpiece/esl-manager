"""Browser QA must not depend on one cached Chromium build number."""
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
import test_frontend


class BrowserSetupTests(unittest.TestCase):
    def test_configured_browser_path_takes_precedence(self):
        with tempfile.TemporaryDirectory() as temporary:
            binary = Path(temporary) / "chrome"
            binary.touch()
            with patch.dict("os.environ", {"ESL_CHROMIUM": str(binary)}):
                finder = getattr(test_frontend, "find_chromium", None)
                self.assertTrue(callable(finder), "browser selection must be configurable")
                self.assertEqual(finder(), binary)

    def test_installed_cache_browser_is_discovered_without_pinned_revision(self):
        with patch.dict("os.environ", {"ESL_CHROMIUM": ""}):
            finder = getattr(test_frontend, "find_chromium", None)
            self.assertTrue(callable(finder), "browser selection must discover cached Chromium")
            cached = list((Path.home() / ".cache/ms-playwright").glob("chromium-*/chrome-linux*/chrome"))
            if cached:
                self.assertIn(finder(), cached)
