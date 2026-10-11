import unittest
from unittest.mock import patch
from esl_web.vendor import VendorClient,VendorConfig,VendorError

class TagDisplayTests(unittest.TestCase):
    def setUp(self):
        self.client=VendorClient(VendorConfig(base_url='http://127.0.0.1/esls_new'))

    def test_reads_exact_numeric_tag_identity_and_detail_without_writes(self):
        with patch.object(self.client,'get_tags',return_value=[{'id':'8','mac':'1548769328','updateProgress':'5'}]), patch.object(self.client,'_request_document',return_value={'tag':{'id':8,'mac':1548769328,'width':250,'height':122,'styleid':96,'updateProgress':5,'updatetime':1783423724000}}) as request:
            result=self.client.get_tag_display('92.80.88.48')
        self.assertEqual(result['mac'],'92.80.88.48')
        self.assertEqual(result['style_id'],96)
        self.assertFalse(result['physical_screen_verified'])
        request.assert_called_once_with('GET','/tag/getTagById?id=8')

    def test_missing_duplicate_and_mismatched_tag_fail_closed(self):
        cases=[([],None),([{'id':8,'mac':'1548769328'},{'id':9,'mac':'92.80.88.48'}],None),([{'id':8,'mac':'1548769328'}],{'tag':{'id':8,'mac':123,'width':250,'height':122}})]
        for rows,detail in cases:
            with self.subTest(rows=rows), patch.object(self.client,'get_tags',return_value=rows), patch.object(self.client,'_request_document',return_value=detail):
                with self.assertRaises(VendorError): self.client.get_tag_display('92.80.88.48')
