"""Real browser acceptance with deterministic read-only vendor fixture."""
import struct
import unittest
import zlib
from pathlib import Path
from unittest.mock import Mock

import test_frontend as frontend


@unittest.skipUnless(frontend.CHROMIUM.exists(), 'local headless Chromium is unavailable')
class DesignerMediaBrowserTests(unittest.TestCase):
    def test_media_upload_codes_persistence_source_copy_and_offline(self):
        artifact = frontend.WEBAPP / 'test-artifacts/designer-media-browser'
        artifact.mkdir(parents=True, exist_ok=True)
        def chunk(kind, value):
            return struct.pack('>I', len(value)) + kind + value + struct.pack('>I', zlib.crc32(kind + value))
        row = bytes([255, 255, 255, 0, 0, 0, 255, 0, 0, 0, 0, 255]) * 3
        png = (b'\x89PNG\r\n\x1a\n' + chunk(b'IHDR', struct.pack('>IIBBBBB', 12, 6, 8, 2, 0, 0, 0))
               + chunk(b'IDAT', zlib.compress((b'\x00' + row) * 6)) + chunk(b'IEND', b''))
        (artifact / 'upload.png').write_bytes(png)
        vendor = Mock()
        metadata = {'id': 145, 'name': 'Testovací zdroj', 'width': 250, 'height': 122,
                    'type': 2, 'rotate': 0, 'backgroundId': 0}
        vendor.get_style_catalog.return_value = [metadata,
            {'id': 999, 'name': 'Nepodporovaný veľký displej', 'width': 960, 'height': 640, 'type': 2}]
        vendor.get_style_detail.return_value = metadata
        vendor.get_style_layout.return_value = [{
            'id': 2615, 'name': 'Text zdroja', 'type': 'text', 'mpname': 'PriceRetail',
            'text': '9,99', 'prefix': '', 'suffix': ' €', 'status': True,
            'style': {'left': '165px', 'top': '5px', 'width': '90px', 'height': '20px',
                      'font-family': 'Arial', 'font-size': '14px', 'color': '#000000',
                      'background-color': '#ffffff', 'board-width': '1px',
                      'font-weight': 400, 'text-align': 'left'}}]
        registry = Mock()
        registry.default_id = 'test'
        registry.get.return_value = vendor
        registry.metadata.return_value = [{'id': 'test', 'name': 'Test controller',
                                           'base_url': 'http://controller.invalid', 'default': True}]
        frontend.BrowserDomIntegrationTests.run_browser(self, 'designer_media_browser_flows.test.js',
                                                       controller_registry=registry)
        self.assertGreaterEqual(vendor.get_style_catalog.call_count, 1)
        self.assertGreaterEqual(vendor.get_style_layout.call_count, 1)
        self.assertEqual({call[0] for call in vendor.mock_calls},
                         {'get_style_catalog', 'get_style_detail', 'get_style_layout'})
        self.assertEqual(vendor.get_style_layout.return_value[0]['style']['width'], '90px')


if __name__ == '__main__':
    unittest.main()
