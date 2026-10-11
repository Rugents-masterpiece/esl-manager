import tempfile
import unittest
from pathlib import Path
from esl_web.service import Service, ValidationError
from esl_web.storage import Storage

class TagDottedMacTests(unittest.TestCase):
    def test_decimal_dotted_hardware_identity_is_not_reinterpreted_as_ethernet_mac(self):
        for source, expected in [('92.81.10.37','92.81.10.37'),('92.81.05.82','92.81.5.82'),('192.168.100.100','192.168.100.100')]:
            with self.subTest(source=source):
                self.assertEqual(Service._normalized_mac(source),expected)

    def test_bad_decimal_dotted_addresses_fail_and_existing_ethernet_format_remains(self):
        for source in ('999.999.999.999','256.1.2.3','1.2.-3.4','1.2.3','1.2.3.4.5','1548814885'):
            with self.subTest(source=source), self.assertRaises(ValidationError):
                Service._normalized_mac(source)
        self.assertEqual(Service._normalized_mac('aabb.ccdd.eeff'),'AA:BB:CC:DD:EE:FF')

    def test_imported_vendor_tag_content_can_be_saved_without_changing_identity_or_dimensions(self):
        with tempfile.TemporaryDirectory() as directory:
            storage=Storage(Path(directory)/'test.db');storage.initialize();storage.seed_demo();service=Service(storage)
            with storage.connection() as connection:
                connection.execute("INSERT INTO templates(id,controller_id,vendor_id,name,width,height,screen_type) VALUES ('dotted-template','legacy','dotted','Dotted',296,128,2)")
            body={'controller_id':'legacy','mac':'AA:BB:CC:DD:EE:99','label':'CWT','device_model_id':'2.9EPD-BWR','width':296,'height':128,'router_id':'router-main','template_id':'dotted-template','test_data':{}}
            tag=service.create_staged_tag({'id':'dotted-tag',**body})
            with storage.connection() as connection:
                connection.execute("UPDATE tags SET mac='92.81.10.37',inventory_source='vendor',configuration_source='vendor' WHERE id=?",(tag['id'],))
            updated=service.update_tag_configuration(tag['id'],{**body,'mac':'92.81.10.37','test_data':{'product_name':'TEST 03 Ovsené vločky','price':'1,29'}})
            self.assertEqual(updated['mac'],'92.81.10.37');self.assertEqual((updated['width'],updated['height']),(296,128));self.assertEqual(updated['test_data']['product_name'],'TEST 03 Ovsené vločky')
