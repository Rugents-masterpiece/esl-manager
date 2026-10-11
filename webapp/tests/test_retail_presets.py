"""Portable Slovak retail presets: exact families, data, layout and local persistence."""
import json
import tempfile
import unittest
from collections import Counter
from decimal import Decimal
from pathlib import Path

from esl_web.drafts import DraftService
from esl_web.storage import Storage, SUPPORTED_DEVICE_MODELS

PRESETS = Path(__file__).resolve().parents[1] / 'template-presets' / 'retail-sk'


class RetailPresetTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.files = sorted(PRESETS.glob('*.json'))
        cls.documents = [json.loads(path.read_text(encoding='utf-8')) for path in cls.files]

    def test_three_variants_for_every_exact_model(self):
        self.assertEqual(len(self.documents), 9)
        self.assertEqual(len({doc['name'] for doc in self.documents}), 9)
        self.assertEqual(Counter(doc['model_id'] for doc in self.documents),
                         Counter({model: 3 for model in SUPPORTED_DEVICE_MODELS}))
        for model in SUPPORTED_DEVICE_MODELS:
            self.assertEqual({path.name for path in self.files if path.name.startswith(model + '-')},
                             {f'{model}-{style}.json' for style in ('standard', 'promotion', 'details')})

    def test_strict_schema_and_legible_price_priority(self):
        for doc in self.documents:
            with self.subTest(name=doc['name']):
                self.assertEqual(DraftService.validate(doc), doc)
                self.assertEqual(doc['schema_version'], 2)
                fields = {element['field'] for element in doc['elements'] if element['field']}
                self.assertTrue({'product_name', 'price', 'unit_price'} <= fields)
                self.assertTrue(fields <= doc['sample_data'].keys())
                price = next(e for e in doc['elements'] if e['field'] == 'price')
                self.assertTrue(price['bold'])
                self.assertGreaterEqual(price['font_size'], 32)
                self.assertEqual(price['suffix'], ' €')
                self.assertGreaterEqual(price['height'], price['font_size'] * Decimal('1.15'))

    def test_foreground_elements_do_not_overlap(self):
        for doc in self.documents:
            foreground = [e for e in doc['elements'] if e['type'] != 'rectangle']
            for i, a in enumerate(foreground):
                for b in foreground[i + 1:]:
                    with self.subTest(name=doc['name'], a=a['id'], b=b['id']):
                        overlap = (max(a['x'], b['x']) < min(a['x'] + a['width'], b['x'] + b['width'])
                                   and max(a['y'], b['y']) < min(a['y'] + a['height'], b['y'] + b['height']))
                        self.assertFalse(overlap)

    def test_demo_unit_prices_and_discount_reference(self):
        for doc in self.documents:
            sample = doc['sample_data']
            price = Decimal(sample['price'].replace(',', '.'))
            unit = Decimal(sample['unit_price'].split(' ')[0].replace(',', '.'))
            volume = Decimal('0.5') if 'package_info' in sample and '500 ml' in sample['package_info'] else Decimal('1')
            self.assertEqual(price / volume, unit)
            if 'lowest_30d_price' in sample:
                self.assertLess(price, Decimal(sample['lowest_30d_price'].replace(',', '.')))
                prior = next(e for e in doc['elements'] if e['field'] == 'lowest_30d_price')
                self.assertIn('30 dní', prior['prefix'])
                self.assertIn('promotion_validity', sample)

    def test_media_and_monochrome_fallback(self):
        for doc in self.documents:
            for element in doc['elements']:
                if doc['model_id'].endswith('TFT-BW'):
                    self.assertNotEqual(element['color'], '#ff0000')
                    self.assertNotEqual(element['background'], '#ff0000')
                if element['type'] == 'barcode':
                    self.assertEqual(element['barcode_format'], 'CODE128')
                    self.assertEqual(element['field'], 'sku')
                    self.assertEqual(len(doc['sample_data']['sku']), 12)
                if element['type'] == 'qrcode':
                    self.assertEqual(element['error_correction'], 'M')
                    self.assertEqual(element['width'], element['height'])
                    self.assertEqual(doc['sample_data']['product_url'], 'https://example.com/p/10001')

    def test_disposable_database_roundtrip(self):
        with tempfile.TemporaryDirectory() as tmp:
            storage = Storage(Path(tmp) / 'presets.db')
            storage.initialize()
            drafts = DraftService(storage)
            drafts.initialize()
            for doc in self.documents:
                record = drafts.create(doc)
                self.assertEqual(record['document'], doc)
                self.assertEqual(drafts.get(record['id']), record)
            self.assertEqual(len(drafts.list()), 9)


if __name__ == '__main__':
    unittest.main()
