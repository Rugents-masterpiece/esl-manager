import json
import tempfile
import threading
import unittest
from pathlib import Path
from unittest.mock import Mock
from urllib.error import HTTPError
from urllib.request import urlopen
from esl_web.server import create_server
from esl_web.vendor import VendorError

class TagDisplayApiTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.client=Mock()
        self.client.get_tag_display.return_value={'mac':'00:11:22:33:44:55','style_id':96,'physical_screen_verified':False,'update_progress':5}
        self.server=create_server('127.0.0.1',0,database_path=Path(self.tmp.name)/'test.db',vendor_client=self.client)
        self.thread=threading.Thread(target=self.server.serve_forever,daemon=True);self.thread.start()
        self.base=f'http://127.0.0.1:{self.server.server_port}'
    def tearDown(self):
        self.server.shutdown();self.server.server_close();self.thread.join(2);self.tmp.cleanup()
    def test_get_reads_stored_mac_and_does_not_mutate_inventory_or_audit(self):
        before=self.server.service.get_tag('tag-001')
        audit=self.server.service.list_audit()
        with urlopen(self.base+'/api/tags/tag-001/display') as r:
            result=json.load(r)
        self.assertFalse(result['physical_screen_verified'])
        self.assertEqual(result['preview_url'],'/api/vendor/templates/96/preview')
        self.client.get_tag_display.assert_called_once_with(before['mac'])
        self.assertEqual(self.server.service.get_tag('tag-001'),before)
        self.assertEqual(self.server.service.list_audit(),audit)
        self.client.update_screen.assert_not_called()
    def test_query_cannot_override_controller_or_mac(self):
        with self.assertRaises(HTTPError) as error:
            urlopen(self.base+'/api/tags/tag-001/display?controller_id=other')
        self.assertEqual(error.exception.code,400)
        error.exception.close()
        self.client.get_tag_display.assert_not_called()
    def test_vendor_failure_returns_sanitized_integration_error(self):
        self.client.get_tag_display.side_effect=VendorError('private upstream data')
        with self.assertRaises(HTTPError) as error:
            urlopen(self.base+'/api/tags/tag-001/display')
        self.assertEqual(error.exception.code,502)
        self.assertNotIn(b'private upstream data',error.exception.read());error.exception.close()
