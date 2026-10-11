"""Contracts for seven genuinely different additional preset purposes per model."""
import json
import tempfile
import unittest
from collections import Counter
from decimal import Decimal
from pathlib import Path

from esl_web.drafts import DraftService
from esl_web.storage import Storage, SUPPORTED_DEVICE_MODELS

ROOT = Path(__file__).resolve().parents[1]
PRESETS = ROOT / 'template-presets/extended-sk'
REQUIRED = {
    'minimal': {'product_name', 'package_info', 'price', 'unit_price'},
    'loyalty': {'product_name', 'package_info', 'regular_price', 'member_price', 'regular_unit_price', 'member_unit_price', 'membership_condition'},
    'weighed': {'product_name', 'price_per_kg', 'origin', 'quality_class', 'plu_code'},
    'deposit': {'product_name', 'package_info', 'product_price', 'deposit_amount', 'total_price', 'unit_price'},
    'batch': {'product_name', 'package_info', 'price', 'unit_price', 'batch_code', 'date_label', 'expiry_date'},
    'technical': {'product_name', 'brand', 'model_code', 'specs', 'price', 'unit_price', 'warranty_text'},
    'warehouse': {'product_name', 'sku', 'stock_qty', 'stock_unit', 'pick_location', 'replenishment_status'},
}


def documents():
    return {p.stem: json.loads(p.read_text(encoding='utf-8')) for p in PRESETS.glob('*.json')}


class ExtendedPresetTests(unittest.TestCase):
    def test_seven_additional_variants_for_every_model(self):
        docs = documents()
        expected = {f'{model}-{variant}' for model in SUPPORTED_DEVICE_MODELS for variant in REQUIRED}
        self.assertEqual(set(docs), expected)
        self.assertEqual(len({d['name'] for d in docs.values()}), 21)
        original = [json.loads(p.read_text()) for p in (ROOT / 'template-presets/retail-sk').glob('*.json')]
        self.assertEqual(Counter(d['model_id'] for d in [*docs.values(), *original]),
                         Counter({model: 10 for model in SUPPORTED_DEVICE_MODELS}))

    def test_exact_schema_bindings_and_distinct_layouts(self):
        docs = documents()
        self.assertEqual(len(docs), 21)
        for model in SUPPORTED_DEVICE_MODELS:
            signatures = set()
            for variant, required in REQUIRED.items():
                doc = docs[f'{model}-{variant}']
                with self.subTest(model=model, variant=variant):
                    self.assertEqual(DraftService.validate(doc), doc)
                    self.assertEqual(doc['schema_version'], 2)
                    fields = {e['field'] for e in doc['elements'] if e['field']}
                    self.assertTrue(required <= fields, required - fields)
                    self.assertTrue(fields <= doc['sample_data'].keys())
                    signatures.add(tuple((e['type'], e['x'], e['y'], e['width'], e['height'], e['font_size']) for e in doc['elements']))
            self.assertEqual(len(signatures), 7, 'variants must not merely change colors or samples')

    def test_specialized_sample_semantics(self):
        docs = documents()
        self.assertEqual(len(docs), 21)
        number = lambda value: Decimal(str(value).replace(',', '.'))
        for model in SUPPORTED_DEVICE_MODELS:
            sample = docs[f'{model}-deposit']['sample_data']
            self.assertEqual(number(sample['product_price']) + number(sample['deposit_amount']), number(sample['total_price']))
            sample = docs[f'{model}-loyalty']['sample_data']
            self.assertLess(number(sample['member_price']), number(sample['regular_price']))
            self.assertTrue(sample['membership_condition'])
            self.assertFalse(any(e['field'] == 'lowest_30d_price' for e in docs[f'{model}-loyalty']['elements']))
            weighed = docs[f'{model}-weighed']
            main = next(e for e in weighed['elements'] if e['field'] == 'price_per_kg')
            self.assertEqual(main['suffix'], ' €/kg')
            self.assertGreaterEqual(main['font_size'], 32)
            self.assertFalse(any(e['field'] in {'price', 'product_price', 'total_price'} for e in docs[f'{model}-warehouse']['elements']))
            self.assertTrue(any(e['type'] == 'image' and e['image_data'] for e in docs[f'{model}-technical']['elements']))

    def test_foreground_elements_do_not_overlap(self):
        docs = documents()
        self.assertEqual(len(docs), 21)
        for key, doc in docs.items():
            elements = [e for e in doc['elements'] if e['type'] != 'rectangle']
            for i, a in enumerate(elements):
                for b in elements[i + 1:]:
                    with self.subTest(preset=key, a=a['id'], b=b['id']):
                        self.assertFalse(max(a['x'], b['x']) < min(a['x'] + a['width'], b['x'] + b['width'])
                                         and max(a['y'], b['y']) < min(a['y'] + a['height'], b['y'] + b['height']))

    def test_source_catalog_accounts_for_every_binding_without_claiming_live_feeds(self):
        manifest = json.loads((ROOT / 'template-presets/data-sources.json').read_text())
        self.assertEqual(manifest['runtime_source'], 'document.sample_data')
        self.assertFalse(manifest['live_upstreams_connected'])
        docs = {**documents(), **{p.stem: json.loads(p.read_text()) for p in (ROOT / 'template-presets/retail-sk').glob('*.json')}}
        self.assertEqual(set(manifest['presets']), set(docs))
        for key, doc in docs.items():
            fields = {e['field'] for e in doc['elements'] if e['field']}
            mapping = manifest['presets'][key]['bindings']
            self.assertEqual(set(mapping), fields)
            for field, binding in mapping.items():
                self.assertIn(binding['upstream_source'], manifest['upstream_contracts'])
                self.assertEqual(binding['runtime'], 'document.sample_data')
                self.assertIs(binding['upstream_connected'], False)
                self.assertTrue(binding['meaning'])
                self.assertIn(field, doc['sample_data'])

    def test_twenty_one_roundtrip_without_changing_existing_draft(self):
        docs = documents()
        self.assertEqual(len(docs), 21)
        with tempfile.TemporaryDirectory() as tmp:
            storage = Storage(Path(tmp) / 'extended.db')
            storage.initialize()
            service = DraftService(storage)
            service.initialize()
            original = service.create({'schema_version': 2, 'name': 'Preserve user draft',
                                       'model_id': '2.13EPD-BWR', 'elements': [], 'sample_data': {}})
            for doc in docs.values():
                record = service.create(doc)
                self.assertEqual(service.get(record['id']), record)
            self.assertEqual(service.get(original['id']), original)
            self.assertEqual(len(service.list()), 22)


if __name__ == '__main__':
    unittest.main()
