"""Publication persistence and fail-closed dispatch contracts (no hardware)."""
import copy
import hashlib
import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from esl_web.storage import Storage
from esl_web.service import Service, ValidationError, ForbiddenError, ConflictError
from esl_web.vendor import LIVE_WRITE_CONFIRMATION
from tests.test_drafts import document


class PublicationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.storage = Storage(Path(self.temp.name) / 'test.sqlite')
        self.storage.initialize()
        self.doc = document()
        self.doc['elements'][0]['field'] = 'sku'
        self.bindings = {'sku_text': {'field': 'sku', 'element_id': 'label', 'static_value': 'Hello'}}

    def publication(self):
        from esl_web.template_apply import TemplatePublicationService
        pub = TemplatePublicationService(self.storage)
        pub.initialize()
        return pub

    def test_register_readback_revisions_idempotence_and_schema_isolation(self):
        pub = self.publication()
        with self.storage.connection() as c:
            before = c.execute('PRAGMA user_version').fetchone()[0]
        first = pub.register('legacy', 30, 'draft-a', 1, self.doc, self.bindings)
        self.assertEqual(first, pub.register('legacy', 30, 'draft-a', 1, self.doc, self.bindings))
        self.assertEqual(first, self.publication().get('legacy', 30))
        self.assertEqual([first], pub.list('legacy'))
        self.assertEqual([], pub.list('other'))
        self.assertEqual(first['bindings'], self.bindings)
        expected = hashlib.sha256(json.dumps(self.doc, ensure_ascii=False, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()).hexdigest()
        self.assertEqual(expected, first['document_hash'])
        self.doc['name'] = 'New revision'
        second = pub.register('legacy', 30, 'draft-a', 2, self.doc, self.bindings)
        self.assertEqual(2, second['draft_revision'])
        self.assertEqual([second], pub.list())
        with self.assertRaises(ConflictError):
            pub.register('legacy', 30, 'draft-a', 1, self.doc, self.bindings)
        with self.storage.connection() as c:
            self.assertEqual(before, c.execute('PRAGMA user_version').fetchone()[0])
            self.assertEqual(0, c.execute('SELECT count(*) FROM tags').fetchone()[0])

    def dispatch_fixture(self):
        pub = self.publication()
        self.doc['schema_version'] = 2
        duplicate = copy.deepcopy(self.doc['elements'][0])
        duplicate.update(id='barcode', type='barcode', barcode_format='CODE128')
        self.doc['elements'].append(duplicate)
        static = copy.deepcopy(self.doc['elements'][0])
        static.update(id='literal', field='', text='Static')
        self.doc['elements'].append(static)
        image = copy.deepcopy(static)
        image.update(id='photo', type='image', text='', image_fit='contain', image_data='')
        self.doc['elements'].append(image)
        self.bindings.update(sku_barcode={'field': 'sku', 'element_id': 'barcode', 'static_value': 'demo'}, literal={'field': '', 'element_id': 'literal', 'static_value': 'Static'}, photo={'field': '', 'element_id': 'photo', 'static_value': 'native-photo.png'})
        pub.register('legacy', 30, 'draft-a', 1, self.doc, self.bindings)
        with self.storage.connection() as c:
            c.execute("INSERT INTO templates(id,controller_id,vendor_id,name,width,height,screen_type,mapping_type) VALUES ('local-template','legacy','30','Published',250,132,1,99)")
            c.execute("INSERT INTO tags(id,controller_id,vendor_id,mac,width,height,battery,rssi,status,device_model_id) VALUES ('tag-a','legacy','tag-native','AABBCCDDEEFF',250,132,100,-20,'ready','2.13TFT-BW')")
        class Client:
            def __init__(self, fields):
                self.detail = {'id': 30, 'width': 250, 'height': 132, 'type': 1, 'mappingtype': 7, 'styleFileds': fields}
                self.catalog = [dict(self.detail)]
                self.calls = []
                self.reads = []
                self.result = [{'mac': 'AABBCCDDEEFF', '_verified_status': 'updating'}]
            def get_style_detail(self, style_id):
                self.reads.append(('detail', style_id))
                return self.detail
            def get_style_catalog(self):
                self.reads.append(('catalog',))
                return self.catalog
            def update_screen(self, updates, confirmation):
                self.calls.append((updates, confirmation))
                return self.result
        client = Client(list(self.bindings))
        body = {'template_id': 'local-template', 'data': {'sku': 'SKU-1'}, 'confirmation': LIVE_WRITE_CONFIRMATION}
        return pub, client, body

    def qr_fixture(self, dynamic=True):
        pub, client, body = self.dispatch_fixture()
        qr = copy.deepcopy(self.doc['elements'][0])
        qr.update(id='qr', type='qrcode', width=100, height=100,
                  error_correction='M', prefix='https://example.test/', suffix='?ok=1',
                  field='sku' if dynamic else '')
        self.doc['elements'].append(qr)
        renderer = {key: qr[key] for key in ('type', 'width', 'height', 'error_correction', 'prefix', 'suffix')}
        self.bindings['qr_photo'] = {'field': qr['field'], 'element_id': 'qr',
                                     'static_value': 'published-qr', 'renderer': renderer}
        client.detail['styleFileds'] = list(self.bindings)
        client.catalog = [dict(client.detail)]
        client.uploads = []
        def upload(name, raw, width, height):
            client.uploads.append((name, raw, width, height))
            return {'name': name, 'width': width, 'height': height,
                    'sha256': hashlib.sha256(raw).hexdigest(), 'content_exact': True}
        client.upload_photo = upload
        return pub, client, body

    def test_dynamic_qr_uploads_exact_m_png_and_dispatches_photo_name(self):
        from esl_web.qr_png import qr_png
        pub, client, body = self.qr_fixture()
        receipt = pub.register('legacy', 30, 'draft-a', 2, self.doc, self.bindings)
        self.assertEqual(self.bindings, receipt['bindings'])
        with patch.dict(os.environ, {'ESL_LIVE_WRITES': '1'}):
            pub.apply(Service(self.storage), client, 'legacy', 'tag-a', body)
        raw = qr_png('https://example.test/SKU-1?ok=1', 100, 100, 'M')
        name, actual, width, height = client.uploads[0]
        self.assertEqual((raw, 100, 100), (actual, width, height))
        self.assertLessEqual(len(name), 32)
        self.assertIn(hashlib.sha256(raw).hexdigest()[:12], name)
        self.assertEqual(name, client.calls[0][0][0]['qr_photo'])

    def test_renderer_must_match_original_qr_and_use_exact_m(self):
        pub, client, body = self.qr_fixture()
        original = copy.deepcopy(self.bindings)
        for key, value in [('type', 'image'), ('width', 99), ('height', 99),
                           ('width', 100.0), ('error_correction', 'L'),
                           ('prefix', ''), ('suffix', ''), ('extra', 'unsafe')]:
            bindings = copy.deepcopy(original)
            bindings['qr_photo']['renderer'][key] = value
            with self.subTest(key=key, value=value), self.assertRaises(ValidationError):
                pub.register('legacy', 30, 'draft-a', 2, self.doc, bindings)
        for renderer in [None, [], {}, {'type': 'qrcode'}]:
            bindings = copy.deepcopy(original)
            bindings['qr_photo']['renderer'] = renderer
            with self.subTest(renderer=renderer), self.assertRaises(ValidationError):
                pub.register('legacy', 30, 'draft-a', 2, self.doc, bindings)
        for ecc in ['L', 'Q', 'H']:
            doc = copy.deepcopy(self.doc)
            doc['elements'][-1]['error_correction'] = ecc
            with self.subTest(ecc=ecc), self.assertRaises(ValidationError):
                pub.register('legacy', 30, 'draft-a', 2, doc, original)
        bindings = copy.deepcopy(original)
        bindings['sku_text']['renderer'] = bindings['qr_photo']['renderer']
        with self.assertRaises(ValidationError):
            pub.register('legacy', 30, 'draft-a', 2, self.doc, bindings)
        bindings = copy.deepcopy(original)
        del bindings['qr_photo']['renderer']
        with self.assertRaises(ValidationError):
            pub.register('legacy', 30, 'draft-a', 2, self.doc, bindings)
        self.assertEqual([], client.uploads)

    def test_dynamic_qr_requires_string_before_vendor_reads_or_uploads(self):
        pub, client, body = self.qr_fixture()
        pub.register('legacy', 30, 'draft-a', 2, self.doc, self.bindings)
        for value in [None, True, False, 123, 1.5]:
            with self.subTest(value=value), patch.dict(os.environ, {'ESL_LIVE_WRITES': '1'}):
                with self.assertRaises(ValidationError):
                    pub.apply(Service(self.storage), client, 'legacy', 'tag-a', dict(body, data={'sku': value}))
        self.assertEqual([], client.reads)
        self.assertEqual([], client.uploads)
        self.assertEqual([], client.calls)

    def test_static_qr_reuses_published_photo_without_render_or_upload(self):
        pub, client, body = self.qr_fixture(dynamic=False)
        pub.register('legacy', 30, 'draft-a', 2, self.doc, self.bindings)
        with patch.dict(os.environ, {'ESL_LIVE_WRITES': '1'}):
            pub.apply(Service(self.storage), client, 'legacy', 'tag-a', body)
        self.assertEqual('published-qr', client.calls[0][0][0]['qr_photo'])
        self.assertEqual([], client.uploads)
        self.bindings['qr_photo']['static_value'] = ''
        with self.assertRaises(ValidationError):
            pub.register('legacy', 30, 'draft-a', 3, self.doc, self.bindings)

    def test_registration_never_assigns_existing_tag(self):
        pub, client, body = self.dispatch_fixture()
        before = Service(self.storage).get_tag('tag-a')
        self.doc['name'] = 'Published newer'
        pub.register('legacy', 30, 'draft-a', 2, self.doc, self.bindings)
        self.assertEqual(before, Service(self.storage).get_tag('tag-a'))
        self.assertEqual([], client.calls)
        self.assertEqual([], self.audits())

    def test_qr_render_capacity_error_is_validation_error_without_vendor_writes(self):
        pub, client, body = self.qr_fixture()
        pub.register('legacy', 30, 'draft-a', 2, self.doc, self.bindings)
        with patch.dict(os.environ, {'ESL_LIVE_WRITES': '1'}), self.assertRaises(ValidationError):
            pub.apply(Service(self.storage), client, 'legacy', 'tag-a', dict(body, data={'sku': 'x' * 2000}))
        self.assertEqual([], client.uploads)
        self.assertEqual([], client.calls)

    def test_qr_upload_failure_or_unverified_receipt_never_dispatches_or_assigns(self):
        from esl_web.service import IntegrationError
        pub, client, body = self.qr_fixture()
        pub.register('legacy', 30, 'draft-a', 2, self.doc, self.bindings)
        before = Service(self.storage).get_tag('tag-a')
        for receipt in [None, {}, {'name': 'wrong', 'content_exact': True},
                        {'name': 'ESLM_wrong', 'content_exact': False}]:
            uploads = []
            def upload(name, raw, width, height):
                uploads.append(name)
                return receipt
            client.upload_photo = upload
            with self.subTest(receipt=receipt), patch.dict(os.environ, {'ESL_LIVE_WRITES': '1'}), self.assertRaises(IntegrationError):
                pub.apply(Service(self.storage), client, 'legacy', 'tag-a', body)
            self.assertEqual(1, len(uploads))
            self.assertEqual(before, Service(self.storage).get_tag('tag-a'))
        def upload(*args):
            raise RuntimeError('private endpoint')
        client.upload_photo = upload
        with patch.dict(os.environ, {'ESL_LIVE_WRITES': '1'}), self.assertRaises(IntegrationError):
            pub.apply(Service(self.storage), client, 'legacy', 'tag-a', body)
        self.assertEqual([], client.calls)
        self.assertEqual(before, Service(self.storage).get_tag('tag-a'))

    def test_tampered_renderer_is_revalidated_before_vendor_access(self):
        pub, client, body = self.qr_fixture()
        pub.register('legacy', 30, 'draft-a', 2, self.doc, self.bindings)
        self.bindings['qr_photo']['renderer']['error_correction'] = 'L'
        with self.storage.connection() as c:
            c.execute('UPDATE template_publications SET bindings=?', (json.dumps(self.bindings),))
        with patch.dict(os.environ, {'ESL_LIVE_WRITES': '1'}), self.assertRaises(ValidationError):
            pub.apply(Service(self.storage), client, 'legacy', 'tag-a', body)
        self.assertEqual([], client.reads)
        self.assertEqual([], client.uploads)
        self.assertEqual([], client.calls)

    def test_missing_binding_cannot_hide_a_required_document_field(self):
        pub = self.publication()
        with self.assertRaises(ValidationError):
            pub.register('legacy', 30, 'draft-a', 1, self.doc, {})

    def test_image_static_photo_name_must_not_be_blank(self):
        pub, client, body = self.dispatch_fixture()
        self.bindings['photo']['static_value'] = ''
        with self.assertRaises(ValidationError):
            pub.register('legacy', 30, 'draft-a', 2, self.doc, self.bindings)

    def test_bwr_dispatch_uses_native_no_flag_contract(self):
        pub, client, body = self.dispatch_fixture()
        self.doc['model_id'] = '2.13EPD-BWR'
        for element in self.doc['elements']:
            element['height'] = 122
        pub.register('legacy', 30, 'draft-a', 2, self.doc, self.bindings)
        with self.storage.connection() as c:
            c.execute("UPDATE tags SET height=122,device_model_id='2.13EPD-BWR'")
            c.execute('UPDATE templates SET height=122,screen_type=2')
        client.detail.update(height=122, type=2)
        client.catalog = [dict(client.detail)]
        with patch.dict(os.environ, {'ESL_LIVE_WRITES': '1'}):
            pub.apply(Service(self.storage), client, 'legacy', 'tag-a', body)
        self.assertNotIn('ABDisplayFlag', client.calls[0][0][0])

    def test_register_rejects_reserved_aliases_missing_static_and_wrong_source(self):
        pub = self.publication()
        invalid = [
            {'mac': self.bindings['sku_text']},
            {'sku_text': {'field': 'sku', 'element_id': 'label'}},
            {'sku_text': {'field': 'other', 'element_id': 'label', 'static_value': ''}},
            {'sku_text': {'field': 'sku', 'element_id': 'missing', 'static_value': ''}},
            {'bad alias': self.bindings['sku_text']},
            [],
        ]
        for bindings in invalid:
            with self.subTest(bindings=bindings), self.assertRaises(ValidationError):
                pub.register('legacy', 30, 'draft-a', 1, self.doc, bindings)
        self.assertEqual([], pub.list())

    def test_own_flat_lookup_never_resolves_nested_or_demo_values(self):
        pub, client, body = self.dispatch_fixture()
        self.doc['schema_version'] = 2
        for element in self.doc['elements'][:2]:
            element['field'] = 'sku.value'
        for alias in ('sku_text', 'sku_barcode'):
            self.bindings[alias]['field'] = 'sku.value'
        pub.register('legacy', 30, 'draft-a', 2, self.doc, self.bindings)
        with patch.dict(os.environ, {'ESL_LIVE_WRITES': '1'}):
            with self.assertRaises(ValidationError):
                pub.apply(Service(self.storage), client, 'legacy', 'tag-a', dict(body, data={'sku': {'value': 'nested'}}))
            pub.apply(Service(self.storage), client, 'legacy', 'tag-a', dict(body, data={'sku.value': 'flat'}))
        self.assertEqual('flat', client.calls[0][0][0]['sku_text'])

    def test_guards_and_exact_body_fail_before_any_vendor_call(self):
        pub, client, body = self.dispatch_fixture()
        for flag, confirmation in [('0', LIVE_WRITE_CONFIRMATION), ('1', ''), ('1', LIVE_WRITE_CONFIRMATION + ' ')]:
            with self.subTest(flag=flag, confirmation=confirmation), patch.dict(os.environ, {'ESL_LIVE_WRITES': flag}):
                body['confirmation'] = confirmation
                with self.assertRaises(ForbiddenError):
                    pub.apply(Service(self.storage), client, 'legacy', 'tag-a', body)
        body['confirmation'] = LIVE_WRITE_CONFIRMATION
        for extra in ['mac', 'styleid', 'mappingtype', 'updates']:
            with self.subTest(extra=extra), patch.dict(os.environ, {'ESL_LIVE_WRITES': '1'}):
                with self.assertRaises(ValidationError):
                    pub.apply(Service(self.storage), client, 'legacy', 'tag-a', dict(body, **{extra: 'unsafe'}))
        self.assertEqual([], client.reads)
        self.assertEqual([], client.calls)

    def test_missing_demo_unknown_nested_oversize_and_unsafe_numeric_data_never_dispatch(self):
        pub, client, body = self.dispatch_fixture()
        for data in [{}, {'sku': 'ok', 'extra': 'no'}, {'sku': {}}, {'sku': []}, {'sku': 'x' * 2001}, {'sku': 9007199254740992}, {'sku': float('nan')}, {'sku': float('inf')}]:
            with self.subTest(data=repr(data)[:60]), patch.dict(os.environ, {'ESL_LIVE_WRITES': '1'}):
                with self.assertRaises(ValidationError):
                    pub.apply(Service(self.storage), client, 'legacy', 'tag-a', dict(body, data=data))
        self.assertEqual([], client.calls)

    def test_wrong_scope_model_publication_and_native_mapping_never_dispatch(self):
        from esl_web.service import ServiceError
        pub, client, body = self.dispatch_fixture()
        cases = [
            ("UPDATE tags SET controller_id='other'", None),
            ("UPDATE templates SET controller_id='other'", None),
            ("UPDATE templates SET screen_type=2", None),
            ("UPDATE templates SET vendor_id='31'", None),
            (None, ('type', 2)), (None, ('width', 296)),
            (None, ('mappingtype', None)), (None, ('styleFileds', ['unexpected'])),
            (None, ('id', 31)),
        ]
        with self.storage.connection() as c:
            c.execute("INSERT INTO controllers(id,name,is_default) VALUES ('other','Other',0)")
        for sql, change in cases:
            with self.subTest(sql=sql, change=change):
                with self.storage.connection() as c:
                    if sql:
                        c.execute(sql)
                original = copy.deepcopy(client.detail)
                if change:
                    client.detail[change[0]] = change[1]
                with patch.dict(os.environ, {'ESL_LIVE_WRITES': '1'}), self.assertRaises(ServiceError):
                    pub.apply(Service(self.storage), client, 'legacy', 'tag-a', body)
                client.detail = original
                with self.storage.connection() as c:
                    c.execute("UPDATE tags SET controller_id='legacy'")
                    c.execute("UPDATE templates SET controller_id='legacy',screen_type=1,vendor_id='30'")
        client.catalog[0]['type'] = 2
        with patch.dict(os.environ, {'ESL_LIVE_WRITES': '1'}), self.assertRaises(ServiceError):
            pub.apply(Service(self.storage), client, 'legacy', 'tag-a', body)
        self.assertEqual([], client.calls)

    def test_unverified_dispatch_response_is_not_reported_as_success(self):
        from esl_web.service import IntegrationError
        pub, client, body = self.dispatch_fixture()
        for response in [[], [{'mac': 'different', '_verified_status': 'success'}], [{'mac': 'AABBCCDDEEFF'}], [{'mac': 'AABBCCDDEEFF', '_verified_status': 'ready'}]]:
            client.result = response
            with patch.dict(os.environ, {'ESL_LIVE_WRITES': '1'}), self.assertRaises(IntegrationError):
                pub.apply(Service(self.storage), client, 'legacy', 'tag-a', body)

    def audits(self):
        with self.storage.connection() as c:
            return [dict(row, details=json.loads(row['details'])) for row in
                    c.execute("SELECT * FROM audit_events WHERE entity_id='tag-a' ORDER BY id")]

    def test_verified_apply_audits_before_write_and_persists_only_selected_config(self):
        pub, client, body = self.dispatch_fixture()
        with self.storage.connection() as c:
            c.execute("UPDATE tags SET label='Keep label',test_data=?,configuration_source='vendor',show_style='keep'",
                      (json.dumps({'old': 'not a fallback'}),))
            before = dict(c.execute("SELECT * FROM tags WHERE id='tag-a'").fetchone())
        original = client.update_screen
        def update(updates, confirmation):
            audits = self.audits()
            self.assertEqual(['template.apply.attempted'], [row['action'] for row in audits])
            with self.storage.connection() as c:
                self.assertIsNone(c.execute("SELECT template_id FROM tags WHERE id='tag-a'").fetchone()[0])
            return original(updates, confirmation)
        client.update_screen = update
        with patch.dict(os.environ, {'ESL_LIVE_WRITES': '1'}):
            pub.apply(Service(self.storage), client, 'legacy', 'tag-a', body)
        with self.storage.connection() as c:
            after = dict(c.execute("SELECT * FROM tags WHERE id='tag-a'").fetchone())
        expected = dict(before, template_id='local-template', test_data=json.dumps(body['data'], sort_keys=True, separators=(',', ':')), status='updating', configuration_source='local')
        self.assertEqual(expected, after)
        audits = self.audits()
        self.assertEqual(['template.apply.attempted', 'template.apply.verified'], [row['action'] for row in audits])
        self.assertEqual('updating', audits[-1]['details']['status'])
        self.assertEqual(audits[0]['details']['attempt_id'], audits[1]['details']['attempt_id'])

    def test_failed_or_unknown_update_has_durable_sanitized_audit_and_no_assignment_or_retry(self):
        from esl_web.service import IntegrationError
        pub, client, body = self.dispatch_fixture()
        before = Service(self.storage).get_tag('tag-a')
        attempts = []
        def update(updates, confirmation):
            attempts.append(updates)
            self.assertEqual('template.apply.attempted', self.audits()[-1]['action'])
            raise RuntimeError('secret-token https://vendor/password')
        client.update_screen = update
        with patch.dict(os.environ, {'ESL_LIVE_WRITES': '1'}), self.assertRaises(IntegrationError):
            pub.apply(Service(self.storage), client, 'legacy', 'tag-a', body)
        self.assertEqual(1, len(attempts))
        self.assertEqual(before, Service(self.storage).get_tag('tag-a'))
        audits = self.audits()
        self.assertEqual(['template.apply.attempted', 'template.apply.failed'], [row['action'] for row in audits])
        self.assertEqual('RuntimeError', audits[-1]['details']['error_type'])
        self.assertNotIn('secret-token', json.dumps(audits))
        self.assertNotIn('password', json.dumps(audits))
        client.update_screen = lambda updates, confirmation: []
        with patch.dict(os.environ, {'ESL_LIVE_WRITES': '1'}), self.assertRaises(IntegrationError):
            pub.apply(Service(self.storage), client, 'legacy', 'tag-a', body)
        self.assertEqual(before, Service(self.storage).get_tag('tag-a'))
        self.assertEqual('template.apply.failed', self.audits()[-1]['action'])
        self.assertEqual('IntegrationError', self.audits()[-1]['details']['error_type'])

    def test_staged_tag_is_rejected_before_any_vendor_access(self):
        pub, client, body = self.dispatch_fixture()
        with self.storage.connection() as c:
            c.execute("UPDATE tags SET inventory_source='local'")
        with patch.dict(os.environ, {'ESL_LIVE_WRITES': '1'}), self.assertRaises(ValidationError):
            pub.apply(Service(self.storage), client, 'legacy', 'tag-a', body)
        self.assertEqual([], client.reads)
        self.assertEqual([], client.calls)
        self.assertEqual([], self.audits())

    def test_attempt_audit_failure_blocks_vendor_write(self):
        pub, client, body = self.dispatch_fixture()
        with self.storage.connection() as c:
            c.execute("CREATE TRIGGER block_attempt BEFORE INSERT ON audit_events "
                      "WHEN NEW.action='template.apply.attempted' BEGIN SELECT RAISE(ABORT, 'audit unavailable'); END")
        with patch.dict(os.environ, {'ESL_LIVE_WRITES': '1'}), self.assertRaises(Exception):
            pub.apply(Service(self.storage), client, 'legacy', 'tag-a', body)
        self.assertEqual([], client.calls)
        self.assertIsNone(Service(self.storage).get_tag('tag-a')['template_id'])

    def test_verified_success_persists_explicit_data_and_success_status(self):
        pub, client, body = self.dispatch_fixture()
        client.result[0]['_verified_status'] = 'success'
        body['data'] = {'sku': None}
        with patch.dict(os.environ, {'ESL_LIVE_WRITES': '1'}):
            pub.apply(Service(self.storage), client, 'legacy', 'tag-a', body)
        tag = Service(self.storage).get_tag('tag-a')
        self.assertEqual('success', tag['status'])
        self.assertEqual('local-template', tag['template_id'])
        self.assertEqual({'sku': None}, tag['test_data'])
        self.assertEqual('success', self.audits()[-1]['details']['status'])

    def test_uploads_respect_auth_and_model_guards_before_side_effects(self):
        from esl_web.service import IntegrationError
        pub, client, body = self.qr_fixture()
        pub.register('legacy', 30, 'draft-a', 2, self.doc, self.bindings)
        with patch.dict(os.environ, {'ESL_LIVE_WRITES': '0'}), self.assertRaises(ForbiddenError):
            pub.apply(Service(self.storage), client, 'legacy', 'tag-a', body)
        client.detail['type'] = 2
        with patch.dict(os.environ, {'ESL_LIVE_WRITES': '1'}), self.assertRaises(IntegrationError):
            pub.apply(Service(self.storage), client, 'legacy', 'tag-a', body)
        self.assertEqual([], client.uploads)
        self.assertEqual([], client.calls)
        self.assertEqual([], self.audits())
        client.detail['type'] = 1
        original = client.upload_photo
        def upload(*args):
            receipt = original(*args)
            os.environ['ESL_LIVE_WRITES'] = '0'
            return receipt
        client.upload_photo = upload
        with patch.dict(os.environ, {'ESL_LIVE_WRITES': '1'}), self.assertRaises(IntegrationError):
            pub.apply(Service(self.storage), client, 'legacy', 'tag-a', body)
        self.assertEqual([], client.calls)
        self.assertIsNone(Service(self.storage).get_tag('tag-a')['template_id'])
        self.assertEqual('ForbiddenError', self.audits()[-1]['details']['error_type'])

    def test_apply_uses_verified_ids_aliases_static_photo_and_status_with_assignment(self):
        pub, client, body = self.dispatch_fixture()
        with patch.dict(os.environ, {'ESL_LIVE_WRITES': '1'}):
            result = pub.apply(Service(self.storage), client, 'legacy', 'tag-a', body)
        payload = client.calls[0][0][0]
        self.assertEqual({'mac': 'AABBCCDDEEFF', 'styleid': 30, 'mappingtype': 7, 'sku_text': 'SKU-1', 'sku_barcode': 'SKU-1', 'literal': 'Static', 'photo': 'native-photo.png'}, payload)
        self.assertEqual('updating', result['verified_tags'][0]['status'])
        self.assertEqual('draft-a', result['provenance']['draft_id'])
        self.assertNotIn('physical_success', result)
        with self.storage.connection() as c:
            self.assertEqual('local-template', c.execute("SELECT template_id FROM tags WHERE id='tag-a'").fetchone()[0])


if __name__ == '__main__':
    unittest.main()
