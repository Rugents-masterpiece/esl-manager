import unittest
from unittest.mock import patch
from esl_web.vendor import VendorClient, VendorConfig, VendorError
from test_draft_media import png

class NativePhotoUploadTests(unittest.TestCase):
    def setUp(self):
        self.client = VendorClient(VendorConfig('http://127.0.0.1/esls_new'))
        self.data = png(2, 3)
        self.photos = [{'name': 'ESLM_icon', 'width': 2, 'height': 3}]

    def test_new_photo_multipart_and_exact_readback(self):
        with patch.object(self.client, 'get_photos', side_effect=[[], self.photos]), patch.object(self.client, 'get_photo_data', return_value=(self.data, 'image/png')), patch.object(self.client, '_request_document', return_value=1) as request:
            result = self.client.upload_photo('ESLM_icon', self.data, 2, 3)
        self.assertEqual(result['name'], 'ESLM_icon')
        self.assertTrue(result['content_exact'])
        args = request.call_args.args
        self.assertEqual(args[:2], ('POST', '/style/uploadPhoto'))
        self.assertIn(b'name="photo"; filename="ESLM_icon.png"', args[2])
        self.assertIn(b'name="redphoto"; filename=""', args[2])
        for field in ('name', 'width', 'height'):
            self.assertIn(('name="'+field+'"').encode(), args[2])
        self.assertIn(self.data, args[2])
        self.assertTrue(args[3].startswith('multipart/form-data; boundary='))

    def test_existing_exact_photo_does_not_upload(self):
        with patch.object(self.client, 'get_photos', return_value=self.photos), patch.object(self.client, 'get_photo_data', return_value=(self.data,'image/png')), patch.object(self.client, '_request_document') as request:
            self.assertTrue(self.client.upload_photo('ESLM_icon', self.data, 2, 3)['content_exact'])
        request.assert_not_called()

    def test_bad_or_ambiguous_asset_fails_without_overwrite(self):
        with patch.object(self.client, 'get_photos', return_value=self.photos), patch.object(self.client, 'get_photo_data', return_value=(png(2,3,raw=(b'\0'+b'\xff'*8)*3),'image/png')), patch.object(self.client, '_request_document') as request:
            with self.assertRaises(VendorError):
                self.client.upload_photo('ESLM_icon', self.data, 2, 3)
        request.assert_not_called()

    def test_invalid_image_name_and_geometry_make_no_request(self):
        for name,data,w,h in [('bad\r\nname',self.data,2,3),('icon',b'bad',2,3),('icon',self.data,3,3),('icon',self.data,True,3)]:
            with self.subTest(name=name,w=w), patch.object(self.client,'_request_document') as request:
                with self.assertRaises(VendorError):
                    self.client.upload_photo(name,data,w,h)
            request.assert_not_called()
