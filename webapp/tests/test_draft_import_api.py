"""Real HTTP contracts: source reads do not initialize drafts or refresh inventory."""
import json
import sqlite3
import tempfile
import threading
import unittest
from pathlib import Path
from unittest.mock import call
from urllib.error import HTTPError
from urllib.request import urlopen

from esl_web.controllers import ControllerRegistry
from esl_web.server import create_server
from test_draft_import import importer


class DraftImportApiTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.db = Path(self.temp.name) / 'sources.db'
        self.registry = ControllerRegistry([
            {'id': cid, 'name': cid, 'base_url': 'http://127.0.0.1/' + cid,
             'username': 'fixture', 'password': 'fixture'} for cid in ('north', 'south')], 'north')
        _, self.north = importer()
        _, self.south = importer()
        self.south.get_style_catalog.return_value[0]['name'] = 'South source'
        self.registry._clients = {'north': self.north, 'south': self.south}
        self.server = create_server('127.0.0.1', 0, database_path=self.db, seed=False,
                                    controller_registry=self.registry, api_token='A' * 64)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.base = f'http://127.0.0.1:{self.server.server_port}'

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=2)
        self.temp.cleanup()

    def get(self, path):
        try:
            response = urlopen(self.base + path, timeout=3)
        except HTTPError as error:
            response = error
        with response:
            return response.status, json.loads(response.read())

    def test_catalog_and_conversion_are_unauthenticated_controller_scoped_and_unsaved(self):
        status, catalog = self.get('/api/template-draft-sources')
        self.assertEqual(status, 200)
        self.assertEqual(catalog['controller_id'], 'north')
        status, result = self.get('/api/template-draft-sources/145?controller_id=south')
        self.assertEqual(status, 200)
        self.assertEqual(result['source'], {'id': '145', 'name': 'South source', 'controller_id': 'south'})
        self.assertEqual(result['document']['schema_version'], 2)
        self.assertIsNone(self.server._drafts)
        self.assertEqual(self.north.mock_calls, [call.get_style_catalog()])
        self.assertEqual(self.south.mock_calls, [call.get_style_catalog(), call.get_style_detail(145),
                                                call.get_style_layout(145)])
        with sqlite3.connect(self.db) as connection:
            self.assertEqual(connection.execute('SELECT COUNT(*) FROM templates').fetchone()[0], 0)
            self.assertEqual(connection.execute('SELECT COUNT(*) FROM audit_events').fetchone()[0], 0)
            self.assertEqual(connection.execute("SELECT COUNT(*) FROM sqlite_master WHERE name='template_drafts'").fetchone()[0], 0)

    def test_query_ids_and_nested_paths_are_strict_without_vendor_calls(self):
        for path, expected in [
            ('/api/template-draft-sources?controller_id=unknown', 400),
            ('/api/template-draft-sources?controller_id=', 400),
            ('/api/template-draft-sources?controller_id=north&controller_id=south', 400),
            ('/api/template-draft-sources?other=1', 400),
            ('/api/template-draft-sources/0145', 400),
            ('/api/template-draft-sources/145%2Fx', 404),
            ('/api/template-draft-sources/145/x', 404),
        ]:
            with self.subTest(path=path):
                self.assertEqual(self.get(path)[0], expected)
        self.assertEqual(self.north.mock_calls, [])
        self.assertEqual(self.south.mock_calls, [])

    def test_vendor_failures_do_not_disclose_transport_secrets(self):
        self.north.get_style_catalog.side_effect = RuntimeError('password=secret; JSESSIONID=private')
        status, result = self.get('/api/template-draft-sources')
        self.assertEqual(status, 502)
        self.assertNotIn('secret', json.dumps(result))
        self.assertNotIn('private', json.dumps(result))

    def test_legacy_controller_cannot_import(self):
        self.server.controller_registry = None
        self.server.controller_id = 'legacy'
        self.assertEqual(self.get('/api/template-draft-sources')[0], 400)
        self.assertEqual(self.north.mock_calls, [])


if __name__ == '__main__':
    unittest.main()
