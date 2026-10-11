"""Offline contract tests; the fake is deliberately not a hardware simulator."""
import copy
import importlib
import json
from pathlib import Path
import unittest

from esl_web.service import ValidationError, IntegrationError

ROOT = Path(__file__).resolve().parents[1]


def document():
    return json.loads((ROOT / 'template-presets/retail-sk/2.13EPD-BWR-standard.json').read_text())


class Controller:
    def __init__(self, width=250, height=122, alignment=9, screen_type=2):
        self.layout = []
        self.name = 'Default200'
        self.created = False
        self.calls = []
        self.fields = []
        self.width, self.height = width, height
        self.alignment, self.screen_type = alignment, screen_type

    def get_style_catalog(self):
        return [self.get_style_detail(200)] if self.created else []

    def create_style(self, alignment):
        self.calls.append(('create', alignment))
        self.created = True
        return 200

    def get_style_detail(self, target):
        return dict(id=200, name=self.name, width=self.width, height=self.height,
                    type=self.screen_type, mappingtype=700, styleFileds=list(self.fields))

    def get_style_data(self, target):
        data = self.get_style_detail(target)
        data['type'] = self.alignment
        data['dispMs'] = [self.native_record(e) for e in self.layout]
        return data

    @staticmethod
    def native_record(e):
        s = e['style']
        def px(key):
            return int(str(s.get(key, '0px')).removesuffix('px'))
        return dict(id=e['id'], styleid=200, name=e['name'], columnType=e['type'],
                    sourceColumn=e['feil'], source=e['table'], status=e.get('status', True),
                    text=e.get('text', ''), startText=e.get('prefix', ''), endText=e.get('suffix', ''),
                    x=px('left'), y=px('top'), textX=px('left'), textY=px('top'),
                    width=px('width'), height=px('height'), fontFamily=s.get('font-family'),
                    fontSize=px('font-size'), fontBold='bold' if str(s.get('font-weight')) == '700' else 'normal',
                    fontColor=int(s.get('color', '#000000')[1:], 16),
                    backgroundColor=int(s.get('background-color', '#ffffff')[1:], 16),
                    lineBoarderWidth=1, text_align=s.get('text-align', 'left'),
                    textDecoration=s.get('text-decoration', 'none'), vertical=False,
                    autoReacting=s.get('autoReacting', False), z_index=0)

    def get_style_layout(self, target):
        return copy.deepcopy(self.layout)

    def add_style_field(self, target, mappingtype, kind, alias):
        self.calls.append(('add', alias))
        self.fields.append(alias)
        self.layout.append(dict(id=1000 + len(self.layout), name=kind + str(len(self.layout)),
                                type=kind, feil=kind, mpname=alias, text='', style={},
                                table='tb_photos' if kind == 'photo' else 'tb_tagsandgoods'))
        return 1

    def rename_style(self, target, alignment, name):
        self.calls.append(('rename',))
        self.name = name

    def save_style_layout(self, target, layout):
        self.calls.append(('save',))
        self.layout = copy.deepcopy(layout)
        for component in self.layout:
            component['style']['board-width'] = '1px'
            component['style']['z-index'] = 0

    def get_template_preview(self, target):
        self.calls.append(('preview',))
        return b'offline-preview-bytes', 'image/png'

    def delete_style(self, target):
        self.calls.append(('delete', target))
        self.created = False


class DraftPublicationTests(unittest.TestCase):
    def api(self):
        try:
            return importlib.import_module('esl_web.draft_publish')
        except ModuleNotFoundError:
            self.fail('DraftPublishService is not implemented')

    def test_text_vertical_tracer_publishes_and_returns_registration_metadata(self):
        api = self.api()
        doc = document()
        doc['elements'] = [e for e in doc['elements'] if e['type'] == 'text'][:1]
        client = Controller()
        registered = []
        result = api.DraftPublishService(client, register=registered.append).publish(doc)
        self.assertEqual(result['vendor_id'], 200)
        self.assertTrue(result['verified'])
        self.assertTrue(result['registered'])
        self.assertEqual(registered, [result['raw_metadata']])
        self.assertEqual(len(result['source_sha256']), 64)
        self.assertEqual(len(client.layout), 1)
        component = client.layout[0]
        self.assertEqual(component['style']['font-family'], 'HuaweiSans-Bold')
        self.assertEqual(component['prefix'], doc['elements'][0]['prefix'])
        self.assertEqual(result['mapping'][component['mpname']]['field'], doc['elements'][0]['field'])
        self.assertEqual([c[0] for c in client.calls], ['create', 'add', 'rename', 'save', 'preview'])

    def test_all_thirty_plans_keep_every_element_and_duplicate_bindings(self):
        api = self.api()
        paths = sorted((ROOT / 'template-presets/retail-sk').glob('*.json')) + sorted((ROOT / 'template-presets/extended-sk').glob('*.json'))
        self.assertEqual(len(paths), 30)
        for path in paths:
            doc = json.loads(path.read_text())
            plan = api.translate_native_plan(doc)
            self.assertEqual(len(plan['fields']), len(doc['elements']))
            aliases = [f['alias'] for f in plan['fields']]
            self.assertEqual(len(aliases), len(set(aliases)))
            for element, field in zip(doc['elements'], plan['fields']):
                expected_type = {'rectangle': 'photo', 'image': 'photo', 'qrcode': 'photo'}.get(element['type'], element['type'])
                self.assertEqual(field['column_name'], expected_type)
                self.assertEqual(field['component']['style']['width'], str(element['width']) + 'px')
                if element['type'] == 'rectangle':
                    self.assertEqual(field['component']['text'], field['media']['name'])
                    self.assertTrue(any('rectangle' in w.lower() for w in plan['warnings']))
                if element['type'] == 'qrcode':
                    self.assertTrue(any('ECC' in w and 'not' in w for w in plan['warnings']))
                if element['type'] == 'image':
                    self.assertTrue(field['media']['bytes'].startswith(b'\x89PNG'))
        duplicate = document()
        base = next(e for e in duplicate['elements'] if e['type'] == 'text')
        duplicate['elements'] = [base, dict(base, id='second', field=base['field'])]
        plan = api.translate_native_plan(duplicate)
        self.assertNotEqual(plan['fields'][0]['alias'], plan['fields'][1]['alias'])
        self.assertEqual(len(plan['mapping']), 2)

    def test_media_uploader_is_explicit_and_photo_reference_survives(self):
        api = self.api()
        doc = json.loads((ROOT / 'template-presets/extended-sk/2.13EPD-BWR-technical.json').read_text())
        doc['elements'] = [e for e in doc['elements'] if e['type'] == 'image']
        client = Controller()
        with self.assertRaises(ValidationError):
            api.DraftPublishService(client).publish(doc)
        self.assertEqual(client.calls, [])
        uploaded = []
        def upload(name, data, width, height):
            uploaded.append((name, data, width, height))
            return {'name': name}
        result = api.DraftPublishService(client, media_uploader=upload).publish(doc)
        self.assertEqual(len(uploaded), 1)
        self.assertEqual(client.layout[0]['type'], 'photo')
        self.assertEqual(client.layout[0]['text'], uploaded[0][0])
        self.assertFalse(result['registered'])

    def test_plan_uses_captured_native_css_contract(self):
        api = self.api()
        doc = document()
        plan = api.translate_native_plan(doc)
        style = plan['fields'][0]['component']['style']
        self.assertIn('board-width', style)
        self.assertNotIn('border-width', style)
        self.assertEqual(style['background-color'], '#ffffff')
        capture = json.loads((ROOT / 'test-artifacts/publish-preflight/145.json').read_text())
        api.verify_native_components(capture['layout'], capture['data']['dispMs'], 145)
        changed = copy.deepcopy(capture['data']['dispMs'])
        changed[0]['width'] += 1
        with self.assertRaises(IntegrationError):
            api.verify_native_components(capture['layout'], changed, 145)

    def test_ambiguous_field_mutation_is_reconciled_once_with_normalized_mpname(self):
        api = self.api()
        doc = document()
        doc['elements'] = [e for e in doc['elements'] if e['type'] == 'text'][:2]
        client = Controller()
        original_add = client.add_style_field
        def add(*args):
            original_add(*args)
            client.layout[-1]['mpname'] = 'text'
            raise TimeoutError('ambiguous committed outcome')
        client.add_style_field = add
        result = api.DraftPublishService(client).publish(doc)
        self.assertEqual(len([c for c in client.calls if c[0] == 'add']), 2)
        self.assertEqual(len(result['mapping']), 2)
        self.assertEqual(len(result['component_mapping']), 2)

    def test_bad_native_detail_is_not_registered_and_journal_retains_owned_target(self):
        api = self.api()
        doc = document()
        doc['elements'] = [e for e in doc['elements'] if e['type'] == 'text'][:1]
        client = Controller()
        original = client.get_style_data
        def get(target):
            data = original(target)
            if any(c[0] == 'save' for c in client.calls):
                data['dispMs'][0]['text'] = 'ignored save'
            return data
        client.get_style_data = get
        journal, registered, snapshots = {}, [], []
        with self.assertRaises(IntegrationError):
            api.DraftPublishService(client, register=registered.append, journal_sink=snapshots.append).publish(doc, journal=journal)
        self.assertEqual(registered, [])
        self.assertEqual(journal['owned_target_id'], 200)
        self.assertEqual(journal['status'], 'failed')
        self.assertTrue(snapshots)
        self.assertTrue(client.created)

    def test_verified_journal_is_idempotent_by_fresh_read_not_mutation(self):
        api = self.api()
        doc = document()
        doc['elements'] = [e for e in doc['elements'] if e['type'] == 'text'][:1]
        client, journal = Controller(), {}
        publisher = api.DraftPublishService(client, controller_id='test-controller')
        first = publisher.publish(doc, journal=journal)
        calls = list(client.calls)
        again = publisher.publish(doc, journal=journal)
        self.assertEqual(first['source_sha256'], again['source_sha256'])
        self.assertEqual(client.calls, calls + [('preview',)])
        changed = copy.deepcopy(doc)
        changed['elements'][0]['text'] += '!'
        with self.assertRaises(ValidationError):
            publisher.publish(changed, journal=journal)

    def test_create_without_response_id_never_claims_ownership_or_deletes(self):
        api = self.api()
        doc = document()
        doc['elements'] = [e for e in doc['elements'] if e['type'] == 'text'][:1]
        client, journal = Controller(), {}
        def create(alignment):
            client.created = True
            client.calls.append(('create', alignment))
            raise TimeoutError('created but response lost')
        client.create_style = create
        with self.assertRaises(IntegrationError):
            api.DraftPublishService(client).publish(doc, journal=journal)
        self.assertIsNone(journal.get('owned_target_id'))
        self.assertNotIn('delete', [c[0] for c in client.calls])

    def test_rollback_requires_journal_owned_target_and_reads_after_delete(self):
        api = self.api()
        doc = document()
        doc['elements'] = [e for e in doc['elements'] if e['type'] == 'text'][:1]
        client, journal = Controller(), {}
        publisher = api.DraftPublishService(client)
        publisher.publish(doc, journal=journal)
        self.assertTrue(publisher.rollback(journal))
        self.assertEqual(journal['status'], 'rolled_back')
        self.assertFalse(client.created)
        journal['preexisting_ids'] = [200]
        with self.assertRaises(IntegrationError):
            publisher.rollback(journal)

    def test_bindings_include_static_photo_values_and_preview_bytes(self):
        api = self.api()
        doc = json.loads((ROOT / 'template-presets/extended-sk/2.13EPD-BWR-technical.json').read_text())
        client = Controller()
        result = api.DraftPublishService(client, media_uploader=lambda *args: None).publish(doc, 'Pilot')
        self.assertEqual(result['preview_bytes'], b'offline-preview-bytes')
        for element, native in zip(doc['elements'], client.layout):
            binding = result['bindings'][native['mpname']]
            self.assertEqual(binding['element_id'], element['id'])
            self.assertEqual(binding['field'], element['field'])
            self.assertEqual(binding['static_value'], native['text'])

    def test_different_size_photo_requires_explicit_prepared_asset(self):
        api = self.api()
        doc = json.loads((ROOT / 'template-presets/extended-sk/2.13EPD-BWR-technical.json').read_text())
        image = next(e for e in doc['elements'] if e['type'] == 'image')
        doc['elements'] = [image]
        image['width'] = 60
        with self.assertRaises(ValidationError):
            api.translate_native_plan(doc)
        import io
        from PIL import Image
        output = io.BytesIO()
        Image.new('RGB', (60, 60), 'white').save(output, format='PNG')
        plan = api.translate_native_plan(doc, media_assets={image['id']: output.getvalue()})
        self.assertEqual(plan['fields'][0]['media']['bytes'], output.getvalue())
        client = Controller()
        result = api.DraftPublishService(client, media_uploader=lambda *args: None).publish(doc, media_assets={image['id']: output.getvalue()})
        self.assertTrue(result['verified'])

    def test_normalized_saved_mpname_uses_authoritative_fields_and_owned_ids(self):
        api = self.api()
        doc = document()
        doc['elements'] = [e for e in doc['elements'] if e['type'] == 'text'][:2]
        client = Controller()
        original = client.save_style_layout
        def save(target, layout):
            original(target, layout)
            for e in client.layout:
                e['mpname'] = 'text'
                e['style']['font-weight'] = int(e['style']['font-weight'])
            raise TimeoutError('response lost')
        client.save_style_layout = save
        result = api.DraftPublishService(client).publish(doc)
        self.assertEqual(len(result['bindings']), 2)
        self.assertEqual(len([c for c in client.calls if c[0] == 'save']), 1)

    def test_registration_failure_retries_only_registration_after_fresh_read(self):
        api = self.api()
        doc = document()
        doc['elements'] = [e for e in doc['elements'] if e['type'] == 'text'][:1]
        client, journal = Controller(), {}
        def fail(metadata):
            raise RuntimeError('local transaction failed')
        publisher = api.DraftPublishService(client, register=fail)
        with self.assertRaises(RuntimeError):
            publisher.publish(doc, journal=journal)
        self.assertEqual(journal['status'], 'verified')
        self.assertFalse(journal['registered'])
        registered = []
        publisher.register = registered.append
        result = publisher.publish(doc, journal=journal)
        self.assertTrue(result['registered'])
        self.assertEqual(len(registered), 1)
        self.assertEqual(len([c for c in client.calls if c[0] == 'create']), 1)

    def test_rejected_features_never_reach_controller(self):
        api = self.api()
        for update in ({'type': 'line'}, {'italic': True}):
            with self.subTest(update=update):
                doc = document()
                doc['elements'] = [next(e for e in doc['elements'] if e['type'] == 'text')]
                doc['elements'][0].update(update)
                client = Controller()
                with self.assertRaises(ValidationError):
                    api.DraftPublishService(client).publish(doc)
                self.assertEqual(client.calls, [])

    def test_empty_native_preview_blocks_registration(self):
        api = self.api()
        doc = document()
        doc['elements'] = [e for e in doc['elements'] if e['type'] == 'text'][:1]
        client, registered = Controller(), []
        client.get_template_preview = lambda target: (b'', 'image/png')
        with self.assertRaises(IntegrationError):
            api.DraftPublishService(client, register=registered.append).publish(doc)
        self.assertEqual(registered, [])

    def test_ignored_field_mutation_has_no_retry_and_no_false_success(self):
        api = self.api()
        doc = document()
        doc['elements'] = [e for e in doc['elements'] if e['type'] == 'text'][:1]
        client, journal = Controller(), {}
        client.add_style_field = lambda target, mappingtype, kind, alias: client.calls.append(('add', alias))
        publisher = api.DraftPublishService(client)
        with self.assertRaises(IntegrationError):
            publisher.publish(doc, journal=journal)
        with self.assertRaises(IntegrationError):
            publisher.publish(doc, journal=journal)
        self.assertEqual(len([c for c in client.calls if c[0] == 'add']), 1)

    def test_media_uploads_are_retained_in_journal_for_cleanup_diagnostics(self):
        api = self.api()
        doc = json.loads((ROOT / 'template-presets/extended-sk/2.13EPD-BWR-technical.json').read_text())
        doc['elements'] = [e for e in doc['elements'] if e['type'] == 'image']
        client, journal = Controller(), {}
        result = api.DraftPublishService(client, media_uploader=lambda *args: None).publish(doc, journal=journal)
        self.assertEqual(journal['uploaded_media'][0]['name'], next(iter(result['bindings'].values()))['static_value'])
        self.assertEqual(len(journal['uploaded_media'][0]['sha256']), 64)
        self.assertEqual(journal['uploaded_media'][0]['width'], 50)

    def test_all_thirty_documents_complete_offline_publication_without_input_changes(self):
        api = self.api()
        paths = sorted((ROOT / 'template-presets/retail-sk').glob('*.json')) + sorted((ROOT / 'template-presets/extended-sk').glob('*.json'))
        totals = {}
        for path in paths:
            doc = json.loads(path.read_text())
            original = copy.deepcopy(doc)
            plan = api.translate_native_plan(doc)
            client = Controller(plan['width'], plan['height'], plan['alignment'], plan['screen_type'])
            result = api.DraftPublishService(client, media_uploader=lambda *args: None).publish(doc)
            self.assertTrue(result['verified'])
            self.assertEqual(len(result['bindings']), len(doc['elements']))
            self.assertEqual(doc, original)
            for e in doc['elements']:
                totals[e['type']] = totals.get(e['type'], 0) + 1
        self.assertEqual(totals, {'text': 192, 'rectangle': 24, 'barcode': 6, 'qrcode': 3, 'image': 3})

    def test_rectangles_publish_as_exact_rgba_photos_with_white_text_holes(self):
        import io
        from PIL import Image
        api = self.api()
        doc = document()
        base = next(e for e in doc['elements'] if e['type'] == 'text')
        doc['elements'] = [dict(base, id='red-panel', type='rectangle', x=0, y=0,
                                width=100, height=50, text='', field='', prefix='', suffix='',
                                background='#ff0000', border_width=0),
                           dict(base, id='white-label', x=10, y=10, width=50, height=20,
                                color='#ffffff', background='transparent', border_width=0)]
        original = copy.deepcopy(doc)
        plan = api.translate_native_plan(doc)
        panel, label = plan['fields']
        self.assertEqual(panel['column_name'], 'photo')
        self.assertEqual(label['component']['style']['background-color'], '#ff0000')
        image = Image.open(io.BytesIO(panel['media']['bytes']))
        self.assertEqual(image.mode, 'RGBA')
        self.assertEqual(image.size, (100, 50))
        self.assertEqual(image.getpixel((0, 0)), (255, 0, 0, 255))
        self.assertEqual(image.getpixel((10, 10)), (0, 0, 0, 0))
        self.assertEqual(doc, original)
        uploaded = []
        result = api.DraftPublishService(Controller(), media_uploader=lambda *args: uploaded.append(args)).publish(doc)
        self.assertTrue(result['verified'])
        self.assertEqual(len(uploaded), 1)
        binding = result['bindings'][panel['alias']]
        self.assertEqual(binding['field'], '')
        self.assertEqual(binding['static_value'], uploaded[0][0])
        self.assertRegex(uploaded[0][0], r'^ESLM_[0-9a-f]{12}_\d{3}$')

    def test_qr_photo_preserves_dynamic_renderer_recipe_and_encodes_affixes(self):
        from esl_web.qr_png import qr_png
        api = self.api()
        doc = json.loads((ROOT / 'template-presets/retail-sk/2.9EPD-BWR-details.json').read_text())
        element = next(e for e in doc['elements'] if e['type'] == 'qrcode')
        doc['elements'] = [element]
        element.update(prefix='SKU:', suffix=':SK')
        original = copy.deepcopy(doc)
        plan = api.translate_native_plan(doc)
        field = plan['fields'][0]
        self.assertEqual(field['column_name'], 'photo')
        self.assertEqual(field['component']['prefix'], '')
        self.assertEqual(field['component']['suffix'], '')
        value = str(doc['sample_data'].get(element['field'], element['text']))
        self.assertEqual(field['media']['bytes'], qr_png('SKU:' + value + ':SK', element['width'], element['height'], 'M'))
        binding = plan['bindings'][field['alias']]
        self.assertEqual(binding['field'], element['field'])
        self.assertEqual(binding['renderer'], dict(type='qrcode', width=element['width'], height=element['height'],
                                                 error_correction='M', prefix='SKU:', suffix=':SK'))
        self.assertEqual(binding['static_value'], field['media']['name'])
        self.assertEqual(doc, original)
        client = Controller(plan['width'], plan['height'], plan['alignment'], plan['screen_type'])
        published = api.DraftPublishService(client, media_uploader=lambda *args: None).publish(doc)
        self.assertEqual(published['bindings'][field['alias']], binding)
        self.assertEqual(client.layout[0]['type'], 'photo')
        element.update(field='', text='STATIC')
        static_plan = api.translate_native_plan(doc)
        static_field = static_plan['fields'][0]
        self.assertEqual(static_plan['bindings'][static_field['alias']]['field'], '')
        self.assertEqual(static_plan['bindings'][static_field['alias']]['static_value'], static_field['media']['name'])
        result = api.DraftPublishService(Controller(width=static_plan['width'], height=static_plan['height'],
                                                   alignment=static_plan['alignment'], screen_type=static_plan['screen_type']),
                                         media_uploader=lambda *args: None).publish(doc)
        self.assertTrue(result['verified'])

    def test_non_m_qr_correction_is_rejected_before_vendor_mutation(self):
        from esl_web.drafts import DraftService
        api = self.api()
        for correction in ('L', 'Q', 'H'):
            for dynamic in (False, True):
                with self.subTest(correction=correction, dynamic=dynamic):
                    doc = json.loads((ROOT / 'template-presets/retail-sk/2.9EPD-BWR-details.json').read_text())
                    element = next(e for e in doc['elements'] if e['type'] == 'qrcode')
                    doc['elements'] = [element]
                    element['error_correction'] = correction
                    if not dynamic:
                        element.update(field='', text='STATIC')
                    original = copy.deepcopy(doc)
                    self.assertEqual(DraftService.validate(doc), original)
                    client = Controller(width=296, height=128, alignment=2)
                    uploaded, registered, journal = [], [], {}
                    publisher = api.DraftPublishService(client,
                        media_uploader=lambda *args: uploaded.append(args), register=registered.append)
                    with self.assertRaisesRegex(ValidationError, 'QR.*ECC M'):
                        publisher.publish(doc, journal=journal)
                    self.assertEqual(client.calls, [])
                    self.assertEqual(uploaded, [])
                    self.assertEqual(registered, [])
                    self.assertEqual(journal, {})
                    with self.assertRaisesRegex(ValidationError, 'QR.*ECC M'):
                        api.translate_native_plan(doc)
                    self.assertEqual(doc, original)

    def test_successful_field_adds_reuse_layout_and_defer_alias_metadata_until_final(self):
        api = self.api()
        doc = document()
        doc['elements'] = [e for e in doc['elements'] if e['type'] == 'text'][:2]
        client = Controller()
        reads = []
        original_layout, original_detail, original_add = client.get_style_layout, client.get_style_detail, client.add_style_field
        def layout(target):
            reads.append('layout')
            return original_layout(target)
        def detail(target):
            data = original_detail(target)
            if not any(call[0] == 'save' for call in client.calls):
                data['styleFileds'] = []
            return data
        def add(*args):
            original_add(*args)
            return 1
        client.get_style_layout, client.get_style_detail, client.add_style_field = layout, detail, add
        result = api.DraftPublishService(client).publish(doc)
        self.assertTrue(result['verified'])
        self.assertEqual(len(reads), len(doc['elements']) + 2)
        self.assertEqual(len(result['bindings']), 2)

    def test_non_success_field_replies_reconcile_metadata_once_without_retry(self):
        api = self.api()
        doc = document()
        doc['elements'] = [e for e in doc['elements'] if e['type'] == 'text'][:1]
        for reply in (None, 0, '1', True):
            with self.subTest(reply=reply):
                client = Controller()
                original_add, original_detail = client.add_style_field, client.get_style_detail
                after_add_reads = []
                def add(*args):
                    original_add(*args)
                    return reply
                def detail(target):
                    data = original_detail(target)
                    if any(call[0] == 'add' for call in client.calls):
                        after_add_reads.append(target)
                        data['styleFileds'] = []
                    return data
                client.add_style_field, client.get_style_detail = add, detail
                journal = {}
                with self.assertRaisesRegex(IntegrationError, 'Field creation'):
                    api.DraftPublishService(client).publish(doc, journal=journal)
                self.assertEqual(after_add_reads, [200])
                self.assertEqual([call[0] for call in client.calls], ['create', 'add'])
                self.assertEqual(journal['status'], 'failed')

    def test_application_success_still_requires_final_authoritative_aliases(self):
        api = self.api()
        doc = document()
        doc['elements'] = [e for e in doc['elements'] if e['type'] == 'text'][:1]
        client, registered = Controller(), []
        original = client.get_style_detail
        def detail(target):
            data = original(target)
            data['styleFileds'] = []
            return data
        client.get_style_detail = detail
        with self.assertRaisesRegex(IntegrationError, 'styleFileds differ'):
            api.DraftPublishService(client, register=registered.append).publish(doc)
        self.assertEqual(registered, [])
        self.assertEqual(len([call for call in client.calls if call[0] == 'add']), 1)
        self.assertNotIn('preview', [call[0] for call in client.calls])

    def test_unrepresentable_raster_features_fail_before_any_controller_calls(self):
        api = self.api()
        for update in ({'border_width': 2}, {'italic': True},
                       {'type': 'rectangle', 'text': '', 'field': '', 'prefix': '', 'suffix': '', 'background': 'transparent'},
                       {'type': 'qrcode', 'width': 10, 'height': 10}):
            with self.subTest(update=update):
                doc = document()
                doc['elements'] = [next(e for e in doc['elements'] if e['type'] == 'text')]
                doc['elements'][0].update(update)
                client = Controller()
                with self.assertRaises(ValidationError):
                    api.DraftPublishService(client, media_uploader=lambda *args: None).publish(doc)
                self.assertEqual(client.calls, [])

    def test_controller_defaults_are_compiled_explicitly_without_mutating_source(self):
        api = self.api()
        doc = document()
        doc['elements'] = [e for e in doc['elements'] if e['type'] == 'text'][:2]
        original = copy.deepcopy(doc)
        plan = api.translate_native_plan(doc)
        for field in plan['fields']:
            self.assertEqual(field['component']['style']['board-width'], '1px')
            self.assertEqual(field['component']['style']['z-index'], 0)
        self.assertEqual(doc, original)
        self.assertTrue(any('border' in warning.lower() for warning in plan['warnings']))
        self.assertTrue(any('z-index' in warning for warning in plan['warnings']))

    def test_sample_null_and_boolean_use_local_rendering_string_semantics(self):
        api = self.api()
        doc = document()
        doc['elements'] = [next(e for e in doc['elements'] if e['type'] == 'text')]
        field = doc['elements'][0]['field']
        for value, expected in [(None, ''), (False, 'false'), (True, 'true')]:
            doc['sample_data'][field] = value
            plan = api.translate_native_plan(doc)
            self.assertEqual(plan['fields'][0]['component']['text'], expected)


if __name__ == '__main__':
    unittest.main()
