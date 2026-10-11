from unittest.mock import Mock, patch
from test_draft_api import DraftApiTests

class PublicationApiTests(DraftApiTests):
    def test_publication_list_has_no_vendor_side_effect(self):
        status, _, value = self.request('GET', '/api/template-publications')
        self.assertEqual(status, 200)
        self.assertEqual(value, {'items': []})
        self.assertEqual(self.vendor.mock_calls, [])
        self.assertEqual(self.request('GET', '/api/template-publications?unexpected=x')[0], 400)

    def test_template_scope_cannot_bypass_single_tag_guard(self):
        from run_live import TemplatePublishClient
        self.login()
        self.server.vendor_client = TemplatePublishClient(self.vendor, allow_confirmed_dispatch=True)
        with patch.dict('os.environ', {'ESL_LIVE_WRITES':'1'}):
            status, _, _ = self.request('POST', '/api/dispatch/live', {
                'confirmation':'I CONFIRM LIVE ESL UPDATE', 'updates':[{'mac':'AABBCC'}]})
        self.assertEqual(status, 403)
        self.assertEqual(self.vendor.mock_calls, [])
        with patch.dict('os.environ', {'ESL_LIVE_WRITES':'1'}):
            value = self.request('GET','/api/health')[2]
            assert isinstance(value, dict)
            self.assertEqual(value['mode'], 'live_enabled')

    def test_apply_requires_session_and_confirmation(self):
        route = '/api/tags/missing/apply-template'
        body = {'template_id':'x','data':{},'confirmation':'WRONG'}
        self.assertEqual(self.request('POST',route,body)[0],401)
        self.login()
        with patch.dict('os.environ', {'ESL_LIVE_WRITES':'1'}):
            self.assertEqual(self.request('POST',route,body)[0],403)
        self.assertEqual(self.vendor.mock_calls, [])
