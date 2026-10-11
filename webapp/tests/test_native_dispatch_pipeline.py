"""Offline native transmission regressions, independent of stale MMS assignment."""
import copy
import json
import os
import unittest
from unittest.mock import patch

from esl_web.vendor import VendorClient, VendorConfig, VendorError, LIVE_WRITE_CONFIRMATION


class NativeDispatchPipelineTests(unittest.TestCase):
    def setUp(self):
        self.client = VendorClient(VendorConfig(base_url='http://192.0.2.1/esls_new'))
        self.updates = [{'mac': '92.81.10.37', 'styleid': 175, 'mappingtype': 7,
                         'description': 'Čaj 中文 😀 "quoted" \\ newline\n'}]
        self.environment = patch.dict(os.environ, {'ESL_LIVE_WRITES': '1'})
        self.environment.start()
        self.addCleanup(self.environment.stop)

    def detail(self, status, timestamp):
        return {'mac': '92.81.10.37', 'native_update_progress': status,
                'native_updated_at_ms': timestamp, 'style_id': 98,
                'update_progress': 5, 'updated_at_ms': 1791657431000,
                'physical_screen_verified': False}

    def dispatch(self, before, after):
        with patch.object(self.client, 'get_tag_display', side_effect=[before, after]) as read, patch.object(self.client, '_request', return_value=True) as request, patch.object(self.client, 'get_tags', side_effect=AssertionError('MMS is not transmission evidence')):
            result = self.client.update_screen(self.updates, LIVE_WRITE_CONFIRMATION)
        self.assertEqual(read.call_args_list[0].args, ('92.81.10.37',))
        self.assertEqual(read.call_count, 2)
        request.assert_called_once()
        return result, request.call_args

    def test_legacy_flag_is_omitted_without_mutating_callers_payload(self):
        self.updates[0]['ABDisplayFlag'] = True
        original = copy.deepcopy(self.updates)
        _, call = self.dispatch(self.detail(1, 1000), self.detail(4, 2000))
        self.assertNotIn('ABDisplayFlag', json.loads(call.args[2])[0])
        self.assertEqual(self.updates, original)

    def test_native_transition_verifies_even_when_mms_assignment_remains_stale(self):
        original = copy.deepcopy(self.updates)
        result, call = self.dispatch(self.detail(1, 1791657000000), self.detail(4, 1791657409000))
        self.assertEqual(result[0]['_verified_status'], 'success')
        self.assertEqual(result[0]['style_id'], 98)
        self.assertEqual(result[0]['native_updated_at_ms'], 1791657409000)
        self.assertEqual(call.args[:2], ('POST', '/associate/updateScreen'))
        self.assertEqual(json.loads(call.args[2]), original)
        self.assertEqual(call.args[3], 'application/json')
        self.assertEqual(self.updates, original)

    def test_status_transition_without_fresh_timestamp_never_verifies(self):
        for timestamp in (1000, None):
            with self.subTest(timestamp=timestamp), patch.object(self.client, 'get_tag_display', side_effect=[self.detail(1, 1000), self.detail(4, timestamp)]), patch.object(self.client, '_request', return_value=True) as request:
                with self.assertRaises(VendorError):
                    self.client.update_screen(self.updates, LIVE_WRITE_CONFIRMATION)
                request.assert_called_once()

    def test_updating_or_missing_invalid_timestamp_preflight_blocks_post(self):
        before_states = [self.detail(2, 1000)] + [self.detail(1, value) for value in
                         (None, True, -1, '1000', 1.5, 8640000000000001)]
        for before in before_states:
            with self.subTest(before=before), patch.object(self.client, 'get_tag_display', return_value=before), patch.object(self.client, '_request', return_value=True) as request:
                with self.assertRaises(VendorError):
                    self.client.update_screen(self.updates, LIVE_WRITE_CONFIRMATION)
                request.assert_not_called()

    def test_same_native_success_requires_new_transmission_timestamp(self):
        result, _ = self.dispatch(self.detail(4, 1000), self.detail(4, 2000))
        self.assertEqual(result[0]['_verified_status'], 'success')

    def test_stale_missing_failed_or_wrong_target_native_evidence_never_verifies(self):
        for after in [self.detail(4, 1000), self.detail(4, 999), self.detail(None, None),
                      self.detail(3, 2000), dict(self.detail(4, 2000), mac='92.81.10.38')]:
            with self.subTest(after=after), patch.object(self.client, 'get_tag_display', side_effect=[self.detail(4, 1000), after]), patch.object(self.client, '_request', return_value=True) as request:
                with self.assertRaises(VendorError):
                    self.client.update_screen(self.updates, LIVE_WRITE_CONFIRMATION)
                request.assert_called_once()


class NativeDisplayFieldsTests(unittest.TestCase):
    def setUp(self):
        self.client = VendorClient(VendorConfig(base_url='http://192.0.2.1/esls_new'))
        self.tag = {'id': 8, 'mac': 1548769328, 'width': 250, 'height': 122,
                    'styleid': 98, 'updateProgress': 5, 'updatetime': 1791657431000,
                    'tagAndGood': {'status': 4, 'timestamp': 1791657409000}}

    def display(self, tag):
        with patch.object(self.client, 'get_tags', return_value=[{'id': 8, 'mac': '1548769328'}]), patch.object(self.client, '_request_document', return_value={'tag': tag}):
            return self.client.get_tag_display('92.80.88.48')

    def test_additive_native_fields_do_not_replace_legacy_fields(self):
        result = self.display(self.tag)
        self.assertEqual((result['style_id'], result['update_progress'], result['updated_at_ms']),
                         (98, 5, 1791657431000))
        self.assertEqual((result['native_update_progress'], result['native_updated_at_ms']),
                         (4, 1791657409000))
        self.assertEqual(result['native_update_source'], 'tag.tagAndGood')
        self.assertFalse(result['physical_screen_verified'])

    def test_absent_native_fields_never_fall_back_to_legacy_metadata(self):
        tag = dict(self.tag)
        tag.pop('tagAndGood')
        result = self.display(tag)
        self.assertIsNone(result['native_update_progress'])
        self.assertIsNone(result['native_updated_at_ms'])

    def test_invalid_native_timestamp_fails_closed(self):
        for timestamp in (True, -1, '1791657409000', 1.5, 8640000000000001):
            with self.subTest(timestamp=timestamp), self.assertRaises(VendorError):
                self.display(dict(self.tag, tagAndGood={'status': 4, 'timestamp': timestamp}))

    def test_detail_identity_is_validated_before_native_fields_are_exposed(self):
        with self.assertRaises(VendorError):
            self.display(dict(self.tag, mac=1548769329))


class NativeApplicationContractTests(unittest.TestCase):
    def fixture(self):
        from tests.test_template_apply import PublicationTests
        fixture = PublicationTests('runTest')
        fixture.setUp()
        self.addCleanup(fixture.doCleanups)
        pub, client, body = fixture.dispatch_fixture()
        return fixture, pub, client, body

    def test_publication_dispatch_omits_legacy_display_flag(self):
        from esl_web.service import Service
        fixture, pub, client, body = self.fixture()
        with patch.dict(os.environ, {'ESL_LIVE_WRITES': '1'}):
            pub.apply(Service(fixture.storage), client, 'legacy', 'tag-a', body)
        self.assertNotIn('ABDisplayFlag', client.calls[0][0][0])

    def test_raw_dispatch_accepts_modern_no_flag_array(self):
        from esl_web.service import Service
        fixture, _, client, _ = self.fixture()
        update = {'mac': 'AABBCCDDEEFF', 'styleid': 30, 'mappingtype': 7, 'sku': 'SKU-1'}
        with patch.dict(os.environ, {'ESL_LIVE_WRITES': '1'}):
            result = Service(fixture.storage).dispatch_live(client, {
                'confirmation': LIVE_WRITE_CONFIRMATION, 'updates': [update]})
        self.assertEqual(result['dispatched'], 1)
        self.assertEqual(client.calls[0][0], [update])


if __name__ == '__main__':
    unittest.main()
