"""Template-only launcher cannot enable vendor writes or other inventory reads."""
import os
import unittest
from unittest.mock import Mock, call, patch

import run_live
from esl_web import vendor
from esl_web.service import ForbiddenError


class TemplateReadOnlyLauncherTests(unittest.TestCase):
    def test_only_template_and_image_read_methods_are_exposed(self):
        upstream = Mock()
        client = run_live.TemplateReadOnlyClient(upstream)
        for method in ('get_style_catalog', 'get_style_detail', 'get_style_layout',
                       'get_photos', 'get_photo_data'):
            with self.subTest(method=method):
                getattr(client, method)('fixture')
                getattr(upstream, method).assert_called_once_with('fixture')
        before = list(upstream.mock_calls)
        for method in ('get_tags', 'get_routers', 'get_snapshot', 'update_screen',
                       'clone_template', 'create_template', 'upload_photo',
                       'update_template_layout', 'delete_template', '_request_document',
                       'login', 'anything_else'):
            with self.subTest(method=method), self.assertRaises(ForbiddenError):
                getattr(client, method)
        self.assertEqual(upstream.mock_calls, before)

    def test_templates_only_overrides_enabled_settings_and_process_flag(self):
        settings = {'live_writes': True, 'api_token': 'A' * 64,
                    'base_url': 'http://controller.invalid/esls_new',
                    'username': 'fixture', 'password': 'fixture'}
        server = Mock()
        with patch.object(run_live, 'load_settings', return_value=settings), \
             patch.object(run_live, 'create_server', return_value=server) as create, \
             patch.dict(os.environ, {'ESL_LIVE_WRITES': '1'}):
            run_live.main(['--templates-only'])
            self.assertEqual(os.environ['ESL_LIVE_WRITES'], '0')
            kwargs = create.call_args.kwargs
            self.assertFalse(kwargs['seed'])
            self.assertEqual(kwargs['api_token'], 'A' * 64)
            self.assertIsInstance(kwargs['controller_registry'].get(), run_live.TemplateReadOnlyClient)
            with self.assertRaises(ForbiddenError):
                kwargs['controller_registry'].get().get_tags
            server.serve_forever.assert_called_once()
        self.assertTrue(settings['live_writes'], 'secret settings file/dict must not be rewritten')

    def test_publish_capability_is_an_explicit_narrow_whitelist(self):
        upstream = Mock()
        client = run_live.TemplatePublishClient(upstream)
        allowed = ('get_style_catalog', 'get_style_detail', 'get_style_layout',
                   'get_style_data', 'get_template_preview', 'get_photos', 'get_photo_data',
                   'create_style', 'add_style_field', 'rename_style', 'save_style_layout',
                   'upload_photo')
        for method in allowed:
            getattr(client, method)('fixture')
            getattr(upstream, method).assert_called_once_with('fixture')
        before = list(upstream.mock_calls)
        for method in ('get_tags', 'get_routers', 'get_templates', 'get_snapshot',
                       'get_extended_tags', 'update_screen', 'delete_style',
                       'delete_template', 'clone_template', 'login', '_request_document',
                       'create_template', 'update_template_layout', 'anything_else'):
            with self.subTest(method=method), self.assertRaises(ForbiddenError):
                getattr(client, method)
        self.assertEqual(upstream.mock_calls, before)

    def test_dispatch_opt_in_adds_only_tag_reads_and_confirmed_screen_updates(self):
        upstream = Mock()
        client = run_live.TemplatePublishClient(upstream, allow_confirmed_dispatch=True)
        self.assertIs(client.get_tags(), upstream.get_tags.return_value)
        updates = [{'mac': 'fixture'}]
        with patch.dict(os.environ, {'ESL_LIVE_WRITES': '1'}):
            self.assertIs(client.update_screen(updates, vendor.LIVE_WRITE_CONFIRMATION),
                          upstream.update_screen.return_value)
        upstream.update_screen.assert_called_once_with(updates, vendor.LIVE_WRITE_CONFIRMATION)
        before = list(upstream.mock_calls)
        forbidden = ('get_routers', 'get_templates', 'get_snapshot', 'get_extended_tags',
                     'delete_style', 'delete_template', 'delete_photo', 'delete_tag',
                     'create_tag', 'update_tag', 'bind_tag', 'unbind_tag',
                     'clone_template', 'create_template', 'update_template_layout',
                     'login', '_request', '_request_document', 'anything_else')
        for method in forbidden:
            with self.subTest(method=method), self.assertRaises(ForbiddenError):
                getattr(client, method)
        self.assertEqual(upstream.mock_calls, before)

    def test_dispatch_guard_rejects_invalid_confirmation_before_any_upstream_call(self):
        for confirmation in ('', None, True, 'I CONFIRM',
                             vendor.LIVE_WRITE_CONFIRMATION + ' ',
                             vendor.LIVE_WRITE_CONFIRMATION.lower()):
            with self.subTest(confirmation=confirmation), \
                 patch.dict(os.environ, {'ESL_LIVE_WRITES': '1'}):
                upstream = Mock()
                client = run_live.TemplatePublishClient(upstream, allow_confirmed_dispatch=True)
                with self.assertRaises(ForbiddenError):
                    client.update_screen([], confirmation=confirmation)
                self.assertEqual(upstream.mock_calls, [])

    def test_dispatch_guard_rechecks_environment_at_call_time(self):
        upstream = Mock()
        client = run_live.TemplatePublishClient(upstream, allow_confirmed_dispatch=True)
        with patch.dict(os.environ, {'ESL_LIVE_WRITES': '1'}):
            dispatch = client.update_screen
            os.environ['ESL_LIVE_WRITES'] = '0'
            with self.assertRaises(ForbiddenError):
                dispatch([], vendor.LIVE_WRITE_CONFIRMATION)
        self.assertEqual(upstream.mock_calls, [])

    def test_real_vendor_checks_authorization_again_after_wrapper(self):
        upstream = vendor.VendorClient.__new__(vendor.VendorClient)
        client = run_live.TemplatePublishClient(upstream, allow_confirmed_dispatch=True)
        with patch.object(vendor, 'live_writes_authorized', side_effect=[True, False]) as authorize, \
             patch.object(upstream, 'get_tags') as tags, \
             patch.object(upstream, '_request') as request:
            with self.assertRaises(vendor.LiveWritesDisabled):
                client.update_screen([], vendor.LIVE_WRITE_CONFIRMATION)
        self.assertEqual(authorize.call_args_list,
                         [call(vendor.LIVE_WRITE_CONFIRMATION)] * 2)
        tags.assert_not_called()
        request.assert_not_called()

    def test_publish_mode_forces_physical_writes_off(self):
        settings = {'live_writes': True, 'api_token': 'A' * 64,
                    'base_url': 'http://controller.invalid/esls_new',
                    'username': 'fixture', 'password': 'fixture'}
        with patch.object(run_live, 'load_settings', return_value=settings), \
             patch.object(run_live, 'create_server') as create, \
             patch.dict(os.environ, {'ESL_LIVE_WRITES': '1'}):
            run_live.main(['--template-publish'])
            self.assertEqual(os.environ['ESL_LIVE_WRITES'], '0')
            self.assertFalse(create.call_args.kwargs['seed'])
            self.assertIsInstance(create.call_args.kwargs['controller_registry'].get(),
                                  run_live.TemplatePublishClient)
        self.assertTrue(settings['live_writes'])

    def test_confirmed_dispatch_opt_in_enables_flag_even_when_saved_disabled(self):
        settings = {'live_writes': False, 'api_token': 'A' * 64,
                    'base_url': 'http://controller.invalid/esls_new',
                    'username': 'fixture', 'password': 'fixture'}
        with patch.object(run_live, 'load_settings', return_value=settings), \
             patch.object(run_live, 'create_server') as create, \
             patch.dict(os.environ, {'ESL_LIVE_WRITES': '0'}):
            run_live.main(['--template-publish', '--allow-confirmed-dispatch'])
            self.assertEqual(os.environ['ESL_LIVE_WRITES'], '1')
            client = create.call_args.kwargs['controller_registry'].get()
            self.assertIsInstance(client, run_live.TemplatePublishClient)
            self.assertTrue(client.allow_confirmed_dispatch)
            self.assertFalse(create.call_args.kwargs['seed'])
        self.assertFalse(settings['live_writes'])

    def test_dispatch_flag_requires_publish_before_credentials_are_loaded(self):
        for argv in (['--allow-confirmed-dispatch'],
                     ['--templates-only', '--allow-confirmed-dispatch'],
                     ['--templates-only', '--template-publish', '--allow-confirmed-dispatch']):
            with self.subTest(argv=argv), \
                 patch.object(run_live, 'load_settings', return_value={
                     'live_writes': False, 'api_token': 'A' * 64,
                     'base_url': 'http://controller.invalid/esls_new',
                     'username': 'fixture', 'password': 'fixture'}) as load, \
                 patch.object(run_live, 'create_server') as create, \
                 patch.dict(os.environ, {'ESL_LIVE_WRITES': '0'}), \
                 self.assertRaises(SystemExit) as error:
                run_live.main(argv)
            self.assertEqual(error.exception.code, 2)
            load.assert_not_called()
            create.assert_not_called()

    def test_template_modes_are_mutually_exclusive(self):
        with patch.object(run_live, 'load_settings') as load, self.assertRaises(SystemExit):
            run_live.main(['--templates-only', '--template-publish'])
        load.assert_not_called()

    def test_normal_launcher_retains_explicit_existing_write_mode(self):
        for saved in (False, True):
            settings = {'live_writes': saved, 'api_token': 'A' * 64,
                        'base_url': 'http://controller.invalid/esls_new',
                        'username': 'fixture', 'password': 'fixture'}
            with self.subTest(saved=saved), \
                 patch.object(run_live, 'load_settings', return_value=settings), \
                 patch.object(run_live, 'create_server') as create, \
                 patch.dict(os.environ, {'ESL_LIVE_WRITES': '0' if saved else '1'}):
                run_live.main([])
                self.assertEqual(os.environ['ESL_LIVE_WRITES'], '1' if saved else '0')
                self.assertIsInstance(create.call_args.kwargs['controller_registry'].get(),
                                      vendor.VendorClient)


if __name__ == '__main__':
    unittest.main()
