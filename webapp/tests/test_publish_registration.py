"""Publisher receipts must register without caller-side schema rewriting."""
import json
from pathlib import Path
import tempfile
import unittest

from esl_web.draft_publish import DraftPublishService, translate_native_plan
from esl_web.storage import Storage
from esl_web.template_apply import TemplatePublicationService
from test_draft_publish import Controller

ROOT = Path(__file__).resolve().parents[1]


class PublishRegistrationTests(unittest.TestCase):
    def test_photo_components_use_native_photo_table_not_product_table(self):
        paths = sorted((ROOT / 'template-presets/retail-sk').glob('*.json'))
        paths += sorted((ROOT / 'template-presets/extended-sk').glob('*.json'))
        for path in paths:
            plan = translate_native_plan(json.loads(path.read_text()))
            for field in plan['fields']:
                component = field['component']
                with self.subTest(path=path.name, alias=field['alias']):
                    self.assertEqual(component['table'],
                                     'tb_photos' if component['type'] == 'photo' else 'tb_tagsandgoods')
                    self.assertEqual(component['style']['autoReacting'], component['type'] == 'text')

    def test_all_presets_register_publisher_bindings_and_read_back(self):
        with tempfile.TemporaryDirectory() as directory:
            storage = Storage(Path(directory) / 'receipts.sqlite')
            storage.initialize()
            publications = TemplatePublicationService(storage)
            publications.initialize()
            paths = sorted((ROOT / 'template-presets/retail-sk').glob('*.json'))
            paths += sorted((ROOT / 'template-presets/extended-sk').glob('*.json'))
            self.assertEqual(len(paths), 30)
            for index, path in enumerate(paths):
                with self.subTest(path=path.name):
                    document = json.loads(path.read_text())
                    plan = translate_native_plan(document)
                    client = Controller(plan['width'], plan['height'], plan['alignment'], plan['screen_type'])
                    result = DraftPublishService(client, media_uploader=lambda *args: None).publish(document)
                    receipt = publications.register('default', index + 1, str(index), 1,
                                                    document, result['bindings'])
                    self.assertEqual(receipt, publications.get('default', index + 1))
                    self.assertEqual(receipt['bindings'], result['bindings'])
            self.assertEqual(len(publications.list('default')), 30)
