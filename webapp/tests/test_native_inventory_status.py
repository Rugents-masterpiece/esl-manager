import tempfile
import unittest
from pathlib import Path
from esl_web.service import Service
from esl_web.storage import Storage

class NativeInventoryStatusTests(unittest.TestCase):
    def test_native_status_wins_over_unchanged_mms_progress(self):
        with tempfile.TemporaryDirectory() as directory:
            storage=Storage(Path(directory)/'test.db');storage.initialize();storage.seed_demo();service=Service(storage)
            for native, expected in ((2,'updating'),(3,'failed'),(4,'success')):
                with self.subTest(native=native), storage.connection() as connection:
                    service.upsert_vendor_tag(connection,{'mac':'92.81.10.37','power':90,'width':296,'height':128,'updateProgress':5,'status':1,'_native_update_progress':native},set(),set(),{})
                    self.assertEqual(connection.execute("SELECT status FROM tags WHERE mac='92.81.10.37'").fetchone()[0],expected)

    def test_legacy_only_status_stays_supported(self):
        with tempfile.TemporaryDirectory() as directory:
            storage=Storage(Path(directory)/'test.db');storage.initialize();storage.seed_demo();service=Service(storage)
            with storage.connection() as connection:
                service.upsert_vendor_tag(connection,{'mac':'92.81.10.37','power':90,'updateProgress':3},set(),set(),{})
                self.assertEqual(connection.execute("SELECT status FROM tags WHERE mac='92.81.10.37'").fetchone()[0],'failed')
