"""V2 bindings are literal object keys; preserve native names, never expressions."""
import unittest
from esl_web.drafts import DraftService
from esl_web.service import ValidationError
from test_drafts import document


class LiteralFieldTests(unittest.TestCase):
    def test_js_duplicate_names_round_trip_without_lone_surrogates(self):
        import json
        import subprocess
        from pathlib import Path
        code = """const M=require('./static/designer-model.js');const docs=[];
for(const type of ['text','image'])for(const name of ['a'.repeat(191)+'😀','😀'.repeat(200)]) {
 const d=M.add(M.createDocument(),type);d.elements[0].name=name;
 docs.push(M.duplicate(d,d.elements[0].id));
}console.log(JSON.stringify(docs));"""
        result = subprocess.run(['node', '-e', code], cwd=Path(__file__).resolve().parents[1],
                                capture_output=True, text=True, check=True)
        for doc in json.loads(result.stdout):
            with self.subTest(type=doc['elements'][0]['type'], name=doc['elements'][0]['name']):
                self.assertEqual(DraftService.validate(doc), doc)

    def test_v2_preserves_unicode_spaces_dots_and_own_reserved_names(self):
        for key in ['价格', '商品名', 'pozadie názvu', 'kod položky', 'test ', 'a.b',
                    '__proto__', 'constructor', 'toString', '😀' * 100]:
            with self.subTest(key=key):
                doc = document()
                doc['schema_version'] = 2
                doc['elements'][0]['field'] = key
                doc['sample_data'] = {key: 'hodnota'}
                self.assertEqual(DraftService.validate(doc), doc)

    def test_v1_retains_ascii_limits_and_v2_rejects_invalid_literal_keys(self):
        for version, keys in [(1, ['价格', 'kod položky', 'a.b', 'x' * 65]),
                              (2, ['x' * 101, '😀' * 101, 'bad\n', 'bad\x00',
                                   'bad\x7f', 'bad\x85', '\ud800'])]:
            for key in keys:
                for place in ['field', 'sample']:
                    with self.subTest(version=version, key=repr(key), place=place):
                        doc = document()
                        doc['schema_version'] = version
                        if place == 'field':
                            doc['elements'][0]['field'] = key
                        else:
                            doc['sample_data'] = {key: 'value'}
                        with self.assertRaises(ValidationError):
                            DraftService.validate(doc)
        doc = document()
        doc['schema_version'] = 2
        doc['elements'][0]['field'] = ''
        self.assertEqual(DraftService.validate(doc), doc)
        doc['sample_data'] = {'': 'value'}
        with self.assertRaises(ValidationError):
            DraftService.validate(doc)


if __name__ == '__main__':
    unittest.main()
