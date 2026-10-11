"""Offline canonical identity regressions using native transmission detail."""
import json
import os
import unittest
from unittest.mock import patch

from esl_web.vendor import (
    LIVE_WRITE_CONFIRMATION, LiveWritesDisabled, VendorClient, VendorConfig, VendorError,
)


class DispatchIdentityTests(unittest.TestCase):
    def setUp(self):
        self.client = VendorClient(VendorConfig(base_url='http://192.0.2.1/esls_new'))
        self.updates = [{'mac': '92.80.88.48', 'styleid': 136, 'mappingtype': 101,
                         'ABDisplayFlag': 163, 'Price': '9.99'}]
        self.environment = patch.dict(os.environ, {'ESL_LIVE_WRITES': '1'}, clear=True)
        self.environment.start()
        self.addCleanup(self.environment.stop)
        self.transport = patch.object(self.client, '_request', side_effect=AssertionError('network forbidden'))
        self.request = self.transport.start()
        self.addCleanup(self.transport.stop)
        self.inventory = patch.object(self.client, 'get_tags', side_effect=AssertionError('network forbidden'))
        self.tags = self.inventory.start()
        self.addCleanup(self.inventory.stop)
        self.details = patch.object(self.client, '_request_document', side_effect=AssertionError('network forbidden'))
        self.detail = self.details.start()
        self.addCleanup(self.details.stop)

    def snapshot(self, status, mac: str | int = 1548769328, timestamp=1000, tag_id=8):
        return {'tag': {'id': tag_id, 'mac': mac, 'width': 250, 'height': 122,
                        'styleid': 98, 'updateProgress': 5,
                        'tagAndGood': {'status': status, 'timestamp': timestamp}}}

    def normal_inventory(self):
        self.tags.side_effect = None
        self.tags.return_value = [{'id': 8, 'mac': '1548769328', 'updateProgress': '5'}]
        self.detail.side_effect = [self.snapshot(1), self.snapshot(4, timestamp=2000)]
        self.request.side_effect = None
        self.request.return_value = True

    def dispatch(self):
        return self.client.update_screen(self.updates, LIVE_WRITE_CONFIRMATION)

    def test_dotted_request_matches_decimal_inventory_and_preserves_array_wire_contract(self):
        self.normal_inventory()
        original = [dict(item) for item in self.updates]
        result = self.dispatch()
        self.assertEqual(result[0]['mac'], '92.80.88.48')
        self.assertEqual(result[0]['_verified_status'], 'success')
        self.assertEqual(result[0]['native_update_progress'], 4)
        self.assertEqual(result[0]['update_progress'], 5)
        self.assertEqual(self.updates, original)
        expected = [{k: v for k, v in item.items() if k != 'ABDisplayFlag'} for item in original]
        self.request.assert_called_once_with(
            'POST', '/associate/updateScreen',
            json.dumps(expected, ensure_ascii=False, separators=(',', ':')).encode(), 'application/json')
        self.assertEqual(self.tags.call_count, 2)
        self.assertEqual(self.detail.call_count, 2)

    def test_duplicate_canonical_requested_identity_is_rejected_before_inventory(self):
        self.updates.append({**self.updates[0], 'mac': '1548769328'})
        with self.assertRaisesRegex(VendorError, '[Dd]uplicate'):
            self.dispatch()
        self.tags.assert_not_called()
        self.request.assert_not_called()

    def test_canonical_duplicates_in_each_inventory_fail_closed(self):
        duplicate = [{'id': 8, 'mac': '1548769328'}, {'id': 9, 'mac': '92.80.88.48'}]
        for phase in ('preflight', 'read-back'):
            with self.subTest(phase=phase):
                self.normal_inventory()
                self.request.reset_mock()
                self.tags.side_effect = ([duplicate] if phase == 'preflight' else
                                        [[{'id': 8, 'mac': '1548769328'}], duplicate])
                with self.assertRaisesRegex(VendorError, 'identity'):
                    self.dispatch()
                self.assertEqual(self.request.call_count, 0 if phase == 'preflight' else 1)

    def test_readback_identity_representation_can_change_without_changing_target(self):
        self.normal_inventory()
        self.tags.side_effect = [[{'id': 8, 'mac': 1548769328}],
                                 [{'id': 8, 'mac': '092.080.088.048'}, {'id': 9, 'mac': '92.80.88.49'}]]
        self.detail.side_effect = [self.snapshot(0), self.snapshot(2, '092.080.088.048', timestamp=2000)]
        self.assertEqual(self.dispatch()[0]['_verified_status'], 'updating')
        self.request.assert_called_once()

    def test_other_target_cannot_satisfy_preflight_or_readback(self):
        for phase in ('preflight', 'read-back'):
            with self.subTest(phase=phase):
                self.normal_inventory()
                self.request.reset_mock()
                other = [{'id': 9, 'mac': '1548769329'}]
                self.tags.side_effect = ([other] if phase == 'preflight' else
                                        [[{'id': 8, 'mac': '1548769328'}], other])
                with self.assertRaisesRegex(VendorError, 'find the requested tag'):
                    self.dispatch()
                self.assertEqual(self.request.call_count, 0 if phase == 'preflight' else 1)

    def test_detail_id_or_mac_mismatch_cannot_verify_transmission(self):
        for after in (self.snapshot(4, mac=1548769329), self.snapshot(4, tag_id=9)):
            self.normal_inventory()
            self.request.reset_mock()
            self.detail.side_effect = [self.snapshot(1), after]
            with self.assertRaisesRegex(VendorError, 'identity differs'):
                self.dispatch()
            self.request.assert_called_once()

    def test_stale_updating_and_success_are_rejected_after_one_post(self):
        for status in (2, 4):
            with self.subTest(status=status):
                self.normal_inventory()
                self.request.reset_mock()
                self.detail.side_effect = [self.snapshot(status), self.snapshot(status)]
                with self.assertRaisesRegex(VendorError, 'already-updating' if status == 2 else 'did not confirm'):
                    self.dispatch()
                self.assertEqual(self.request.call_count, 0 if status == 2 else 1)

    def test_process_and_exact_confirmation_are_both_required_before_any_io(self):
        for flag, confirmation in (('0', LIVE_WRITE_CONFIRMATION), ('true', LIVE_WRITE_CONFIRMATION),
                                   ('1', 'wrong'), ('1', LIVE_WRITE_CONFIRMATION + ' ')):
            with self.subTest(flag=flag), patch.dict(os.environ, {'ESL_LIVE_WRITES': flag}, clear=True):
                with self.assertRaises(LiveWritesDisabled):
                    self.client.update_screen(self.updates, confirmation)
        self.tags.assert_not_called()
        self.request.assert_not_called()
        self.detail.assert_not_called()

    def test_ambiguous_post_failure_is_not_retried(self):
        self.normal_inventory()
        self.request.side_effect = VendorError('ambiguous transport failure')
        with self.assertRaisesRegex(VendorError, 'ambiguous transport failure'):
            self.dispatch()
        self.request.assert_called_once()
        self.assertEqual(self.tags.call_count, 1)
        self.assertEqual(self.detail.call_count, 1)

    def test_invalid_requested_and_inventory_identities_do_not_dispatch(self):
        for bad in (True, None, '4294967296', '92.80.88.256', 'not-a-tag'):
            for source in ('request', 'inventory'):
                with self.subTest(bad=bad, source=source):
                    self.updates[0]['mac'] = bad if source == 'request' else '92.80.88.48'
                    self.tags.side_effect = None
                    self.tags.return_value = [{'id': 8, 'mac': bad if source == 'inventory' else '1548769328'}]
                    with self.assertRaises(VendorError):
                        self.dispatch()
        self.request.assert_not_called()
        self.detail.assert_not_called()


if __name__ == '__main__':
    unittest.main()
